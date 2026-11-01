"""`Kapso.load_experience`: the object's sources in load order, a reference
loaded again replacing its entry, the printed line, scope, and the
reference errors reaching the caller unwrapped."""

import pytest

from kapso.experience import ExperienceError, ExperienceReferenceError
from tests.handles_support import facade
from tests.test_experience_reference import bank_home, settings_for


def kapso_at(tmp_path):
    kapso = facade()
    kapso._experience_settings = settings_for(tmp_path)
    return kapso


def test_sources_are_kept_in_load_order_and_a_reload_replaces(tmp_path, capsys):
    kapso = kapso_at(tmp_path)
    bank_home(tmp_path, cards=2)
    team = bank_home(tmp_path, name="team.git", cards=1)

    mine = kapso.load_experience("mine")
    assert capsys.readouterr().out.strip() == f"Experience: mine at {mine.head[:12]}, 2 cards, measured by you"
    kapso.load_experience(str(team))
    assert [s.reference for s in kapso.experience] == ["mine", str(team)]

    again = kapso.load_experience("mine:all")
    assert [s.reference for s in kapso.experience] == [str(team), "mine"]
    assert kapso.experience[-1].scope == "all" and again.head == mine.head
    assert kapso.experience is not kapso._experience   # a copy, not the object's list


def test_a_bad_reference_or_a_missing_source_is_the_callers_to_see(tmp_path):
    kapso = kapso_at(tmp_path)
    with pytest.raises(ExperienceReferenceError, match="the forms are:"):
        kapso.load_experience("Some Bank")
    with pytest.raises(ExperienceError, match="`kapso experience add mine` creates it"):
        kapso.load_experience("mine")
    assert kapso.experience == []
