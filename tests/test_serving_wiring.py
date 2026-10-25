# Serving-live wiring tests: the launch-side plan and staging from the
# loaded sources, the gate env threading, the context-slot replacement,
# and the judge's citation field (Rule 9: the regressions are a loaded
# source silently unserved, two banks collapsing into one clone, an index
# the search gates cannot find, the gate resolving without its campaign
# env, static notes surviving a live brief, and load-bearing citations
# dropped on the floor).

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from benchmarks.relbench.context import (
    FEATURE_ENGINEERING_NOTE,
    knowledge_section,
)
from kapso.execution.search_strategies.generic.feedback_generator.feedback_generator import (
    FeedbackGenerator,
    FeedbackResult,
)
from kapso.experience import (
    ExperienceError,
    ExperienceSource,
    ExperienceStore,
    IndexRecord,
    parse_experience_reference,
    resolve_source,
)
from kapso.gated_mcp.presets import get_mcp_config
from kapso.learning.serving_launch import (
    plan_campaign_serving,
    prepare_campaign_serving,
    task_coordinates,
)
from kapso.learning.update_frame import init_bank
from tests.handles_support import git
from tests.test_bank_retriever import card_text
from tests.test_experience_reference import bank_home, settings_for

TASK = task_coordinates("trading")


def seeded_home(home: Path, cards) -> Path:
    """A bank home with `cards` (name -> text) as its founding state."""
    init_bank(str(home))
    work = home.parent / (home.name + "-seed")
    git(home.parent, "clone", "-q", str(home), str(work))
    for name, text in cards.items():
        (work / "insights" / f"{name}.md").write_text(text)
    listing = "\n".join(f"- [{n}]({n}.md) — hero" for n in cards)
    (work / "insights" / "index.md").write_text("# Insights\n" + listing + "\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "founding cards")
    git(work, "push", "-q", "origin", "main")
    return home


def load(tmp_path, raw):
    settings = settings_for(tmp_path)
    reference = parse_experience_reference(raw, indexes_root=Path(settings["indexes"]), cwd=tmp_path)
    return resolve_source(reference, settings=settings)


def index_source(tmp_path, name, pages=3):
    settings = settings_for(tmp_path)
    store = ExperienceStore(settings["banks"], settings["indexes"])
    store.write_index_record(IndexRecord(
        name=name, id=f"id-{name}", created_at="2026-10-25T12:00:00+00:00", source="https://github.com/org/x",
        search_backend="kg_graph_search", backend_refs={"collection": name}, page_count=pages, path=store.index_dir(name),
    ))
    return load(tmp_path, name)


def head_of(path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()


def test_one_bank_is_staged_pinned_with_its_intro(tmp_path):
    seeded_home(tmp_path / "bank.git", {"a-card": card_text("a-card")})
    work_dir = tmp_path / "work"
    serving = prepare_campaign_serving([load(tmp_path, "mine")], TASK, work_dir, 1)
    env = serving["bank_serving"]
    [entry] = json.loads(env["KAPSO_BANKS"])
    # the intro names the source with its served count, its pinned head
    # and the three tools — never a card's content (the agent selects)
    assert "1 card measured by you, under the trading harness" in serving["intro"]
    assert entry["head"][:12] in serving["intro"]
    assert "bank_index()" in serving["intro"]
    assert "bank_get_card_with_evidence(" in serving["intro"]
    assert "[card:a-card]" not in serving["intro"]
    # the banner lines are the intro's source lines; the intro is staged
    # where the prompts read it
    assert len(serving["lines"]) == 1 and f"- {serving['lines'][0]}" in serving["intro"]
    assert Path(serving["intro_path"]) == work_dir / ".kapso" / "serving" / "intro.md"
    assert Path(serving["intro_path"]).read_text() == serving["intro"] + "\n"
    # the record carries the task and the sources, inside the harvested tree
    record = yaml.safe_load(Path(serving["record_path"]).read_text())
    assert record["task"] == TASK
    assert [(s["reference"], s["head"], s["cards"]) for s in record["sources"]] == [
        ("mine", entry["head"], 1),
    ]
    assert Path(serving["record_path"]).parent == work_dir / ".kapso" / "serving"
    # the gate env is complete and points into the work dir
    assert entry["provenance"] == "measured by you" and entry["scope"] == "harness"
    assert env["KAPSO_TASK_HARNESS"] == "trading" and env["KAPSO_PROBE_BUDGET"] == "1"
    assert env["KAPSO_SERVING_PULL_LOG"] == str(work_dir / ".kapso" / "serving" / "serving-pull.jsonl")
    # the checkout is PINNED at the source's head
    assert head_of(entry["dir"]) == entry["head"]
    assert Path(entry["dir"]).parent == work_dir / ".kapso" / "serving" / "banks"


def test_two_banks_are_two_clones_and_one_intro(tmp_path):
    seeded_home(tmp_path / "bank.git", {"a-card": card_text("a-card")})
    team = seeded_home(
        tmp_path / "team" / "bank.git",
        {"b-card": card_text("b-card"), "c-card": card_text("c-card")},
    )
    sources = [load(tmp_path, "mine"), load(tmp_path, str(team))]
    serving = prepare_campaign_serving(sources, TASK, tmp_path / "work", 1)
    entries = json.loads(serving["bank_serving"]["KAPSO_BANKS"])
    assert [e["reference"] for e in entries] == ["mine", str(team)]
    assert len({e["dir"] for e in entries}) == 2
    for entry in entries:
        assert head_of(entry["dir"]) == entry["head"]
    assert (Path(entries[1]["dir"]) / "insights" / "c-card.md").is_file()
    assert entries[1]["provenance"] == "measured by others" and entries[1]["scope"] == "all"
    # one intro, one line per source, the tools once
    assert serving["lines"][0].startswith("1 card measured by you, under the trading harness")
    assert serving["lines"][1].startswith(f"2 cards from `{team}`, measured by others, every scope")
    assert serving["intro"].count("bank_index()") == 1
    assert serving["counts"] == {"mine": 1, str(team): 2}


def test_two_banks_that_read_alike_as_names_never_share_a_clone(tmp_path):
    # Regression: `/x/team/a-b.git` and `/x/team-a/b.git` made the same
    # directory name, and the second staging removed the first's clone.
    sources = [
        ExperienceSource(reference=reference, kind="bank", resolved=reference, head="a" * 40,
                         provenance="measured by others", scope="all", path=Path(reference))
        for reference in ("/x/team/a-b.git", "/x/team-a/b.git")
    ]
    plan = plan_campaign_serving(sources, TASK, tmp_path / "work", 1)
    dirs = [Path(entry["dir"]) for entry in plan["banks"]]
    assert len(set(dirs)) == 2
    assert all(d.parent == tmp_path / "work" / ".kapso" / "serving" / "banks" and d.name.startswith("x-team") for d in dirs)


def test_nothing_loaded_is_nothing_staged(tmp_path):
    assert prepare_campaign_serving([], TASK, tmp_path / "w", 1) is None
    assert not (tmp_path / "w").exists()


def test_the_hosted_gate_and_an_index_ride_without_a_bank(tmp_path, monkeypatch):
    monkeypatch.setenv("LEEROOPEDIA_API_KEY", "kpsk_test")
    sources = [load(tmp_path, "leeroopedia"), index_source(tmp_path, "org-x")]
    plan = plan_campaign_serving(sources, TASK, tmp_path / "work", 1)
    # the hosted gate rides as loaded: its URL (the key's placeholder in
    # it) and timeout from the config the source was loaded with
    assert plan["hosted"] == {"url": settings_for(tmp_path)["hosted"]["url"], "tool_timeout_seconds": 600}
    assert plan["banks"] == [] and plan["bank_serving"] == {}
    assert plan["kg_index_path"] == str(Path(settings_for(tmp_path)["indexes"]) / "org-x" / "index.json")
    staged = prepare_campaign_serving(sources, TASK, tmp_path / "work", 1)
    assert "Leeroopedia's pages, reported by others" in staged["intro"]
    assert "the `org-x` corpus (3 pages), reported by others" in staged["intro"]
    assert "bank_index()" not in staged["intro"]
    assert "`idea` and `code` tools" in staged["intro"]
    # the search gates read one index per campaign
    with pytest.raises(ExperienceError, match="one index per campaign"):
        plan_campaign_serving(
            [index_source(tmp_path, "org-x"), index_source(tmp_path, "org-y")], TASK, tmp_path / "work", 1,
        )


def test_bank_serving_env_threads_into_the_gate_server(tmp_path):
    mapping = {
        "KAPSO_BANKS": json.dumps([{
            "reference": "mine", "head": "abc123", "dir": str(tmp_path),
            "provenance": "measured by you", "scope": "harness",
        }]),
        "KAPSO_SERVING_PULL_LOG": str(tmp_path / "pull.jsonl"),
        "KAPSO_TASK_HARNESS": "trading",
        "KAPSO_PROBE_BUDGET": "1",
    }
    mcp_servers, tools = get_mcp_config(
        ["bank"], gate_failure_policy="error", bank_serving=mapping,
    )
    env = mcp_servers["gated-knowledge"]["env"]
    for key, value in mapping.items():
        assert env[key] == value
    assert "bank" in env["MCP_ENABLED_GATES"]
    # without the mapping the gate must not resolve
    mcp_servers, _ = get_mcp_config(
        ["bank"], gate_failure_policy="skip", bank_serving=None,
    )
    assert "gated-knowledge" not in mcp_servers


def test_knowledge_slot_additive_intro_on_static_notes():
    live = knowledge_section("## Experience (measured before)\nSERVED INTRO BODY")
    # additive contract: notes are the permanent base, intro appends after
    assert FEATURE_ENGINEERING_NOTE in live
    assert "SERVED INTRO BODY" in live
    assert live.index(FEATURE_ENGINEERING_NOTE) < live.index("SERVED INTRO BODY")
    fallback = knowledge_section(None)
    assert FEATURE_ENGINEERING_NOTE in fallback
    assert "Experience" not in fallback


def test_judge_parses_cards_load_bearing():
    generator = FeedbackGenerator.__new__(FeedbackGenerator)
    parsed = generator._parse_response(
        "<stop>false</stop><evaluation_valid>true</evaluation_valid>"
        "<score>0.7</score><feedback>keep going</feedback>"
        "<cards_load_bearing>[card:group-relative-standing], "
        "cross-branch-ensemble-candidate</cards_load_bearing>"
    )
    assert parsed.cards_load_bearing == [
        "group-relative-standing", "cross-branch-ensemble-candidate",
    ]
    assert parsed.to_dict()["cards_load_bearing"] == parsed.cards_load_bearing
    # none / absent both mean no attribution — and never a parse failure
    for tail in ("<cards_load_bearing>none</cards_load_bearing>", ""):
        parsed = generator._parse_response(
            "<stop>false</stop><feedback>f</feedback>" + tail
        )
        assert parsed.cards_load_bearing == []
    assert FeedbackResult(stop=False, evaluation_valid=True,
                          feedback="x").cards_load_bearing == []
