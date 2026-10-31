"""Retrieval-quality eval for kg_graph_search: recall@k and MRR per arm.

Indexes the synthetic corpus into a dedicated Weaviate collection (and a
dedicated Neo4j instance) with the repo's own indexer, fetches each
query's candidate pool once, then scores every arm on that same pool: the
reranker off, and the reranker on with each configured overview cap. All
metrics are reported over every query and over the stress subset (queries
whose target page has an overview long enough for the cap to cut).

Run from the repository root:
    python -m benchmarks.kg_retrieval.runner \
        --config benchmarks/kg_retrieval/config.yaml
"""

import argparse
import copy
import json
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from benchmarks.kg_retrieval.labels import load_labels
from benchmarks.kg_retrieval.metrics import aggregate
from kapso.core.cli_inference import resolve_inference_config
from kapso.core.config import load_config, load_mode_config
from kapso.knowledge_base.search import (
    KGIndexInput,
    KGSearchFilters,
    KnowledgeSearchFactory,
)
from kapso.knowledge_base.search.kg_graph_search import parse_wiki_directory

SEARCH_BACKEND = "kg_graph_search"

# Provider keys (the embedder's OPENAI_API_KEY) live in a gitignored .env, as
# for the CLI and the other benchmark runners; no setting is read from it.
load_dotenv(find_dotenv(usecwd=True))


class RerankFailed(RuntimeError):
    """A rerank call failed; scoring it would silently measure no reranker."""


class FailLoudReranker:
    """Wraps the rerank LLM backend; remembers if its last call finished.

    KGGraphSearch._rerank_results swallows any error from the backend and
    returns the original order, which would score a failed run as the
    "reranker off" arm. The wrapper cannot stop that swallow, but it leaves
    a flag the caller checks right after the rerank.
    """

    def __init__(self, backend):
        self.backend = backend
        self.last_call_completed = False

    def llm_completion_with_system_prompt(self, **kwargs):
        self.last_call_completed = False
        response = self.backend.llm_completion_with_system_prompt(**kwargs)
        self.last_call_completed = True
        return response


class KGRetriever:
    """The retrieval operations the arm loop needs, over a KGGraphSearch."""

    def __init__(self, search):
        self.search = search
        self.reranker = FailLoudReranker(search._llm_backend)
        search._llm_backend = self.reranker

    def top(self, query, top_k):
        """What the product returns with the reranker off."""
        filters = KGSearchFilters(top_k=top_k, include_content=False)
        return self.search.search(
            query, filters=filters, use_llm_reranker=False
        ).results

    def pool(self, query, pool_size):
        """The candidates the reranker would be shown."""
        filters = KGSearchFilters(top_k=pool_size, include_content=False)
        return self.search.search(
            query, filters=filters, use_llm_reranker=False
        ).results

    def rerank(self, query, pool, top_k, overview_cap):
        """Rerank a copy of the pool with this arm's cap on the prompt."""
        if not pool:
            return []
        self.search.reranker_overview_max_chars = overview_cap
        candidates = copy.deepcopy(pool)
        results = self.search._rerank_results(query, candidates, top_k)
        if not self.reranker.last_call_completed:
            raise RerankFailed(f"rerank call failed for query {query!r}")
        return results


def check_isolated(search_params):
    """Refuse to run against the stores a real knowledge graph lives in."""
    defaults = KnowledgeSearchFactory.get_defaults(SEARCH_BACKEND)
    for key in ("weaviate_collection", "neo4j_uri"):
        if search_params[key] == defaults[key]:
            raise ValueError(
                f"{key} is {search_params[key]!r}, the shipped default; the "
                "eval needs its own so it never touches a real graph"
            )


def clipped_counts(pool, overview_cap):
    """Pool overviews the prompt cap cuts, and the pool size."""
    if overview_cap is None:
        return 0, len(pool)
    return sum(len(item.overview) > overview_cap for item in pool), len(pool)


def summarize(indices, rankings, queries, ks, extras):
    """Metrics for the queries at `indices`; extras carry per-query counts."""
    relevants = [queries[i].relevant for i in indices]
    scores = aggregate([rankings[i] for i in indices], relevants, ks)
    counts = [extras["returned"][i] for i in indices]
    scores["mean_results"] = sum(counts) / len(counts)
    if extras["clipped"] is not None:
        clipped = sum(extras["clipped"][i][0] for i in indices)
        total = sum(extras["clipped"][i][1] for i in indices)
        scores["clipped_share"] = clipped / total
    return scores


