"""A real `Kapso()` is whole: every attribute a verb reads is set by the
constructor, including the ones initialised last (the first proof review
found `_web_researcher` stranded after a method was inserted into the
constructor's body, so `research()` raised AttributeError)."""

from kapso import Kapso


def test_a_constructed_kapso_has_every_lazy_attribute():
    kapso = Kapso()
    assert kapso._web_researcher is None
    assert kapso.harness is None and kapso._harness is None
    assert isinstance(kapso._harness_settings, dict) and "store" in kapso._harness_settings
    assert kapso.experience == [] and "banks" in kapso._experience_settings
    # `bank=` moves where `mine` lives.
    assert Kapso(bank="/somewhere/else/bank.git")._experience_settings["bank_home"] == "/somewhere/else/bank.git"
