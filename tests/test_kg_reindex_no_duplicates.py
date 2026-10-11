"""Weaviate lookups by page id act on that exact page, never on a sibling that
shares its tokens: a re-index replaces the page's object instead of adding a
duplicate, and existence checks and edits leave the siblings alone."""

import re
import uuid
from types import SimpleNamespace

from kapso.knowledge_base.search.base import KGEditInput, WikiPage
from kapso.knowledge_base.search.kg_graph_search import KGGraphSearch


def _tokens(text):
    """Weaviate's word tokenization: lowercase alphanumeric runs."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class _FakeQuery:
    """`equal` on a word-tokenized text property matches every object that
    contains all the filter's tokens, as the real store does."""

    def __init__(self, collection):
        self.collection = collection

    def fetch_objects(self, *, filters, limit, return_properties=None):
        wanted = _tokens(filters.value)
        matched = [
            obj for obj in self.collection.objects
            if wanted <= _tokens(obj.properties[filters.target])
        ]
        return SimpleNamespace(objects=matched[:limit])


class _FakeData:
    def __init__(self, collection):
        self.collection = collection

    def insert(self, *, properties, vector):
        self.collection.objects.append(SimpleNamespace(uuid=str(uuid.uuid4()), properties=properties))

    def delete_many(self, *, where):
        """Only deletion by id is supported: a property filter would be the
        token-matching delete this test exists to rule out."""
        assert where.target == "_id", where.target
        gone = {str(value) for value in where.value}
        self.collection.objects = [obj for obj in self.collection.objects if obj.uuid not in gone]

    def update(self, *, uuid, properties, vector=None):
        obj = next(obj for obj in self.collection.objects if obj.uuid == uuid)
        obj.properties = {**obj.properties, **properties}


class _FakeCollection:
    def __init__(self):
        self.objects = []
        self.data = _FakeData(self)
        self.query = _FakeQuery(self)


class _FakeWeaviate:
    def __init__(self, collection):
        self.collections = SimpleNamespace(get=lambda name: collection)

    def close(self):
        pass


def _page(page_id, overview):
    return WikiPage(
        id=page_id,
        page_type="Principle",
        overview=overview,
        content=f"== Overview ==\n{overview}",
        domains=["Deep_Learning"],
    )


def _search(collection):
    search = object.__new__(KGGraphSearch)
    search._weaviate_client = _FakeWeaviate(collection)
    search._neo4j_driver = None
    search._embedder = None
    search.weaviate_collection = "KGWikiPages"
    search._pages = []
    search._ensure_weaviate_collection = lambda: None
    search._embed_page = lambda page_id, text: [0.1, 0.2, 0.3]
    search._embed = lambda text: [0.1, 0.2, 0.3]
    return search


def test_reindexing_replaces_existing_page_and_keeps_other_pages():
    collection = _FakeCollection()
    search = _search(collection)

    search._index_to_weaviate([
        _page("Principle/Batch_Size", "old text"),
        _page("Principle/Learning_Rate", "lr"),
        # Shares every token of Principle/Batch_Size: a token-matching delete would take it too.
        _page("Principle/Batch_Size_Schedule", "schedule"),
    ])
    search._index_to_weaviate([_page("Principle/Batch_Size", "new text")])

    by_id = {}
    for obj in collection.objects:
        by_id.setdefault(obj.properties["page_id"], []).append(obj.properties["overview"])
    assert by_id == {
        "Principle/Batch_Size": ["new text"],
        "Principle/Learning_Rate": ["lr"],
        "Principle/Batch_Size_Schedule": ["schedule"],
    }


def test_single_page_reindex_keeps_its_sibling():
    collection = _FakeCollection()
    search = _search(collection)

    search._index_to_weaviate([_page("Workflow/Page", "one"), _page("Workflow/Page_Sibling", "two")])
    assert search._index_single_page_to_weaviate(_page("Workflow/Page", "one again"))

    assert sorted((obj.properties["page_id"], obj.properties["overview"]) for obj in collection.objects) == [
        ("Workflow/Page", "one again"),
        ("Workflow/Page_Sibling", "two"),
    ]


def test_page_exists_is_false_when_only_a_sibling_shares_the_tokens():
    collection = _FakeCollection()
    search = _search(collection)

    search._index_to_weaviate([_page("Principle/Batch_Size_Config", "config")])
    assert not search.page_exists("Principle/Batch_Size")

    search._index_to_weaviate([_page("Principle/Batch_Size", "batch")])
    assert search.page_exists("Principle/Batch_Size")


def test_edit_changes_the_exact_page_even_when_a_sibling_was_indexed_first():
    collection = _FakeCollection()
    search = _search(collection)
    search._index_to_weaviate([_page("Principle/Batch_Size_Config", "config"), _page("Principle/Batch_Size", "batch")])

    assert search.edit(KGEditInput(page_id="Principle/Batch_Size", overview="edited", update_source_files=False))

    assert sorted((obj.properties["page_id"], obj.properties["overview"]) for obj in collection.objects) == [
        ("Principle/Batch_Size", "edited"),
        ("Principle/Batch_Size_Config", "config"),
    ]
