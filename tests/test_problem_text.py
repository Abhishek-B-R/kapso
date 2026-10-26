"""The problem text and the evaluation contract (docs/plans/redesign/
wp4-config.md, change 5): the generic handler's context is the brief
and the two reference lines, nothing else; the contract is rendered
once, in the implementation prompt, in three forms; `build()` takes no
context arguments."""

import inspect

from kapso.environment.handlers.base import ProblemHandler
from kapso.environment.handlers.generic import GenericProblemHandler
from kapso.execution.search_strategies.generic.registered_evaluation import (
    deferred_evaluation_instructions,
    evaluation_instructions,
)
from kapso.kapso import Kapso


def test_the_context_is_the_brief_and_the_references(tmp_path):
    assert GenericProblemHandler("# Goal\nRaise AUC").get_problem_context() == "# Goal\nRaise AUC"
    evaluation = tmp_path / "evaluation"
    data = tmp_path / "data"
    evaluation.mkdir()
    data.mkdir()
    both = GenericProblemHandler("# Goal\nRaise AUC", eval_dir=str(evaluation), data_dir=str(data))
    assert both.get_problem_context() == (
        "# Goal\nRaise AUC\n\n"
        "The evaluation is provided in `kapso_evaluation/`.\n"
        "The data is provided in `kapso_datasets/`."
    )
    # A directory that is not there is not named (it is refused earlier).
    absent = GenericProblemHandler("# Goal\nRaise AUC", eval_dir=str(tmp_path / "none"))
    assert absent.get_problem_context() == "# Goal\nRaise AUC"
    # No contract prose and no execution notes in the problem text.
    for text in (both.get_problem_context(), absent.get_problem_context()):
        assert "result.json" not in text and "Execution Notes" not in text


def test_the_contract_has_three_forms():
    registered = evaluation_instructions("python kapso_evaluation/kapso_eval.py", provided=True)
    assert "maintained by the system" in registered and "Run the registered evaluation" in registered

    provided = evaluation_instructions(None, provided=True)
    assert "provided in `kapso_evaluation/`" in provided and "Run it as given" in provided
    assert "Never modify, delete,\n   replace or add evaluator source files" in provided
    assert "result.json" in provided
    assert "build and run evaluation" not in provided and "Create evaluation script" not in provided

    own = evaluation_instructions(None, provided=False)
    assert "You MUST build and run evaluation" in own and "Create evaluation script" in own
    assert "provided in" not in own


def test_the_deferred_contract_keeps_the_three_forms():
    assert "maintained by the system" in deferred_evaluation_instructions("python eval.py")
    provided = deferred_evaluation_instructions(None, provided=True)
    assert "provided in `kapso_evaluation/`" in provided and "Kapso runs it after admission" in provided
    assert "Create `kapso_evaluation/evaluate.py`" in deferred_evaluation_instructions(None)


def test_no_context_arguments():
    parameters = inspect.signature(Kapso.build).parameters
    assert "context" not in parameters and "additional_context" not in parameters
    assert "additional_context" not in inspect.signature(GenericProblemHandler).parameters
    assert not hasattr(ProblemHandler, "additional_context")
