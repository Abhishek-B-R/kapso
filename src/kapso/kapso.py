# Kapso Agent - Main Entry Point
#
# The primary user-facing API for the Kapso Agent system: the verbs
# build, deploy and learn on one object.
#   Kapso.build() -> Kapso.deploy() -> Software.run(); Kapso.learn()
#
# Usage:
#     from kapso import Kapso, Brief, Budget, Solution, DeployStrategy
#
#     kapso = Kapso(config="./kapso-config.yaml")     # engine knobs only
#     solution = kapso.build(
#         Brief.read("kapso-brief.md"),
#         evaluation="./evaluation", data="./data", repo=".",
#         output="../churn-build", budget=Budget(minutes=480),
#     )
#     software = kapso.deploy(solution, strategy=DeployStrategy.LOCAL)
#     result = software.run({"input": "data"})
#     Solution.open("../churn-build")                  # the same solution, from any process

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

import git

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Load environment variables from .env file (if present)
from dotenv import find_dotenv, load_dotenv
# Resolve .env from the caller's CWD upward. The no-arg default anchors at
# THIS file's directory — site-packages in a pip install — so the .env the
# README tells users to create next to their project was never read.
load_dotenv(find_dotenv(usecwd=True))

from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.execution.observability import (
    KnowledgeStatus,
    LessonStatus,
    OperationStatusView,
    credits_summary,
    knowledge_summary,
    platform_cost_summary,
)
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.execution.evaluation_maintainer.registry import EvaluationRegistry
from kapso.execution.iteration_evaluator import IterationEvaluator
from kapso.handles import Brief, Budget, EvaluatorRef, Solution
from kapso.execution.evaluation_integrity import build_evaluation_manifest
from kapso.environment.handlers.generic import GenericProblemHandler
from kapso.knowledge_base.search import KnowledgeSearchFactory, KGIndexInput
from kapso.knowledge_base.search.base import KGIndexMetadata
from kapso.knowledge_base.search.workflow_search import WorkflowRepoSearch
from kapso.knowledge_base.learners import Source, KnowledgePipeline
from kapso.knowledge_base.learners.defaults import learner_defaults
from kapso.core.cli_inference import resolve_inference_config
from kapso.researcher import Researcher, ResearchDepth, ResearchMode
from kapso.knowledge_base.types import ResearchFindings
from kapso.core.config import load_config, load_deployment_defaults, load_harness_defaults, load_mode_config
from kapso.harness import (
    BUILD_MODULES,
    Harness,
    HarnessError,
    advisory_lines,
    load_harness,
    reload_harness,
    resume_refusal,
    unmet_message,
)
from kapso.execution.inbox import (
    Request,
    idea_line,
    inbox_path,
    launch_mismatches,
    load_requests,
    read_launch_record,
    record_reply,
    register_campaign,
    resume_arguments,
    write_launch_record,
)
from kapso.execution.run_checkpoint import (
    RunCheckpointIncompatibleError,
    RunCheckpointStore,
)
from kapso.core.preflight import run_preflight
from kapso.learning.graders.frame import GradingFrame
from kapso.learning.lesson_result import LessonResult, MemoryStatus
from kapso.learning.mining import MiningFrame
from kapso.learning.serving_launch import (
    plan_campaign_serving,
    stage_serving,
)
from kapso.learning.trajectory_store import TrajectoryStore, save_trajectory
from kapso.learning.bank_remote import bank_origin
from kapso.learning.update_frame import UpdateFrame, init_bank

