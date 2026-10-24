"""The reference grammar and the store: the forms parse as pinned, a path
that does not exist is reported as one and never cloned, a local bare
repository stands in for the remote, `update` moves a branch and leaves a
tag alone, `remove` refuses a path."""

import json
import shutil
from pathlib import Path

import pytest

from kapso.harness.reference import HarnessReference, HarnessReferenceError, parse_reference
from kapso.harness.store import SOURCE_FILE, HarnessStore
from tests.handles_support import git

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


# ----------------------------------------------------------------- the grammar

def test_a_bundled_name_resolves_under_the_bundled_root(tmp_path):
    bundled = tmp_path / "bundled"
    (bundled / "trading").mkdir(parents=True)
    (bundled / "trading" / "harness.yaml").write_text("schema_version: 1\n")
    reference = parse_reference("trading", cwd=tmp_path, bundled_root=bundled)
    assert reference == HarnessReference(raw="trading", kind="bundled", path=bundled / "trading")


def test_a_directory_is_used_in_place_and_made_absolute(tmp_path):
    (tmp_path / "harness" / "trading").mkdir(parents=True)
    reference = parse_reference("./harness/trading", cwd=tmp_path, bundled_root=tmp_path / "none")
    assert reference.kind == "path" and reference.path == (tmp_path / "harness" / "trading").resolve()
    absolute = parse_reference(str(tmp_path / "harness" / "trading"), bundled_root=tmp_path / "none")
    assert absolute.path == reference.path


@pytest.mark.parametrize("text, url, rev, subdirectory", [
    ("git+https://github.com/acme/harnesses@v3#trading", "https://github.com/acme/harnesses", "v3", "trading"),
    ("acme/harnesses@v3#trading", "https://github.com/acme/harnesses.git", "v3", "trading"),
    ("acme/harnesses#trading", "https://github.com/acme/harnesses.git", "HEAD", "trading"),
    ("acme/harnesses@main", "https://github.com/acme/harnesses.git", "main", ""),
    ("https://github.com/acme/harnesses.git", "https://github.com/acme/harnesses.git", "HEAD", ""),
    ("git@github.com:acme/harnesses.git@v3#h/trading", "git@github.com:acme/harnesses.git", "v3", "h/trading"),
    ("ssh://git@github.com/acme/harnesses@release/2", "ssh://git@github.com/acme/harnesses", "release/2", ""),
])
def test_the_git_forms(tmp_path, text, url, rev, subdirectory):
    reference = parse_reference(text, cwd=tmp_path, bundled_root=tmp_path / "none")
    assert reference.kind == "git"
    assert (reference.url, reference.rev, reference.subdirectory) == (url, rev, subdirectory)
    assert reference.slug == "github.com-acme-harnesses"


def test_a_slash_without_rev_or_subdirectory_is_a_path_and_is_never_cloned(tmp_path):
    with pytest.raises(HarnessReferenceError) as caught:
        parse_reference("harness/trading", cwd=tmp_path, bundled_root=tmp_path / "none")
    message = str(caught.value)
    assert message.startswith(f"no directory {tmp_path / 'harness' / 'trading'}")
    assert "the forms are:" in message


def test_a_bare_name_that_is_neither_bundled_nor_a_directory_says_both(tmp_path):
    with pytest.raises(HarnessReferenceError, match="no bundled harness named `trading` and no directory"):
        parse_reference("trading", cwd=tmp_path, bundled_root=tmp_path / "none")


def test_an_empty_or_odd_string_lists_the_forms(tmp_path):
    with pytest.raises(HarnessReferenceError, match="the forms are:"):
        parse_reference("   ", cwd=tmp_path, bundled_root=tmp_path / "none")
    with pytest.raises(HarnessReferenceError, match="not a bundled name or a git reference"):
        parse_reference("Trading Desk", cwd=tmp_path, bundled_root=tmp_path / "none")


# -------------------------------------------------------------------- the store