def evaluate(queries, arms, retriever, ks, top_k, pool_size):
    """Score every arm on one candidate pool per query."""
    pool_rankings = []
    arm_runs = {}
    for arm in arms:
        arm_runs[arm["name"]] = {"rankings": [], "returned": [], "clipped": []}
    for query in queries:
        pool = retriever.pool(query.query, pool_size)
        pool_rankings.append([item.id for item in pool])
        for arm in arms:
            run = arm_runs[arm["name"]]
            if arm["rerank"]:
                cap = arm["reranker_overview_max_chars"]
                results = retriever.rerank(query.query, pool, top_k, cap)
                run["clipped"].append(clipped_counts(pool, cap))
            else:
                results = retriever.top(query.query, top_k)
            run["rankings"].append([item.id for item in results])
            run["returned"].append(len(results))
    subsets = {
        "overall": list(range(len(queries))),
        "stress": [i for i, query in enumerate(queries) if query.stress],
    }
    report = {"queries": {name: len(idx) for name, idx in subsets.items()}}
    report["pool_ceiling"] = {
        name: aggregate(
            [pool_rankings[i] for i in idx],
            [queries[i].relevant for i in idx],
            [pool_size],
        )
        for name, idx in subsets.items()
    }
    report["arms"] = {}
    for arm in arms:
        run = arm_runs[arm["name"]]
        extras = {
            "returned": run["returned"],
            "clipped": run["clipped"] if arm["rerank"] else None,
        }
        report["arms"][arm["name"]] = {
            name: summarize(idx, run["rankings"], queries, ks, extras)
            for name, idx in subsets.items()
        }
    return report


def render_markdown(report, ks, pool_size):
    """One table per subset, one row per arm."""
    columns = [f"recall@{k}" for k in ks] + ["mrr", "mean_results"]
    lines = []
    for subset, count in report["queries"].items():
        ceiling = report["pool_ceiling"][subset][f"recall@{pool_size}"]
        lines += [
            f"## {subset} ({count} queries)",
            "",
            f"Candidate pool ceiling, recall@{pool_size}: {ceiling:.3f}",
            "",
            "| arm | " + " | ".join(columns) + " | clipped_share |",
            "|---|" + "---|" * (len(columns) + 1),
        ]
        for arm, subsets in report["arms"].items():
            scores = subsets[subset]
            cells = [f"{scores[column]:.3f}" for column in columns]
            clipped = scores.get("clipped_share")
            cells.append("n/a" if clipped is None else f"{clipped:.3f}")
            lines.append(f"| {arm} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def validate_arms(arms):
    if not isinstance(arms, list) or not arms:
        raise ValueError("arms must be a non-empty list")
    for arm in arms:
        if not isinstance(arm.get("name"), str) or not isinstance(
            arm.get("rerank"), bool
        ):
            raise ValueError(f"arm needs a name and a boolean rerank: {arm!r}")
        if arm["rerank"] and "reranker_overview_max_chars" not in arm:
            raise ValueError(
                f"arm {arm['name']!r} reranks, so it must set "
                "reranker_overview_max_chars (null for no cap)"
            )


def build_search(config_path, eval_config):
    """A KGGraphSearch with the reranker on, so a call can switch it off."""
    mode_config = load_mode_config(config_path)
    params = dict(eval_config["search"])
    params.update(
        include_connected_pages=False,
        use_llm_reranker=True,
        models=mode_config.get("models"),
        retry=mode_config.get("retry"),
        inference=resolve_inference_config(config_path),
    )
    check_isolated(params)
    return KnowledgeSearchFactory.create(SEARCH_BACKEND, params=params)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True, help="path to config.yaml")
    args = parser.parse_args(argv)

    eval_config = load_config(args.config)["retrieval_eval"]
    validate_arms(eval_config["arms"])
    ks, top_k, pool_size = (
        eval_config["ks"],
        eval_config["top_k"],
        eval_config["candidate_pool_size"],
    )
    if max(ks) > top_k or pool_size < top_k:
        raise ValueError("need max(ks) <= top_k <= candidate_pool_size")

    corpus_dir = Path(eval_config["corpus_dir"])
    page_ids = {page.id for page in parse_wiki_directory(corpus_dir)}
    queries = load_labels(eval_config["labels_path"], page_ids)
    if not any(query.stress for query in queries):
        raise ValueError("no stress queries in the labels")

    search = build_search(args.config, eval_config)
    if eval_config["index_corpus"]:
        search.index(KGIndexInput(wiki_dir=corpus_dir))
    report = evaluate(
        queries, eval_config["arms"], KGRetriever(search), ks, top_k, pool_size
    )
    report["config"] = eval_config
    search.close()

    results_dir = Path(eval_config["results_dir"])
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "results.json").write_text(json.dumps(report, indent=2))
    table = render_markdown(report, ks, pool_size)
    (results_dir / "results.md").write_text(table)
    print(table)


if __name__ == "__main__":
    main()
