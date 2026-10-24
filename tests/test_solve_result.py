# SolveResult, the orchestrator's return: the shape the facade reads.

import unittest

from kapso.execution.search_strategies.generic.feedback_generator.feedback_generator import FeedbackResult
from kapso.execution.orchestrator import SolveResult


class TestSolveResult(unittest.TestCase):
    """Test SolveResult dataclass."""

    def test_solve_result_creation(self):
        """Test creating a SolveResult."""
        from kapso.execution.search_strategies.base import ExperimentResult

        result = SolveResult(
            best_experiment=ExperimentResult(
                node_id=1,
                solution="Test solution",
                score=0.9,
                branch_name="test_branch",
                had_error=False,
            ),
            final_feedback=FeedbackResult(
                stop=True,
                evaluation_valid=True,
                feedback="Done",
                score=0.9,
            ),
            stopped_reason="goal_achieved",
            iterations_run=3,
            total_cost=1.50,
        )

        self.assertEqual(result.stopped_reason, "goal_achieved")
        self.assertEqual(result.iterations_run, 3)
        self.assertEqual(result.total_cost, 1.50)
        self.assertIsNotNone(result.best_experiment)
        self.assertIsNotNone(result.final_feedback)

    def test_solve_result_stopped_reasons(self):
        """Test different stopped reasons."""
        for reason in ["goal_achieved", "max_iterations", "budget_exhausted", "legacy_stop"]:
            result = SolveResult(
                best_experiment=None,
                final_feedback=None,
                stopped_reason=reason,
                iterations_run=1,
                total_cost=0.0,
            )
            self.assertEqual(result.stopped_reason, reason)


if __name__ == "__main__":
    unittest.main()
