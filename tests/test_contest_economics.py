"""The allocation-grading contract (platform side): the core templates'
critical-path and time-allocation duties. The insured finalization floor
and the handler's deliverable hook were retired with the harness ports
(docs/plans/redesign/wp8-harness-ports.md, change 10): the engine's derived
reserve is the only reserve."""

from kapso.core.prompt_loader import load_prompt


def test_core_templates_carry_the_allocation_contract():
    implementation = load_prompt(
        "execution/search_strategies/generic/prompts/implementation_claude_code.md"
    )
    assert "Identify the critical path" in implementation
    assert "TIME ALLOCATION" in implementation

    feedback = load_prompt(
        "execution/search_strategies/generic/feedback_generator/prompts/feedback_generator.md"
    )
    assert "time-to-first-strong-score" in feedback
    assert "critical-path velocity" in feedback
    assert "counterfactual ledger" in feedback
    assert "never to be traded for speed" in feedback

    selector = load_prompt(
        "execution/search_strategies/generic/prompts/ideation_selector.md"
    )
    assert "Time-to-first-strong-score" in selector
    assert "staged plan beats a monolithic one" in selector
