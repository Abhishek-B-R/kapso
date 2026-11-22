"""The graph read that adds each result's connected pages: its failure
reaches the caller instead of reading as a page with no connections
(Rule 2)."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from kapso.knowledge_base.search import kg_graph_search as module
from kapso.knowledge_base.search.base import KGSearchFilters
from kapso.knowledge_base.search.factory import KnowledgeSearchFactory

pytest.importorskip("weaviate")


class OneHitCollection:
    """Answers the hybrid query with a single page."""

    def __init__(self):
        self.query = self

    def hybrid(self, **kwargs):
        hit = SimpleNamespace(
            properties={
                "page_id": "Principle/A",
                "page_type": "Principle",
                "overview": "o",
                "content": "c",
                "domains": [],
            },
            metadata=SimpleNamespace(score=0.9),
        )
        return SimpleNamespace(objects=[hit])


class FailingGraphSession:
    def run(self, query, **params):
        raise RuntimeError("neo4j read failed")


def test_a_failed_connected_pages_read_raises(monkeypatch):
    cls = module.KGGraphSearch
    monkeypatch.setattr(cls, "_initialize_neo4j", lambda self: None)
    monkeypatch.setattr(cls, "_initialize_weaviate", lambda self: None)
    monkeypatch.setattr(module, "make_embedder", lambda params: None)
    search = KnowledgeSearchFactory.create(
        "kg_graph_search", params={"corpus": "index-id"}
    )
    search._embedder = SimpleNamespace(
        embed_query=lambda query: [0.0], close=lambda: None
    )
    collection = OneHitCollection()
    search._weaviate_client = SimpleNamespace(
        collections=SimpleNamespace(get=lambda name: collection),
        close=lambda: None,
    )

    @contextmanager
    def session():
        yield FailingGraphSession()

    search._neo4j_driver = SimpleNamespace(session=session, close=lambda: None)
    assert search.include_connected_pages
    with pytest.raises(RuntimeError, match="neo4j read failed"):
        search.search("q", KGSearchFilters(top_k=3), use_llm_reranker=False)