@pytest.fixture
def remote(tmp_path) -> Path:
    """A repository holding the trading harness under `harnesses/trading`,
    tagged v1 on main, served from a bare clone."""
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    shutil.copytree(TRADING, work / "harnesses" / "trading")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "trading 0.1.0")
    git(work, "tag", "v1")
    bare = tmp_path / "acme-harnesses.git"
    git(tmp_path, "clone", "-q", "--bare", str(work), str(bare))
    return bare


def reference_for(remote: Path, rev: str) -> HarnessReference:
    return parse_reference(f"git+file://{remote}@{rev}#harnesses/trading", bundled_root=remote / "none")


def test_a_git_reference_is_fetched_once_into_the_store(tmp_path, remote):
    store = HarnessStore(tmp_path / "store")
    reference = reference_for(remote, "v1")
    assert not store.is_fetched(reference)
    harness = store.resolve(reference)
    clone = store.clone_dir(reference)
    assert clone.parent == tmp_path / "store"
    assert clone.name.startswith("local-") and clone.name.endswith("-acme-harnesses@v1")
    assert harness == clone / "harnesses" / "trading"
    assert (harness / "harness.yaml").is_file()
    source = json.loads((harness.parent.parent / SOURCE_FILE).read_text())
    assert source["rev"] == "v1" and len(source["commit"]) == 40 and source["remote"] == f"file://{remote}"
    # A second resolve uses the store: the clone's marker is untouched.
    marker = harness.parent.parent / SOURCE_FILE
    before = marker.stat().st_mtime_ns
    assert store.resolve(reference) == harness and marker.stat().st_mtime_ns == before
    assert store.is_fetched(reference)


def test_the_subdirectory_must_hold_a_manifest(tmp_path, remote):
    store = HarnessStore(tmp_path / "store")
    reference = parse_reference(f"git+file://{remote}@v1#harnesses", bundled_root=remote / "none")
    with pytest.raises(HarnessReferenceError, match="no harness.yaml at `harnesses`"):
        store.resolve(reference)


def test_update_moves_a_branch_and_leaves_a_tag_alone(tmp_path, remote):
    store = HarnessStore(tmp_path / "store")
    tag = reference_for(remote, "v1")
    branch = reference_for(remote, "main")
    store.resolve(tag)
    store.resolve(branch)
    first = json.loads((store.clone_dir(branch) / SOURCE_FILE).read_text())["commit"]

    # The author bumps the version on main.
    work = tmp_path / "work"
    page = work / "harnesses" / "trading" / "harness.yaml"
    page.write_text(page.read_text().replace("version: 0.1.0", "version: 0.2.0"))
    git(work, "commit", "-q", "-am", "trading 0.2.0")
    git(work, "push", "-q", str(remote), "main")

    assert store.update(tag) == (store.update(tag)[0], store.update(tag)[0])
    before, after = store.update(branch)
    assert before == first and after != first
    assert "version: 0.2.0" in (store.resolve(branch) / "harness.yaml").read_text()
    assert "version: 0.1.0" in (store.resolve(tag) / "harness.yaml").read_text()


def test_entries_list_every_fetched_harness_with_its_version(tmp_path, remote):
    store = HarnessStore(tmp_path / "store")
    assert store.entries() == []
    store.resolve(reference_for(remote, "v1"))
    [entry] = store.entries()
    assert (entry.name, entry.version) == ("trading", "0.1.0")
    assert entry.reference == f"file://{remote}@v1#harnesses/trading"
    assert entry.path == store.clone_dir(reference_for(remote, "v1")) / "harnesses" / "trading"


def test_remove_deletes_a_clone_and_refuses_a_path(tmp_path, remote):
    store = HarnessStore(tmp_path / "store")
    reference = reference_for(remote, "v1")
    store.resolve(reference)
    assert store.remove(reference) == store.clone_dir(reference)
    assert not store.clone_dir(reference).exists()
    with pytest.raises(HarnessReferenceError, match="nothing fetched"):
        store.remove(reference)
    local = parse_reference(str(TRADING), bundled_root=tmp_path / "none")
    with pytest.raises(HarnessReferenceError, match="is a local path; nothing was fetched"):
        store.remove(local)
    assert TRADING.is_dir()