from kapso.deployment import (
    Software,
    DeployConfig,
    DeployStrategy,
    DeploymentFactory,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class KGIndexError(Exception):
    """
    Raised when KG index file is invalid or backend data is missing.
    
    This typically happens when:
    - The .index file exists but the backend (Weaviate/Neo4j) was wiped
    - The .index file is corrupted or has invalid format
    - The backend is not accessible
    """
    pass


# =============================================================================
# KAPSO AGENT
# =============================================================================

# Path to default configuration
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _absolute(path: Optional[str]) -> Optional[str]:
    """A launch argument as the launch record keeps it: resolved against
    the launch directory, so a resume or an inbox reply run from any other
    directory (a host session's, say) finds the same files."""
    return None if path is None else str(Path(path).expanduser().resolve())


def _git_rev(workspace: Path, ref: str) -> str:
    """The commit a ref names in the campaign workspace."""
    return subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", ref],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


# Experiments per campaign when the caller names no cap. One source for the
# facade default and the CLI's help text.
DEFAULT_MAX_ITERATIONS = 10


def _memory_overrides(
    serving_plan: Optional[Dict[str, Any]],
    kg_index_path: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Per-campaign strategy params carrying BOTH memory stores.

    The strategy mounts the gates that follow from these: a staged bank
    pulls in the `bank` gate, a staged knowledge index pulls in the
    wiki-search gates. Neither is an independent config choice — the
    injected intro tells sessions those tools exist (E2E review
    2026-08-24: they did not).
    """
    overrides: Dict[str, Any] = {}
    if serving_plan:
        overrides["bank_serving"] = serving_plan["bank_serving"]
    if kg_index_path:
        overrides["kg_index_path"] = kg_index_path
    return overrides or None

class Kapso:
    """
    The main Kapso Agent class.

    A Kapso is an intelligent agent with ONE memory and TWO stores
    (learn-api-design.md §8):
    - knowledge  — what others know, imported via learn_knowledge()
      (repos, research outputs) into the knowledge graph;
    - experience — what the agent measured by doing, earned via learn()
      (its own campaigns) into the evidence-priced bank.
    build() consults BOTH automatically, through separate surfaces
    (KG search gates vs bank serving), and every Solution stamps
    the exact memory it drew on.

    The closed loop:
        kapso = Kapso(kg_index="data/indexes/ml.index")
        kapso.learn_knowledge(Source.Repo(url), kapso.research(question))
        solution = kapso.build(brief, budget=Budget(minutes=240))
        lesson   = kapso.learn(solution)     # import -> mine -> exam -> lesson
        print(kapso.memory.explain())        # one status view of both stores
        solution2 = kapso.build(brief)       # smarter on both axes

    Deployment:
        software = kapso.deploy(solution)
        result = software.run({"ticker": "AAPL"})

    With an evaluation, data and a starting repository:
        solution = kapso.build(
            "Build a classifier with 95% accuracy",
            evaluation="./evaluation/",
            data="./datasets/",
            repo="https://github.com/owner/starter-repo",
        )
    """
    
    # Mapping from Source type to Learner type
    _SOURCE_TO_LEARNER = {
        Source.Repo: "repo",
        Source.Solution: "experiment",
    }
    
    def __init__(
        self,
        config: Optional[str] = None,
        kg_index: Optional[str] = None,
        bank: Optional[str] = None,
    ):
        """
        Initialize a Kapso agent. Nothing starts here.

        Args:
            config: Path to the configuration file, the engine's knobs
                    (the packaged config.yaml when not given)
            kg_index: Path to existing .index file to load knowledge graph from.
                      If provided, connects to the indexed knowledge graph.
                      If not provided, knowledge search is disabled.
            bank: Experience-store (knowledge bank) home directory. Overrides
                  the config default (learning.bank.local_path). The bank is
                  where learn() writes evidence-priced cards and where
                  build() serves them from when serving is enabled.
        """
        self.config_path = config or DEFAULT_CONFIG_PATH
        self._config = load_config(self.config_path)
        # The harness block (store, thresholds, the two session timeouts)
        # and the loaded harness: none until load_harness() is called.
        self._harness_settings = load_harness_defaults(self.config_path)
        self._harness: Optional[Harness] = None
        # By construction time every dependency import has settled, so
        # this atexit registration lands last (LIFO-first at exit) and
        # keeps third-party exit-time warning noise out of user output.
        CodingAgentFactory.register_quiet_exit()

        # The agent's memory resolves ONCE here (design §8.2): knowledge =
        # the KG connection below; experience = the bank home. Every later
        # call (learn / learn_knowledge / build) reads this resolution —
        # never re-reading config at call time.
        configured_bank = (
            (self._config.get("learning") or {}).get("bank") or {}
        ).get("local_path")
        bank_path = bank or configured_bank
        self._bank_home: Optional[Path] = (
            Path(bank_path).expanduser() if bank_path else None
        )
        
        # Initialize knowledge search
        if kg_index:
            self._load_kg_index(kg_index)
            self._kg_index_path = kg_index
        else:
            self.knowledge_search = KnowledgeSearchFactory.create_null()
            self._kg_index_path = None
        # Backend clients (Weaviate/Neo4j/embeddings) hold real sockets;
        # close them at interpreter exit so scripts end without unclosed-
        # socket ResourceWarnings (onboarding E2E finding #8).
        atexit.register(self.close)
        
        # Print initialization status
        if kg_index:
            print(f"Initialized Kapso")
        else:
            print(f"Initialized Kapso (Knowledge Graph: disabled)")

    # ------------------------------------------------------------ harness

    @property
    def harness(self) -> Optional[Harness]:
        """The loaded harness, or None: today's generic behaviour."""
        return self._harness

    def load_harness(self, ref: str) -> Harness:
        """Resolve a bundled name, a path or a git reference; run `check`
        and raise on a failure; hash it; read what this machine lacks into
        `harness.missing` without raising. A second call replaces the
        first: one object, one harness. Nothing starts here."""
        self._harness = load_harness(ref, settings=self._harness_settings)
        print(f"Harness: {self._harness.label()} from {self._harness.source}")
        for row in self._harness.missing:
            print(f"  needs {row.label}: {row.fix}  [{', '.join(row.modules)}]")
        return self._harness

        # Lazy-initialized web researcher (created on first `.research()` call).
        self._web_researcher: Optional[Researcher] = None
    
    # =========================================================================
    # Knowledge Graph Indexing
    # =========================================================================
    
    def _load_kg_index(self, index_path: str) -> None:
        """
        Load existing index from .index file.
        
        Args:
            index_path: Path to the .index file
            
        Raises:
            KGIndexError: If index file is invalid or backend data is missing
            FileNotFoundError: If index file doesn't exist
        """
        index_path = Path(index_path)
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        
        # Load index metadata
        with open(index_path) as f:
            index_data = json.load(f)
        
        metadata = KGIndexMetadata.from_dict(index_data)
        
        # Get search config from mode config
        mode = self._config.get("default_mode", "GENERIC")
        mode_config = self._config.get("modes", {}).get(mode, {})
        search_config = mode_config.get("knowledge_search", {})
        
        # Merge backend_refs into params (backend_refs take precedence)
        params = search_config.get("params", {}).copy()
        params.update(metadata.backend_refs)
        params.setdefault("models", mode_config.get("models"))
        params.setdefault("retry", mode_config.get("retry"))
        params.setdefault("inference", resolve_inference_config(self.config_path))

        # Create search backend (closing any superseded one's clients)
        self._close_knowledge_search()
        self.knowledge_search = KnowledgeSearchFactory.create(
            search_type=metadata.search_backend,
            params=params,
        )
        
        # Validate backend has data
        if not self.knowledge_search.validate_backend_data():
            raise KGIndexError(
                f"Index file exists but backend data not found.\n"
                f"Re-index with: kapso.index_kg("
                f"wiki_dir='{metadata.data_source}', save_to='{index_path}')"
            )
        
        print(f"  Knowledge Graph: Loaded ({metadata.page_count} pages from {metadata.search_backend})")

    def _close_knowledge_search(self) -> None:
        # Runs at atexit — tolerate a test-stubbed backend without close();
        # every real KnowledgeSearch implements it (base class contract).
        closer = getattr(self.__dict__.get("knowledge_search"), "close", None)
        if callable(closer):
            closer()

    def close(self) -> None:
        """Release the knowledge-search backend's network clients
        (Weaviate, Neo4j, embeddings). Idempotent — registered atexit at
        construction so scripts end without unclosed-socket
        ResourceWarnings; also safe to call earlier when done with
        knowledge search (index_kg / learn_knowledge reconnect fresh)."""
        self._close_knowledge_search()

    def index_kg(
        self,
        wiki_dir: Optional[str] = None,
        data_path: Optional[str] = None,
        save_to: str = None,
        search_type: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """
        Index knowledge data and save index reference file.
        
        This is a ONE-TIME operation. After indexing, the data persists
        in the configured backends (Weaviate, Neo4j, etc.). Use the returned
        .index file path with kg_index parameter on subsequent runs.
        
        Args:
            wiki_dir: Path to wiki directory (for kg_graph_search backend).
                      Contains .md files organized in type subdirectories.
            data_path: Path to JSON data file (for kg_llm_navigation backend).
                       Contains nodes and edges dict.
            save_to: Path to save .index file (e.g., "data/indexes/ml.index")
            search_type: Override search backend type. If not provided, uses
                         config default or infers from input type.
            force: If True, clears existing data before indexing
            
        Returns:
            Path to created .index file
            
        Raises:
            ValueError: If neither wiki_dir nor data_path provided
            
        Example:
            # Index wiki pages (kg_graph_search)
            kapso.index_kg(
                wiki_dir="data/wikis/ml_knowledge",
                save_to="data/indexes/ml.index",
            )
            
            # Index JSON knowledge graph (kg_llm_navigation)
            kapso.index_kg(
                data_path="benchmarks/mle/data/kg_data.json",
                save_to="data/indexes/kaggle.index",
                search_type="kg_llm_navigation",
            )
        """
        if save_to is None:
            raise ValueError("save_to is required - specify where to save the .index file")
        
        if not wiki_dir and not data_path:
            raise ValueError("Must provide either wiki_dir or data_path")
        
        # Determine search type
        if search_type is None:
            if data_path:
                # JSON data implies kg_llm_navigation
                search_type = "kg_llm_navigation"
            else:
                # Wiki dir implies kg_graph_search (or use config default)
                mode = self._config.get("default_mode", "GENERIC")
                mode_config = self._config.get("modes", {}).get(mode, {})
                search_config = mode_config.get("knowledge_search", {})
                search_type = search_config.get("type", "kg_graph_search")
        
        # Get params from config
        mode = self._config.get("default_mode", "GENERIC")
        mode_config = self._config.get("modes", {}).get(mode, {})
        search_config = mode_config.get("knowledge_search", {})
        params = search_config.get("params", {}).copy()
        params.setdefault("models", mode_config.get("models"))
        params.setdefault("retry", mode_config.get("retry"))
        params.setdefault("inference", resolve_inference_config(self.config_path))

        # Create search backend (closing any superseded one's clients)
        self._close_knowledge_search()
        self.knowledge_search = KnowledgeSearchFactory.create(
            search_type=search_type,
            params=params,
        )
        
        # Clear existing data if force=True
        if force:
            print("  Clearing existing index...")
            self.knowledge_search.clear()
        
        # Determine data source and index
        if wiki_dir:
            data_source = str(wiki_dir)
            print(f"  Indexing wiki: {wiki_dir}")
            self.knowledge_search.index(KGIndexInput(wiki_dir=wiki_dir))
        else:
            data_source = str(data_path)
            print(f"  Indexing JSON: {data_path}")
            # Load JSON and index directly (for kg_llm_navigation)
            with open(data_path) as f:
                graph_data = json.load(f)
            self.knowledge_search.index(graph_data)
        
        # Get page count
        page_count = self.knowledge_search.get_indexed_count()
        
        # Build index metadata
        metadata = KGIndexMetadata(
            version="1.0",
            created_at=datetime.now().isoformat(),
            data_source=data_source,
            search_backend=search_type,
            backend_refs=self.knowledge_search.get_backend_refs(),
            page_count=page_count,
        )
        
        # Save index file
        save_path = Path(save_to)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        self._kg_index_path = str(save_path)
        print(f"  Index saved: {save_to} ({page_count} pages)")
        
        return str(save_path)

    # =========================================================================
    # Public Web Research
    # =========================================================================

    def research(
        self,
        objective: str,
        *,
        mode: ResearchMode = ["idea", "implementation"],
        depth: ResearchDepth = "deep",
    ) -> ResearchFindings:
        """
        Do deep public web research for an objective.
        
        Args:
            objective: What you want to research on the public web.
            mode: "idea" | "implementation" | "study" (or list of modes)
            depth: "light" | "deep"
                Maps to OpenAI `reasoning.effort`:
                - light -> "medium"
                - deep  -> "high"
        
        Returns:
            `ResearchFindings` with fluent accessors:
            - .ideas -> List[Source.Idea]
            - .implementations -> List[Source.Implementation]
            - .report -> Source.ResearchReport (if mode="study")
        """
        run_preflight("research", self._config)
        if self._web_researcher is None:
            # CLI-only inference: the researcher's session spec comes from
            # the resolved `inference:` block (packaged defaults, this
            # config file's overrides on top), not the mode's model routes.
            self._web_researcher = Researcher(config_path=self.config_path)

        return self._web_researcher.research(objective, mode=mode, depth=depth)
    
    def learn_knowledge(
        self,
        *sources: Union[Source.Repo, Source.Solution, Source.Idea, Source.Implementation, Source.ResearchReport, ResearchFindings],
        wiki_dir: str = "data/wikis",
        skip_merge: bool = False,
        kg_index: Optional[str] = None,
        github_org: Optional[str] = None,
        is_private: Optional[bool] = None,
        on_status: Optional[Any] = None,
    ) -> "PipelineResult":
        """
        Learn from one or more knowledge sources.
        
        This ingests knowledge into the Knowledge Graph (KG) via `KnowledgePipeline`.
        
        Supported sources (MVP):
        - `Source.Repo(...)`
        - `Source.Solution(...)`
        - `Source.Idea(...)`, `Source.Implementation(...)`, `Source.ResearchReport(...)`
        - `ResearchFindings` (output of `Kapso.research(...)`)
        
        Args:
            *sources: One or more Source objects.
            wiki_dir: Path to a local wiki directory (e.g., `data/wikis`) used as
                the KG source-of-truth on disk.
                
                Note:
                - URL-based KG targets (e.g. `https://skills.leeroo.com`) are not
                  supported in this code path yet.
            skip_merge: If True, only extract `WikiPage`s (Stage 1) and skip merging
                into the KG backends (Stage 2). This avoids requiring Neo4j/Weaviate.
            github_org: GitHub organization to publish the extracted
                workflows' repositories to (the token's own account when
                not given). Passing it turns publishing on for this call;
                otherwise `learner.ingestor.publish_workflows` decides.
            is_private: Whether those repositories are private. None (the
                default) defers to the config's github_repo_visibility.
                Passing it turns publishing on for this call too.
            
        Example:
            # Learn from repo + web research and merge into local KG
            kapso.learn_knowledge(
                Source.Repo("https://github.com/user/repo"),
                kapso.research("How to pick LoRA rank?", mode="idea"),
                wiki_dir="data/wikis",
            )
            
            # Learn and push workflow repos to an organization as public
            kapso.learn_knowledge(
                Source.Repo("https://github.com/user/repo"),
                github_org="my-org",
                is_private=False,
            )
        """
        if not sources:
            raise ValueError("learn_knowledge() requires at least one source")
        # skip_merge=True stops after page extraction, so the merger session
        # and both KG stores drop out of the requirement set.
        # The call's GitHub arguments turn publishing on; otherwise the
        # config's learner.ingestor block decides (packaged default when a
        # caller's config omits the key).
        mode_for_publishing = self._config.get("default_mode", "GENERIC")
        ingestor_config = (
            self._config.get("modes", {}).get(mode_for_publishing, {})
            .get("learner", {}).get("ingestor", {})
        )
        publish_workflows = (
            github_org is not None
            or is_private is not None
            or bool(ingestor_config.get(
                "publish_workflows", learner_defaults("ingestor")["publish_workflows"]
            ))
        )
        run_preflight(
            "learn_knowledge", self._config,
            skip_merge=skip_merge, publish_workflows=publish_workflows,
        )
        # research(mode="idea"/"implementation") returns a LIST of typed
        # sources; the advertised contract passes that output directly as
        # one argument — flatten one level so the pipeline's per-source
        # factory sees the typed items, never a bare list (found live
        # 2026-08-24 by the facade E2E: "Unknown ingestor type: 'list'").
        flattened: List[Any] = []
        for item in sources:
            if isinstance(item, (list, tuple)):
                flattened.extend(item)
            else:
                flattened.append(item)
        sources = tuple(flattened)
        if not sources:
            raise ValueError(
                "learn_knowledge() received only empty source lists"
            )

        # URL wiki targets are not supported: silently rewriting the
        # caller's destination to an unrelated local path was how pages
        # landed somewhere the caller never chose (stale-code audit
        # 2026-08-26, B2). Fail loud instead.
        if isinstance(wiki_dir, str) and wiki_dir.startswith(("http://", "https://")):
            raise ValueError(
                f"URL wiki_dir is not supported ({wiki_dir}); pass a local "
                "directory path"
            )
        resolved_wiki_dir = wiki_dir

        # Optional: propagate an existing `.index` file path into the merge agent.
        #
        # Why:
        # - The KnowledgeMerger performs create/edit operations via an MCP server.
        # - That MCP server now supports Option A: initializing from KG_INDEX_PATH.
        # - We pass the index path through pipeline->merger so the Claude Code
        #   subprocess can set KG_INDEX_PATH for the MCP server.
        index_path = kg_index or getattr(self, "_kg_index_path", None)
        merger_params = {"kg_index_path": index_path} if index_path else {}

        # Get learner config from mode config
        # This allows config.yaml to specify ingestor/merger params (auth_mode, timeout, etc.)
        mode = self._config.get("default_mode", "GENERIC")
        mode_config = self._config.get("modes", {}).get(mode, {})
        learner_config = mode_config.get("learner", {})

        # Extract ingestor and merger params from config
        ingestor_params = learner_config.get("ingestor", {}).copy()
        config_merger_params = learner_config.get("merger", {})

        # The call's GitHub settings override config.yaml's; the ingestor
        # takes the config's github_repo_visibility when is_private is not
        # passed (stale-code audit 2026-08-26, A1).
        ingestor_params["publish_workflows"] = publish_workflows
        if github_org is not None:
            ingestor_params["github_org"] = github_org
        if is_private is not None:
            ingestor_params["github_repo_visibility"] = (
                "private" if is_private else "public"
            )

        # Merge config merger params with kg_index_path (kg_index_path takes precedence)
        final_merger_params = {**config_merger_params, **merger_params}

        pipeline = KnowledgePipeline(
            wiki_dir=resolved_wiki_dir,
            ingestor_params=ingestor_params,
            merger_params=final_merger_params,
            index_builder=self.index_kg,
        )

        # Observability (design §2): ingestion sessions run long between
        # natural updates, so the base-class daemon carries liveness; the
        # pipeline reports per-source progress and the merge phase.
        heartbeat_seconds = self._status_heartbeat_seconds()
        status = KnowledgeStatus(
            self._status_file("learn_knowledge"),
            heartbeat_seconds=heartbeat_seconds,
            daemon=bool(heartbeat_seconds),
            on_status=on_status,
        )
        print(f"status: {status.path}")
        try:
            result = self._learn_knowledge_chain(
                pipeline, sources, skip_merge, resolved_wiki_dir, status
            )
        finally:
            in_flight = sys.exc_info()[1]
            if in_flight is not None:
                status.failed(in_flight)
        return result

    def _learn_knowledge_chain(
        self,
        pipeline: "KnowledgePipeline",
        sources: tuple,
        skip_merge: bool,
        resolved_wiki_dir: str,
        status: KnowledgeStatus,
    ) -> "PipelineResult":
        result = pipeline.run(*sources, skip_merge=skip_merge, status=status)

        # The merge wrote pages into the KG backends AND an .index beside
        # the wiki dir. Record that index as this agent's knowledge
        # provenance: build stamps it into every Solution and threads it
        # to the wiki-search gates, so a solution is traceable to the
        # knowledge state that produced it. Without this the stamp was
        # null on every learn_knowledge -> build sequence and the gates
        # had no index to mount (E2E review 2026-08-24).
        if not skip_merge:
            merged_index = Path(resolved_wiki_dir).expanduser() / ".index"
            if merged_index.is_file():
                self._kg_index_path = str(merged_index)
                print(f"  Knowledge index: {merged_index}")
        # S1 fix (learn-api-design.md §8.2): a merged run just wrote into
        # the KG backends — a Kapso constructed without kg_index would
        # otherwise keep its null search and the next build() in this
        # object would be blind to knowledge it just learned. Refresh the
        # search from the config preset, exactly as index_kg() does.
        if not skip_merge and not self.knowledge_search.is_enabled():
            mode = self._config.get("default_mode", "GENERIC")
            mode_config = self._config.get("modes", {}).get(mode, {})
            search_config = mode_config.get("knowledge_search", {})
            params = search_config.get("params", {}).copy()
            params.setdefault("models", mode_config.get("models"))
            params.setdefault("retry", mode_config.get("retry"))
            params.setdefault("inference", resolve_inference_config(self.config_path))
            self._close_knowledge_search()
            self.knowledge_search = KnowledgeSearchFactory.create(
                search_type=search_config.get("type", "kg_graph_search"),
                params=params,
            )
            print("  Knowledge search connected (post-learn refresh)")

        # Keep a small, user-friendly summary.
        print(
            f"Learn complete: sources={result.sources_processed}, "
            f"extracted_pages={result.total_pages_extracted}, "
            f"created={result.created}, edited={result.edited}, "
            f"errors={len(result.errors)}"
        )

        status.done(
            pages_extracted=result.total_pages_extracted,
            created=result.created,
            edited=result.edited,
            errors=len(result.errors),
        )
        return result
    

    # =========================================================================
    # Learning from experience (learn-from-trajectories)
    # =========================================================================

    def _bank_head(self) -> str:
        """Current head of the bank home (fail loud when absent)."""
        return subprocess.run(
            ["git", "--git-dir", str(self._bank_home), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    @property
    def memory(self) -> MemoryStatus:
        """What this agent knows right now, across both memory stores
        (design §8.2): knowledge (imported — KG) and experience (earned —
        the bank)."""
        knowledge_enabled = self.knowledge_search.is_enabled()
        bank_head = None
        active_cards = None
        store_count = None
        if self._bank_home is not None and self._bank_home.exists():
            bank_head = self._bank_head()
            listing = subprocess.run(
                ["git", "--git-dir", str(self._bank_home), "ls-tree",
                 "-r", "--name-only", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
            active_cards = sum(
                1 for path in listing
                if (path.startswith("insights/") or path.startswith("procedures/"))
                and path.endswith(".md") and not path.endswith("index.md")
            )
            store = TrajectoryStore.from_config(self._config)
            store_count = len(store.list_manifests())
        return MemoryStatus(
            knowledge_index=self._kg_index_path,
            knowledge_backend=(
                type(self.knowledge_search).__name__ if knowledge_enabled else None
            ),
            knowledge_enabled=knowledge_enabled,
            bank_path=str(self._bank_home) if self._bank_home else None,
            bank_head=bank_head,
            bank_active_cards=active_cards,
            store_trajectories=store_count,
            serving_enabled=bool(
                ((self._config.get("learning") or {}).get("serving") or {})
                .get("enabled")
            ),
        )

    # =========================================================================
    # Observability (evolve-observability-design.md v3)
    # =========================================================================

    @staticmethod
    def status(path: str) -> OperationStatusView:
        """Read any operation's status file — a workspace, a status file,
        or a directory of them. A classmethod on purpose: observing a run
        needs no constructed agent. `view.explain()` renders the same
        screen `kapso watch` shows."""
        return OperationStatusView(path)

    def _status_heartbeat_seconds(self) -> Optional[float]:
        """The status daemons' beat, from the resolved mode config's
        budget block (the same key that paces a build's durable clock)."""
        interval = (
            load_mode_config(self.config_path).get("budget") or {}
        ).get("checkpoint_heartbeat_seconds")
        return float(interval) if interval else None

    def _status_file(self, operation: str) -> Path:
        status_dir = (self._config.get("learning") or {}).get("status_dir")
        if status_dir is None:
            # Sourced from the canonical config, never re-hardcoded
            # (Rule 1): caller configs that omit the key inherit the
            # packaged default from its single home.
            status_dir = load_config(DEFAULT_CONFIG_PATH)["learning"][
                "status_dir"
            ]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return Path(status_dir).expanduser() / f"{operation}-{stamp}.json"

    def learn(
        self,
        source: Union[Solution, str],
        *,
        trajectory_id: Optional[str] = None,
        learner_version: Optional[str] = None,
        exam: bool = True,
        push: Optional[bool] = None,
        on_status: Optional[Any] = None,
    ) -> LessonResult:
        """Learn from one finished campaign: import it into the trajectory
        store, mine it, grade the bank on it (exam-before-lesson), then run
        the update crew — evidence-priced cards, one tagged bank commit.

        Args:
            source: What to learn from —
                - the Solution returned by build() (its campaign
                  directory, `trace`, is read directly),
                - a path to a campaign directory (archived + imported), or
                - a trajectory id already in the store (import skipped).
            trajectory_id: Store id when importing a directory; default is
                derived (<goal-or-dir-slug>/<UTC-stamp>).
            learner_version: Update-crew version; default from config
                (learning.update_crew.default_version).
            exam: Run the hindcast exam against the pinned pre-lesson bank
                head first. False is for development replays only.
            push: Push the bank commit to the bank's `origin` remote
                (attached via `kapso bank connect <url>`). None means
                "push exactly when an origin is attached".
            on_status: Optional hook called with the status dict after
                every status write and heartbeat (observability §4b).
                Exceptions from the hook propagate.

        Returns:
            LessonResult — what changed in the bank and the paper trail.
        """
        started = datetime.now(timezone.utc)
        if self._bank_home is None:
            raise ValueError(
                "no bank configured — set learning.bank.local_path or "
                "pass Kapso(bank=...)"
            )
        if not self._bank_home.exists():
            init_bank(str(self._bank_home))
            print(f"initialized bank home at {self._bank_home}")
        origin = bank_origin(self._bank_home)
        should_push = bool(origin) if push is None else push
        # Preflight (onboarding E2E findings #1 and #5): every crew's CLI
        # and credentials, plus the bank's push destination, verified in
        # seconds up front — never after hours of crew work on the far side.
        run_preflight(
            "learn", self._config,
            bank_home=self._bank_home, push=should_push,
        )
        learning_config = self._config["learning"]
        version = (
            learner_version
            or learning_config["update_crew"]["default_version"]
        )
        store = TrajectoryStore.from_config(self._config)

        # Observability (design §2): crew sessions run 30+ minutes between
        # updates, so the base-class daemon carries liveness.
        heartbeat_seconds = self._status_heartbeat_seconds()
        status = LessonStatus(
            self._status_file("learn"),
            heartbeat_seconds=heartbeat_seconds,
            daemon=bool(heartbeat_seconds),
            on_status=on_status,
        )
        print(f"status: {status.path}")
        try:
            return self._learn_chain(
                source, trajectory_id, version, exam, should_push, origin,
                started, store, learning_config, status,
            )
        finally:
            in_flight = sys.exc_info()[1]
            if in_flight is not None:
                status.failed(in_flight)

    def _learn_chain(
        self,
        source: Union[Solution, str],
        trajectory_id: Optional[str],
        version: str,
        exam: bool,
        should_push: bool,
        origin: Optional[str],
        started: datetime,
        store: TrajectoryStore,
        learning_config: Dict[str, Any],
        status: LessonStatus,
    ) -> LessonResult:
        status.phase("harvest")

        # --- dispatch (design §2) ---
        if isinstance(source, Solution):
            campaign_dir = source.campaign
            slug_seed = source.brief.objective
        else:
            known_ids = {m["id"] for m in store.list_manifests()}
            if source in known_ids:
                campaign_dir = None
                trajectory_id = source
                slug_seed = source
            else:
                campaign_dir = Path(source).expanduser()
                slug_seed = campaign_dir.name
                if not campaign_dir.is_dir():
                    raise FileNotFoundError(
                        f"learn() source {source!r} is neither a store "
                        f"trajectory id nor an existing campaign directory"
                    )

        if campaign_dir is not None:
            if trajectory_id is None:
                slug = "".join(
                    ch if ch.isalnum() else "-" for ch in slug_seed.lower()
                ).strip("-")[:48].strip("-") or "campaign"
                stamp = started.strftime("%Y%m%dT%H%M%S")
                trajectory_id = f"{slug}/{stamp}_facade"
            # Harvest bridge (the same step benchmark drivers run at
            # campaign completion). A bare build workspace lacks the
            # benchmark-shaped artifacts, so the facade synthesizes the
            # historical-contract trio HONESTLY from what the campaign
            # actually produced — each generated file says so.
            kapso_dir = campaign_dir / ".kapso"
            kapso_dir.mkdir(exist_ok=True)
            meta_path = campaign_dir / "campaign_meta.json"
            if not meta_path.is_file():
                meta_path.write_text(json.dumps({
                    "goal": slug_seed,
                    "workspace": str(campaign_dir),
                    "harvested_by": "Kapso.learn",
                    "harvested_at": started.isoformat(timespec="seconds"),
                }, indent=1))
            report_path = campaign_dir / "final_report.json"
            if not report_path.is_file():
                report: Dict[str, Any] = {"generated_by": "Kapso.learn"}
                # The manifest reads family/dataset from here, and the
                # update crew scopes cards by them. Recording the coords
                # the campaign was SERVED on keeps the cards a lesson
                # mints eligible for the very task that produced them
                # (E2E review 2026-08-24: cards were scoped to invented
                # families and matched nothing).
                served_record = (
                    campaign_dir / ".kapso" / "serving" / "serving-record.yaml"
                )
                if served_record.is_file():
                    served_task = yaml.safe_load(
                        served_record.read_text()
                    ).get("task") or {}
                    report["family"] = served_task.get("family")
                    report["dataset"] = served_task.get("dataset")
                if isinstance(source, Solution):
                    report.update({
                        "goal": source.brief.objective,
                        "goal_achieved": source.goal_achieved,
                        "final_score": source.score,
                        "stopped_reason": source.stopped_reason,
                        "experiments": source.experiments,
                        "experiments_total": source.experiments_total,
                        "cost_usd": source.cost_usd,
                    })
                report_path.write_text(json.dumps(report, indent=1, default=str))
            log_path = campaign_dir / ".kapso" / "campaign.log"
            if not log_path.is_file():
                lines = ["# facade-generated harvest log (Kapso.learn)"]
                if isinstance(source, Solution):
                    lines.append(source.explain())
                log_path.write_text("\n".join(lines) + "\n")
            # The store contract requires registered runs. A bare build
            # workspace records its experiments in the history store, not
            # a runs/ archive — synthesize run manifests from that REAL
            # history (one per recorded experiment; a campaign with zero
            # experiments has nothing to learn from and fails loud).
            runs_dir = campaign_dir / "runs"
            if not any(runs_dir.glob("run_*")):
                history_path = (
                    campaign_dir / ".kapso" / "experiment_history.json"
                )
                if not history_path.is_file():
                    raise FileNotFoundError(
                        f"learn() source {campaign_dir} has neither runs/ "
                        "nor .kapso/experiment_history.json — nothing to "
                        "learn from"
                    )
                history = json.loads(history_path.read_text())
                entries = (
                    history if isinstance(history, list)
                    else history.get("experiments", [])
                )
                if not entries:
                    raise ValueError(
                        f"learn() source {campaign_dir} recorded no "
                        "experiments — nothing to learn from"
                    )
                for index, entry in enumerate(entries, start=1):
                    run_dir = runs_dir / f"run_{index:04d}"
                    run_dir.mkdir(parents=True, exist_ok=True)
                    (run_dir / "manifest.txt").write_text(
                        json.dumps(
                            {"generated_by": "Kapso.learn", **entry}
                            if isinstance(entry, dict)
                            else {"generated_by": "Kapso.learn",
                                  "experiment": entry},
                            indent=1, default=str,
                        )
                    )
            serving_record = (
                campaign_dir / ".kapso" / "serving" / "serving-record.yaml"
            )
            served_head: Optional[str] = None
            if serving_record.is_file():
                served_head = yaml.safe_load(
                    serving_record.read_text()
                )["bank_head"]
            save_trajectory(
                store,
                trajectory_id,
                work_dir=str(campaign_dir),
                campaign_log=str(log_path),
                contract="historical",
                # A build workspace IS a git repo, and `.git/index` is
                # rewritten by any git command a later reader runs — the
                # mining frame's raw-immutability check then fails the view
                # ("raw file .git/index was modified during mining", found
                # live 2026-08-24). The repo's own object store is not
                # campaign evidence: the working tree, living documents,
                # run manifests and logs are.
                work_dir_exclude=(".git",),
                bank_head=served_head,
                upload=None,
            )
            print(f"  Harvested into store: {trajectory_id}")
            status.note(
                f"harvested into store ({trajectory_id})",
                trajectory_id=trajectory_id,
            )

        # --- mine (idempotent: skip when the view exists) ---
        status.phase("mine", trajectory_id=trajectory_id)
        manifest = store.manifest(trajectory_id)
        if not manifest.get("derived", {}).get("mined"):
            mined_dir = MiningFrame.from_config(self._config).mine(trajectory_id)
            print(f"  Mined view: {mined_dir}")
            status.note(f"mined view written ({mined_dir})")

        # --- the exam pin: clone + record the head BEFORE the lesson ---
        graders_root = Path(
            learning_config["graders"]["run_root"]
        ).expanduser()
        checkout = (
            graders_root / "ingest-serving"
            / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
               + "-" + uuid.uuid4().hex[:8])
        )
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", str(self._bank_home), str(checkout)],
            check=True,
        )
        bank_head_before = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

        status.note(
            f"pinned pre-lesson bank head {bank_head_before[:8]}",
            bank_head_before=bank_head_before,
        )
        exam_report_path: Optional[str] = None
        if exam:
            status.phase("exam")
            grading = GradingFrame(store, self._config)
            learn_set_ids = [
                row["id"] for row in store.list_manifests()
                if row["id"] != trajectory_id
                and (store.local / row["id"] / "mined").is_dir()
            ]
            exam_report_path = str(grading.grade_exam(
                trajectory_id, str(checkout), bank_head_before,
                str(graders_root), learn_set_ids,
            ))
            print(f"  Exam report: {exam_report_path}")
            status.note(f"exam graded ({exam_report_path})")

        # --- the lesson ---
        status.phase("lesson")
        frame = UpdateFrame(store, self._config)
        run_dir = frame.run_update(
            [{"trajectory": trajectory_id,
              "hindcast_report": exam_report_path}]
            if exam_report_path else
            [{"trajectory": trajectory_id}],
            learning_config["update_crew"]["run_root"],
            version,
        )
        bank_head_after = self._bank_head()

        # --- what changed (derived from the bank itself, never trusted) ---
        cards_created: List[str] = []
        cards_updated: List[str] = []
        if bank_head_after != bank_head_before:
            diff = subprocess.run(
                ["git", "--git-dir", str(self._bank_home), "diff",
                 "--name-status", bank_head_before, bank_head_after,
                 "--", "insights", "procedures"],
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
            for line in diff:
                change_status, _, path = line.partition("\t")
                if not path.endswith(".md") or path.endswith("index.md"):
                    continue
                # insights/<name>.md -> stem; procedures/<name>/card.md
                # -> the directory name (the card's identity).
                parts = Path(path).parts
                name = (
                    Path(path).parent.name
                    if parts[0] == "procedures" and parts[-1] == "card.md"
                    else Path(path).stem
                )
                if change_status.startswith("A"):
                    cards_created.append(name)
                elif change_status.startswith("M"):
                    cards_updated.append(name)

        status.note(
            f"lesson landed: {len(cards_created)} created, "
            f"{len(cards_updated)} updated; bank "
            f"{bank_head_before[:8]} -> {bank_head_after[:8]}"
        )

        # --- push (to the bank's own origin; preflighted at learn() start) ---
        status.phase("push")
        pushed = False
        if should_push:
            subprocess.run(
                ["git", "--git-dir", str(self._bank_home), "push", "origin",
                 "main", "--tags"],
                check=True,
            )
            pushed = True

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        status.done(
            cards={
                "created": sorted(cards_created),
                "updated": sorted(cards_updated),
            },
            bank_head_after=bank_head_after,
            pushed=pushed,
        )
        if pushed:
            print(f"lesson banked and pushed to {origin}")
        else:
            print("lesson banked locally · to share: kapso bank connect <url>")
        return LessonResult(
            trajectory_id=trajectory_id,
            bank_head_before=bank_head_before,
            bank_head_after=bank_head_after,
            cards_created=sorted(cards_created),
            cards_updated=sorted(cards_updated),
            exam_report_path=exam_report_path,
            lesson_report_path=str(Path(run_dir) / "report.md"),
            metadata={
                "learner_version": version,
                "pushed": pushed,
                "duration_minutes": round(duration / 60, 1),
                "status_path": str(status.path),
            },
        )

    def build(
        self,
        brief: Union[str, Brief, None] = None,
        *,
        evaluation: Optional[str] = None,
        data: Optional[str] = None,
        repo: Optional[str] = None,
        output: Optional[str] = None,
        budget: Optional[Budget] = None,
        resume: bool = False,
        on_status: Optional[Any] = None,
        iteration_evaluator: Optional[IterationEvaluator] = None,
        iteration_evaluator_failure_policy: str = "record",
        # Engine knobs that later packages retire: the harness package
        # takes over context and additional_context, the experience
        # package serving_scope, the config package mode.
        mode: Optional[str] = None,
        coding_agent: Optional[str] = None,
        context: Optional[List[Any]] = None,
        additional_context: str = "",
        serving_scope: Optional[Dict[str, str]] = None,
    ) -> Solution:
        """Build software that meets the brief, by experiment: propose a
        candidate, implement it on its own branch, measure it, keep the
        best, repeat until the goal is met or the budget is spent.

        Args:
            brief: What to build: a sentence, or a `Brief` with the metric,
                the baseline, the target and the rules. A string becomes a
                brief with only an objective. The whole brief reaches the
                engine, never clipped. Left out only on a resume, which
                takes it from the checkpoint.
            evaluation: Directory holding the evaluation; copied to
                `kapso_evaluation/` in the workspace and integrity-protected,
                so a candidate that edits it is rejected.
            data: Directory holding the data; copied to `kapso_datasets/`.
            repo: The starting repository: a local path (copied, never
                modified) or a GitHub URL (cloned). None starts empty, or
                from a workflow the knowledge graph knows.
            output: The campaign directory, the solution's `trace`. A
                fresh campaign needs it empty; a resume needs it to hold
                the campaign.
            budget: What the build may spend. Its set fields win over the
                brief's budget; on a resume the launch's values fill what
                is still unset; the config's defaults fill the rest.
            resume: Continue the campaign in `output`: its workspace and a
                compatible checkpoint must exist. Settings the checkpoint
                fingerprints (mode, coding agent, evaluation, config,
                knowledge index) must match the launch's; a disagreement
                is refused by name.
            on_status: Called with the status dict after every status
                write and heartbeat.
            iteration_evaluator: Callback that evaluates each finalized
                candidate in an isolated detached worktree;
                `iteration_evaluator_failure_policy` is `record` (store
                the error on the candidate) or `raise` (stop the run).

        Returns:
            The `Solution`: the delivered candidate, its measurement and
            the account of the campaign. It is also written to
            `<output>/.kapso/solution.json`, so `Solution.open(output)`
            reads it from any process.
        """
        if isinstance(brief, str):
            brief = Brief(objective=brief)
        elif brief is not None and not isinstance(brief, Brief):
            raise TypeError(
                f"brief must be a string or a Brief, got {type(brief).__name__}"
            )
        if brief is None and not resume:
            raise ValueError(
                "build() needs a brief: a sentence or a Brief; only a resume "
                "may leave it out, and then it comes from the checkpoint"
            )
        # Absolute from here on: the workspace, its sessions and the record
        # are addressed from directories other than the launch's (a session
        # clone commits its run data by path, a resume runs from anywhere),
        # and a relative `output` broke the first session close on the
        # fresh-machine proof run. A repository URL is left as it is.
        eval_dir, data_dir, output_path = _absolute(evaluation), _absolute(data), _absolute(output)
        initial_repo = (
            repo if repo is None or self._is_github_url(repo) else _absolute(repo)
        )
        for label, directory in (("evaluation", eval_dir), ("data", data_dir)):
            if directory is not None and not Path(directory).is_dir():
                raise FileNotFoundError(f"{label} directory not found: {directory}")
        if initial_repo is not None and not self._is_github_url(initial_repo) \
                and not Path(initial_repo).is_dir():
            raise FileNotFoundError(f"repo directory not found: {initial_repo}")
        checkpoint = None
        record = None
        if resume:
            self._validate_resume_workspace(output_path)
            # A resume without a checkpoint is refused by the orchestrator
            # with its own message; here the checkpoint is read when it
            # exists, for the brief and the harness comparison.
            store = RunCheckpointStore(output_path)
            checkpoint = store.load() if store.exists() else None
            if brief is None:
                if checkpoint is None:
                    checkpoint = store.load()
            if brief is None:
                # The checkpoint's goal is the brief as the launch rendered
                # it, so the one grammar reads it back; it comes first so
                # its budget takes part in the merge below.
                brief = Brief.parse(
                    checkpoint.goal,
                    source=str(Path(output_path) / ".kapso" / "run_state.json"),
                )
        spend = (budget or Budget()).merged_over(brief.budget)
        max_iterations = spend.experiments
        time_budget_minutes = spend.minutes
        cost_budget = spend.usd
        finalization_reserve_minutes = spend.reserve_minutes
        if resume:
            # A resume needs the launch's own arguments. The launch record
            # holds them, so a bare `kapso build --output <dir> --resume`
            # works; anything passed explicitly must agree with the record
            # where the checkpoint fingerprints it, and a disagreement is
            # named here rather than surfacing as a bare fingerprint
            # mismatch from the checkpoint.
            record = read_launch_record(output_path)
            if record is not None:
                # The campaign's own .env, from wherever the resume runs;
                # the process environment keeps precedence.
                if record.get("dotenv_path"):
                    load_dotenv(record["dotenv_path"])
                arguments = resume_arguments(record, {
                    "mode": mode,
                    "coding_agent": coding_agent,
                    "eval_dir": eval_dir,
                    "data_dir": data_dir,
                    "additional_context": additional_context,
                    "context": context,
                    "serving_scope": serving_scope,
                    "max_iterations": max_iterations,
                    "time_budget_minutes": time_budget_minutes,
                    "cost_budget": cost_budget,
                    "finalization_reserve_minutes": finalization_reserve_minutes,
                })
                mismatches = launch_mismatches(record, {
                    **arguments,
                    "kg_index": self._kg_index_path,
                    "config_path": self._launch_config_path(),
                })
                if mismatches:
                    changed = "; ".join(
                        f"{key} was {was!r}, now {now!r}"
                        for key, (was, now) in mismatches.items()
                    )
                    raise RunCheckpointIncompatibleError(
                        "This resume changes settings the checkpoint "
                        f"fingerprints: {changed}. Pass the launch's values, or "
                        "start a new campaign in a new output path."
                    )
                mode = arguments["mode"]
                coding_agent = arguments["coding_agent"]
                eval_dir = arguments["eval_dir"]
                data_dir = arguments["data_dir"]
                additional_context = arguments["additional_context"] or ""
                context = arguments["context"]
                serving_scope = arguments["serving_scope"]
                max_iterations = arguments["max_iterations"]
                time_budget_minutes = arguments["time_budget_minutes"]
                cost_budget = arguments["cost_budget"]
                finalization_reserve_minutes = arguments["finalization_reserve_minutes"]
        # The whole brief is the engine's goal text: the judge reads every
        # field, and the checkpoint fingerprints these exact bytes.
        goal_text = brief.render()
        if max_iterations is None:
            max_iterations = DEFAULT_MAX_ITERATIONS
        if eval_dir:
            # Validate caller-owned evaluation inputs before resolving an
            # initial repository or initializing the experiment workspace.
            build_evaluation_manifest(eval_dir)
        # Preflight before the first session is spawned: the campaign's
        # own CLIs and credentials, the gates the strategy names, and the
        # stores this agent's knowledge/experience actually connect to.
        run_preflight(
            "build", self._config,
            mode=mode,
            coding_agent=coding_agent,
            kg_index=self._kg_index_path,
            bank_home=self._bank_home,
        )

        print(f"\n{'='*60}")
        print(f"BUILDING: {brief.objective.splitlines()[0]}")
        print(f"{'='*60}")
        print(f"  Max iterations: {max_iterations}")
        print(f"  Resume: {resume}")
        print(f"  Coding agent: {coding_agent or 'from config'}")
        if eval_dir:
            print(f"  Evaluation: {eval_dir}")
        if data_dir:
            print(f"  Data: {data_dir}")

        # Resolve the starting repository: a URL, a local path, or a
        # workflow search over the knowledge graph.
        resolved_repo = (
            None
            if resume
            else self._resolve_initial_repo(initial_repo, brief.objective)
        )
        if resolved_repo:
            print(f"  Repo: {resolved_repo}")
        print()

        problem = self._build_problem_description(goal_text)

        # Build context string from context items (text, not sources)
        # Context items are converted to strings and appended to additional_context
        context_parts = []
        if context:
            for item in context:
                # Convert each context item to string
                context_parts.append(str(item))

        # Combine knowledge context + caller-provided context + context items
        #
        # Why:
        # - The system already uses `additional_context` to inject KG snippets.
        # - Research ideas should be injected the same way.
        user_context = (additional_context or "").strip()
        items_context = "\n\n".join(context_parts).strip()
        combined_context = "\n\n".join([c for c in [user_context, items_context] if c])

        # Experience serving (learn-api-design.md §4), two-phase: the
        # PLAN (deterministic env + head, no filesystem writes) happens
        # before orchestrator construction so bank_serving can be
        # fingerprinted into the strategy params; the STAGE (bank clone,
        # intro, launch record) happens after construction, once the
        # workspace exists — a seeded workspace must be EMPTY at
        # construction, so nothing may touch it earlier. Serving off, or
        # no bank -> byte-identical to the pre-serving path.
        serving_plan = None
        serving = None
        serving_coords = None
        if (
            ((self._config.get("learning") or {}).get("serving") or {})
            .get("enabled")
            and self._bank_home is not None
            and self._bank_home.exists()
        ):
            output_path = output_path or _absolute(os.path.join(
                "tmp", "search_strategy_workspace", uuid.uuid4().hex
            ))
            serving_config = dict(self._config)
            serving_config["learning"] = dict(self._config["learning"])
            serving_config["learning"]["bank"] = {
                **self._config["learning"]["bank"],
                "local_path": str(self._bank_home),
            }
            serving_coords = serving_scope or {
                "family": (
                    mode or self._config.get("default_mode", "GENERIC")
                ).lower()
            }
            serving_plan = plan_campaign_serving(
                serving_config, serving_coords, output_path
            )
            self._serving_config = serving_config

        # The harness: the loaded one wins over the brief's line (as call
        # arguments win for budgets); a resume with none loaded takes the
        # launch record's source first (absolute, resolvable from any
        # directory), then the brief's line. A resume compares the hash
        # with the checkpoint's and refuses a changed harness by name.
        harness = self._harness
        if harness is None and record is not None and record.get("harness"):
            harness = load_harness(record["harness"]["source"], settings=self._harness_settings)
        if harness is None and brief.harness:
            harness = load_harness(brief.harness, settings=self._harness_settings)
        if checkpoint is not None:
            recorded = checkpoint.harness
            changed = (recorded is None) != (harness is None) or (
                recorded is not None and recorded["hash"] != harness.hash
            )
            if changed:
                raise RunCheckpointIncompatibleError(resume_refusal(recorded, harness))
        if harness is not None:
            if harness is self._harness:
                # The directory as it is at the call, not at the load: an
                # edit since changes the hash, a fix since clears a row.
                # The object keeps the fresh handle.
                harness = reload_harness(harness, settings=self._harness_settings)
                self._harness = harness
            unmet = harness.missing_for(BUILD_MODULES)
            if unmet:
                raise HarnessError(unmet_message(harness, unmet, "build"))
            overrode = self._harness is not None and brief.harness and brief.harness != harness.source
            print(
                f"  Harness: {harness.label()} from {harness.source}"
                + (f" (loaded; wins over the brief's line {brief.harness!r})" if overrode else "")
            )
            added = harness.sessions_added()
            print(f"  Harness sessions: {'; '.join(added) if added else 'none (pages and attachments only)'}")
            for line in advisory_lines(harness, BUILD_MODULES):
                print(line)

        # Create problem handler with all options
        handler = GenericProblemHandler(
            problem_description=problem,
            eval_dir=eval_dir,
            data_dir=data_dir,
            additional_context=combined_context,
        )

        # Create orchestrator
        orchestrator = OrchestratorAgent(
            handler,
            config_path=self.config_path,
            mode=mode,
            coding_agent=coding_agent,
            is_kg_active=self.knowledge_search.is_enabled(),
            knowledge_search=self.knowledge_search if self.knowledge_search.is_enabled() else None,
            # The orchestration layer owns the experiment workspace (a git
            # repo with branches); `output` IS that workspace, so the
            # solution's trace is a real git repo with the record under
            # .kapso/.
            workspace_dir=output_path,
            resume=resume,
            harness=harness,
            iteration_evaluator=iteration_evaluator,
            iteration_evaluator_failure_policy=(
                iteration_evaluator_failure_policy
            ),
            initial_repo=resolved_repo,
            eval_dir=eval_dir,
            data_dir=data_dir,
            goal=goal_text,
            strategy_params_overrides=_memory_overrides(
                serving_plan, self._kg_index_path
            ),
        )

        # Stage serving now that the workspace exists (see the plan/stage
        # note above), and inject the intro into the problem context —
        # the handler reads additional_context lazily at solve time.
        if serving_plan is not None:
            serving = stage_serving(
                self._serving_config, serving_coords, serving_plan
            )
            # Fail loud rather than lie: the intro instructs sessions to
            # call the three bank tools, so the gate that provides them
            # must have resolved. A silently-unmounted gate produced an
            # intro advertising tools no session had (E2E review
            # 2026-08-24, blocker 1).
            mounted = orchestrator.search_strategy.ideation_gates
            if "bank" not in mounted:
                raise RuntimeError(
                    "serving staged but the 'bank' gate is not mounted in "
                    f"ideation gates {mounted} — the intro would advertise "
                    "tools the sessions do not have"
                )
            handler.additional_context = "\n\n".join(
                [c for c in [handler.additional_context, serving["intro"]] if c]
            )
            print(f"  Knowledge bank: serving at head {serving['bank_head']}")
            print(f"  Bank tools mounted in gates: {mounted}")

        # On a fresh campaign, record the launch so a resume (`kapso build
        # --resume`, `kapso inbox reply`) continues with the launch's own
        # brief and flags without the person retyping anything; with the
        # inbox on (docs/research/evolve-hub-design.md v4), also register
        # the campaign so `kapso inbox` can list it.
        inbox_block = (
            load_mode_config(self.config_path, mode).get("inbox") or {}
        )
        if not resume:
            workspace_dir = orchestrator.search_strategy.workspace.workspace_dir
            write_launch_record(workspace_dir, {
                "brief": brief.to_dict(),
                "harness": harness.ref_dict() if harness is not None else None,
                "config_path": _absolute(self._launch_config_path()),
                "kg_index": _absolute(self._kg_index_path),
                "mode": mode,
                "coding_agent": coding_agent,
                "output_path": str(Path(workspace_dir).resolve()),
                "max_iterations": max_iterations,
                "time_budget_minutes": time_budget_minutes,
                "cost_budget": cost_budget,
                "finalization_reserve_minutes": finalization_reserve_minutes,
                "eval_dir": _absolute(eval_dir),
                "data_dir": _absolute(data_dir),
                "additional_context": additional_context,
                "context": (
                    list(context)
                    if context and all(isinstance(item, str) for item in context)
                    else None
                ),
                "serving_scope": serving_scope,
                "resumable_from_inbox": (
                    iteration_evaluator is None
                    and all(isinstance(item, str) for item in (context or []))
                ),
                "dotenv_path": find_dotenv(usecwd=True),
            })
            if inbox_block.get("enabled"):
                register_campaign(inbox_block["registry"], workspace_dir, brief.objective)

        # Run experimentation
        print("Running experiments...")
        solve_result = orchestrator.solve(
            experiment_max_iter=max_iterations,
            time_budget_minutes=time_budget_minutes,
            cost_budget=cost_budget,
            finalization_reserve_minutes=finalization_reserve_minutes,
            on_status=on_status,
        )

        # The deliverable: the strategy checks the workspace out at the
        # delivered candidate's branch (None when nothing succeeded), and
        # the registry head says which evaluator measured it.
        strategy = orchestrator.search_strategy
        campaign = Path(strategy.workspace.workspace_dir).resolve()
        best_branch = strategy.checkout_to_best_experiment_branch()
        head = EvaluationRegistry(str(campaign)).head()
        # The judge's words on the delivered candidate; with nothing
        # delivered, the last judgment says why (the third proof run
        # delivered node 0 and reported node 1's failed judgment).
        delivered = strategy.get_deliverable_experiment()
        feedback = (
            delivered.feedback if delivered is not None
            else solve_result.final_feedback.feedback
            if solve_result.final_feedback else None
        )
        solution = Solution(
            brief=brief,
            campaign=campaign,
            branch=best_branch,
            commit=_git_rev(campaign, "HEAD") if best_branch else None,
            base_commit=_git_rev(campaign, "main"),
            score=strategy.get_deliverable_score(),
            goal_achieved=bool(
                solve_result.final_feedback and solve_result.final_feedback.stop
            ),
            stopped_reason=solve_result.stopped_reason,
            stop_detail=solve_result.stop_detail,
            experiments=solve_result.iterations_run,
            experiments_total=solve_result.cumulative_iterations,
            cost_usd=float(solve_result.total_cost),
            # The inbox: what the person must answer when the campaign
            # paused for them (empty otherwise).
            requests=list(solve_result.requests),
            feedback=feedback,
            evaluator=(
                EvaluatorRef(
                    version=head.version,
                    evaluator_id=head.evaluator_id,
                    provenance=head.provenance,
                )
                if head else None
            ),
            harness=harness.ref() if harness is not None else None,
            experience=[],
            rejected_candidates=sum(
                not node.evaluation_valid
                for node in strategy.get_experiment_history()
            ),
            callback_metrics=dict(
                getattr(solve_result.best_experiment, "metrics", {}) or {}
            ),
            callback_primary_metric=getattr(
                solve_result.best_experiment, "primary_metric", None
            ),
            # Memory provenance (design §8.2): the exact stores this
            # solution drew on.
            knowledge_index=self._kg_index_path,
            experience_head=serving["bank_head"] if serving else None,
        )
        solution.save()

        print(f"\n{'='*60}")
        print("Build complete")
        print(f"{'='*60}")
        print(solution.explain())
        # Every gate call across the campaign's nodes, per gate and tool,
        # and what the metered gates reported spending.
        campaign_phases = {
            f"{node.node_id}:{phase}": values
            for node in strategy.get_experiment_history()
            for phase, values in node.phase_telemetry.items()
        }
        knowledge = knowledge_summary(campaign_phases)
        if knowledge:
            print(f"Knowledge consulted: {knowledge}")
        credits = credits_summary(campaign_phases)
        if credits:
            print(f"Knowledge credits: {credits}")
        # The campaign's platform spend against its budget, the same
        # renderer as the watch bar, so the two never drift.
        if solve_result.platform_budget is not None:
            print(f"Platform cost: {platform_cost_summary(solve_result.platform_budget)}")

        return solution

    # =========================================================================
    # THE INBOX (docs/research/evolve-hub-design.md v4)
    # =========================================================================

    @staticmethod
    def inbox(campaign: str) -> List[Request]:
        """The campaign's open requests, oldest first — what the person
        must answer before it continues. Empty when nothing waits."""
        requests = load_requests(inbox_path(campaign))
        return sorted(
            (request for request in requests.values() if request.open),
            key=lambda request: request.id,
        )

    @staticmethod
    def inbox_ideas(campaign: str) -> Dict[int, str]:
        """One line per node of the campaign — the `for` row of a request
        — read from the checkpoint. Empty without a checkpoint."""
        store = RunCheckpointStore(campaign)
        if not store.exists():
            return {}
        nodes = store.load().strategy_state.get("node_history") or []
        return {
            int(node["node_id"]): idea_line(str(node.get("solution", "")))
            for node in nodes
        }

    @classmethod
    def reply(
        cls, campaign: str, request_id: int, note: str = "", *,
        allow_secret: bool = False,
    ) -> Optional[Solution]:
        """Answer a request and, when the node that asked has every request
        answered, resume the campaign in this process: the session that
        asked is continued with the reply. Returns the campaign's result,
        or None when it could not be resumed here (another request still
        open, or a campaign started from a script with a callback — resume
        it from the script with resume=True).

        Refuses while a live process holds the campaign, so nothing runs
        twice, and refuses a note shaped like a credential unless
        allow_secret is True (replies are plain text handed to the coder;
        the value belongs in the .env the fix names). An empty note means
        "done"."""
        campaign_dir = str(Path(campaign).resolve())
        if not Path(campaign_dir, ".kapso").is_dir():
            raise FileNotFoundError(
                f"{campaign_dir} is not a campaign directory on this machine"
            )
        status_file = Path(campaign_dir) / ".kapso" / "status.json"
        if status_file.is_file() and OperationStatusView(status_file).alive:
            pid = OperationStatusView(status_file).data.get("pid")
            raise RuntimeError(
                f"{campaign_dir} is running (pid {pid}); wait for it to pause "
                "before replying"
            )
        path = inbox_path(campaign_dir)
        request = record_reply(path, request_id, note, allow_secret=allow_secret)
        print(f"#{request_id} answered.")
        still_open = sorted(
            other.id
            for other in load_requests(path).values()
            if other.node == request.node and other.open
        )
        if still_open:
            print(
                f"{', '.join(f'#{i}' for i in still_open)} still open, so node "
                f"{request.node} waits; nothing else to run."
            )
            return None
        record = read_launch_record(campaign_dir)
        if record is None or not record.get("resumable_from_inbox"):
            print(
                f"Recorded. This campaign cannot be resumed from the inbox "
                "(started from a script with a callback, or before the inbox "
                "existed) — resume it from your script with resume=True."
            )
            return None
        checkpoint = RunCheckpointStore(campaign_dir).load()
        remaining = max(
            1, int(record["max_iterations"]) - int(checkpoint.completed_iterations)
        )
        print(
            f"Resuming {campaign_dir}: continuing node {request.node}'s session. "
            "Ctrl-C stops it; resume later with kapso build --output "
            f"{campaign_dir} --resume"
        )
        # Everything else a resume needs comes from the launch record,
        # its .env included: a reply may run far from the launch directory.
        if record.get("dotenv_path"):
            load_dotenv(record["dotenv_path"])
        kapso = cls(config=record["config_path"], kg_index=record["kg_index"])
        return kapso.build(
            output=campaign_dir,
            budget=Budget(experiments=remaining),
            resume=True,
        )

    def _launch_config_path(self) -> Optional[str]:
        """The config a launch record names: None for the packaged default.
        The default's path belongs to one install, so recording it would make
        a resume from another install (or after an upgrade) look like a
        changed config."""
        if self.config_path == DEFAULT_CONFIG_PATH:
            return None
        return self.config_path

    @staticmethod
    def _validate_resume_workspace(output_path: Optional[str]) -> None:
        """Reject resume requests before they can initialize or mutate a repo."""
        if not output_path:
            raise ValueError("resume=True requires an existing output_path")

        path = Path(output_path).expanduser()
        if not path.is_dir():
            raise FileNotFoundError(
                f"Resume workspace does not exist or is not a directory: {path}"
            )

        if not (path / ".git").is_dir():
            raise ValueError(
                f"Resume workspace is not a Git repository: {path}"
            )
        if git.Repo(str(path), search_parent_directories=False).bare:
            raise ValueError(
                f"Resume workspace must be a non-bare Git repository: {path}"
            )
    
    def deploy(
        self,
        solution: Solution,
        strategy: DeployStrategy = DeployStrategy.AUTO,
        env_vars: Optional[Dict[str, str]] = None,
        coding_agent: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Software:
        """
        Deploy a solution to create running software.

        Uses the deployment pipeline:
        1. Selector: Analyzes solution and selects strategy (if AUTO)
        2. Adapter: Adapts and deploys via coding agent
        3. Runner: Creates execution backend

        Args:
            solution: The Solution from build(), or Solution.open(path)
            strategy: Where to deploy (AUTO, LOCAL, DOCKER, MODAL, BENTOML, LANGGRAPH)
                - AUTO: System analyzes code and chooses best strategy
                - LOCAL: Run as local Python process (fastest)
                - DOCKER: Run in Docker container (isolated)
                - MODAL: Deploy to Modal.com (serverless, GPU)
                - BENTOML: Deploy with BentoML (BentoCloud)
                - LANGGRAPH: Deploy as an agent on LangGraph Platform
            env_vars: Environment variables the software needs at runtime:
                written to `.env` in the adapted workspace, named (never
                valued) in the adapter prompt, and set on the runtimes Kapso
                manages (local process, Docker container)
            coding_agent: The coding agent behind the selector and adapter
                sessions; default from config `deployment.coding_agent`
            model: The model that agent is asked for; default from config
                `deployment.model`
            
        Returns:
            Software instance with unified interface:
            - .run(inputs) -> {"status": "success", "output": ...}
            - .stop() -> cleanup resources
            - .logs() -> execution logs
            - .is_healthy() -> health check
            
        Example:
            solution = kapso.build("Create a trading bot")
            software = kapso.deploy(solution, strategy=DeployStrategy.LOCAL)
            result = software.run({"ticker": "AAPL"})
            software.stop()
        """
        if solution.commit is None:
            raise ValueError(
                f"nothing to deploy: the build in {solution.campaign} delivered no "
                f"candidate (stopped: {solution.stopped_reason})"
            )
        checked_out = _git_rev(solution.campaign, "HEAD")
        if checked_out != solution.commit:
            raise ValueError(
                f"{solution.campaign} is checked out at {checked_out[:12]}, not at "
                f"the delivered candidate {solution.commit[:12]} ({solution.branch}); "
                f"run `git -C {solution.campaign} checkout {solution.branch}` first"
            )
        # The packaged deployment block, with the user config's own block
        # layered over it key by key (the same shape as the inference block).
        deployment = {
            **load_deployment_defaults(),
            **(self._config.get("deployment") or {}),
        }
        coding_agent = coding_agent or deployment["coding_agent"]
        model = model or deployment["model"]
        run_preflight(
            "deploy", self._config,
            strategy=getattr(strategy, "value", str(strategy)),
            coding_agent=coding_agent,
        )
        print(f"\n{'='*60}")
        print(f"DEPLOYING: {solution.brief.objective.splitlines()[0]}")
        print(f"{'='*60}")
        print(f"  Strategy: {strategy}")
        print(f"  Campaign: {solution.campaign}")
        print()
        
        config = DeployConfig(
            solution=solution,
            env_vars=env_vars,
            coding_agent=coding_agent,
            model=model,
        )
        
        return DeploymentFactory.create(strategy, config)
    
    # =========================================================================
    # INITIAL REPO RESOLUTION HELPERS
    # =========================================================================
    
    def _resolve_initial_repo(self, initial_repo: Optional[str], goal: str) -> Optional[str]:
        """
        Resolve initial_repo to a local path.
        
        Handles three cases:
        1. GitHub URL: Clone to temp directory
        2. Local path: Use as-is
        3. None: Search for workflow repo in KG
        
        Args:
            initial_repo: Local path, GitHub URL, or None
            goal: The goal (used for workflow search if initial_repo is None)
            
        Returns:
            Local path to repo, or None if no repo found/provided
        """
        if initial_repo is not None:
            # Check if it's a GitHub URL
            if self._is_github_url(initial_repo):
                return self._clone_github_repo(initial_repo)
            # Assume local path
            return initial_repo
        
        # No initial_repo provided - search for workflow repo
        return self._search_workflow_repo(goal)
    
    def _is_github_url(self, path: str) -> bool:
        """Check if path is a GitHub URL."""
        return (
            path.startswith("https://github.com/") or 
            path.startswith("git@github.com:") or
            path.startswith("http://github.com/")
        )
    
    def _clone_github_repo(self, url: str) -> str:
        """
        Clone a GitHub repository to a temporary directory.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Local path to cloned repository
        """
        temp_dir = tempfile.mkdtemp(prefix="kapso_repo_")
        print(f"  Cloning {url}...")
        # A clone that fails propagates: a build must not start from an
        # empty repository when the person named one.
        git.Repo.clone_from(url, temp_dir)
        print(f"  Cloned to: {temp_dir}")
        return temp_dir
    
    def _search_workflow_repo(self, goal: str) -> Optional[str]:
        """
        Search for a relevant workflow repository in the Knowledge Graph.
        
        Args:
            goal: The goal to search for
            
        Returns:
            Local path to cloned workflow repo, or None if not found
        """
        # Only search if KG is enabled
        if not self.knowledge_search.is_enabled():
            print("  No KG index - skipping workflow search")
            return None
        
        print("  Searching for relevant workflow...")
        workflow_search = WorkflowRepoSearch(kg_search=self.knowledge_search)
        result = workflow_search.search(goal, top_k=1)
        if not result.is_empty and result.top_result.github_url:
            starter_url = result.top_result.github_url
            print(f"  Found workflow repo: {starter_url}")
            return self._clone_github_repo(starter_url)
        print("  No matching workflow found")
        return None
    
    def _build_problem_description(self, goal: str) -> str:
        """Build the full problem description for the orchestrator."""
        return f"# Goal\n{goal}"
    


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

__all__ = [
    "Kapso",
    "KGIndexError",
    "Source",
    "Brief",
    "Budget",
    "Solution",
    "Software",
    "DeployStrategy",
    "DeployConfig",
    "DeploymentFactory",
    "ResearchFindings",
    "IterationEvaluator",
]
