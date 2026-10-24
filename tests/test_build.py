# Live tests for Kapso.build().
#
# Both spawn real coding-agent sessions and spend real subscription quota, so
# the whole module carries the `live` marker and is skipped unless --run-live
# is passed.
#
# Run with:
#   pytest tests/test_build.py --run-live -v -s

import pytest

from kapso import Budget, Kapso

pytestmark = pytest.mark.live


def test_build_iris_classifier(tmp_path):
    """Build a simple ML task: Iris classification.

    The coding agent writes both main.py and the evaluation; the feedback
    generator decides when the goal is met.
    """
    solution = Kapso().build(
        "Train an Iris flower classifier using scikit-learn. "
        "Target accuracy > 0.90 on test set.",
        output=str(tmp_path / "iris_classifier"),
        budget=Budget(iterations=5),
    )

    assert solution.trace.is_dir()
    assert solution.iterations >= 1


def test_build_simple_math(tmp_path):
    """Build a numeric optimization task with a checkable target."""
    solution = Kapso().build(
        """
        Find the minimum of the Rosenbrock function: f(x,y) = (1-x)^2 + 100*(y-x^2)^2

        The global minimum is at (1, 1) where f(1,1) = 0.

        Your solution should:
        1. Implement an optimization algorithm (gradient descent, scipy.optimize, etc.)
        2. Print the found minimum point (x, y) and function value

        Target: Find a point where f(x,y) < 0.001
        """,
        output=str(tmp_path / "rosenbrock_min"),
        budget=Budget(iterations=3),
    )

    assert solution.trace.is_dir()
    assert solution.iterations >= 1
