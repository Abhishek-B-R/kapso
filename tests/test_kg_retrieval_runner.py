"""The retrieval eval's arm loop, scored against stand-ins with no services.

A stand-in retriever returns scripted pools and rerank orders, so the
expected metrics below are worked out by hand. The reranker-failure test
drives the real KGGraphSearch._rerank_results, which swallows backend
errors, to show the runner still aborts.
"""

import pytest

from benchmarks.kg_retrieval.labels import LabeledQuery
from benchmarks.kg_retrieval.runner import (
    KGRetriever,
    RerankFailed,
    check_isolated,
    evaluate,
)
from kapso.knowledge_base.search.base import KGResultItem
from kapso.knowledge_base.search.kg_graph_search import KGGraphSearch


def item(page_id, overview=""):
    return KGResultItem(
        id=page_id,
        score=1.0,
        page_type="Principle",
        overview=overview,
    )


class StandInRetriever:
    """Pool A,B,C per query; the reranker puts the last candidate first."""

    def top(self, query, top_k):
        return [item("B"), item("A")][:top_k]

    def pool(self, query, pool_size):
        overviews = [10, 400, 500]
        return [item(i, "x" * n) for i, n in zip("ABC", overviews)]

    def rerank(self, query, pool, top_k, overview_cap):
        return [pool[2], pool[0]][:top_k]


ARMS = [
    {"name": "off", "rerank": False},
    {"name": "capped", "rerank": True, "reranker_overview_max_chars": 300},
    {"name": "nocap", "rerank": True, "reranker_overview_max_chars": None},
]


def test_each_arm_is_scored_overall_and_on_the_stress_subset():
    queries = [
        LabeledQuery("q1", "first", ("C",)),
        LabeledQuery("q2", "second", ("A",), stress=True),
    ]

    retriever = StandInRetriever()
    report = evaluate(queries, ARMS, retriever, [1, 2], top_k=2, pool_size=3)

    assert report["queries"] == {"overall": 2, "stress": 1}
    # off returns B,A: q1 misses C (recall 0, RR 0); q2 finds A at rank 2
    off = report["arms"]["off"]
    assert off["overall"]["recall@1"] == 0.0
    assert off["overall"]["recall@2"] == 0.5
    assert off["overall"]["mrr"] == pytest.approx(0.25)
    assert off["stress"]["mrr"] == pytest.approx(0.5)
    # reranked order is C,A: q1 hits at rank 1, q2 at rank 2
    capped = report["arms"]["capped"]
    assert capped["overall"]["recall@1"] == 0.5 and capped["overall"][
        "mrr"
    ] == pytest.approx(0.75)
    assert capped["stress"]["recall@1"] == 0.0
    # a 300 cap cuts 2 of 3 overviews per query; no cap cuts none; off has none
    assert capped["overall"]["clipped_share"] == pytest.approx(2 / 3)
    assert report["arms"]["nocap"]["overall"]["clipped_share"] == 0.0
    assert "clipped_share" not in off["overall"]
    # the pool holds every target, so the ceiling is 1.0
    assert report["pool_ceiling"]["overall"]["recall@3"] == 1.0


class RaisingBackend:
    def llm_completion_with_system_prompt(self, **kwargs):
        raise RuntimeError("provider down")


def reranking_search(backend):
    search = KGGraphSearch.__new__(KGGraphSearch)
    search._llm_backend = backend
    search.reranker_overview_max_chars = None
    search._neo4j_driver = search._weaviate_client = search._embedder = None
    return search


def test_a_swallowed_rerank_error_aborts_the_run():
    pool = [item("A", "first"), item("B", "second")]

    # KGGraphSearch hides the failure behind the original order ...
    silent = reranking_search(RaisingBackend())._rerank_results("q", pool, 2)
    assert [result.id for result in silent] == ["A", "B"]

    # ... and the retriever turns it into an error.
    retriever = KGRetriever(reranking_search(RaisingBackend()))
    with pytest.raises(RerankFailed):
        retriever.rerank("q", pool, 2, 300)


def test_the_eval_refuses_the_shipped_stores():
    own = {
        "weaviate_collection": "EvalOnly",
        "neo4j_uri": "bolt://localhost:7688",
    }
    check_isolated(own)

    with pytest.raises(ValueError, match="weaviate_collection"):
        check_isolated({**own, "weaviate_collection": "KapsoKG"})
    with pytest.raises(ValueError, match="neo4j_uri"):
        check_isolated({**own, "neo4j_uri": "bolt://localhost:7687"})
