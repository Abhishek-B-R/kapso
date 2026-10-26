# Generic Problem Handler
#
# A flexible problem handler for any arbitrary problem.
# In the new design, the developer agent is responsible for building and
# running evaluation. This handler provides problem context.
#
# Usage:
#     from kapso.environment.handlers.generic import GenericProblemHandler
#     
#     handler = GenericProblemHandler(
#         problem_description="Build a web scraper...",
#     )

import os
from typing import Any, Dict, Optional

from kapso.environment.handlers.base import ProblemHandler


class GenericProblemHandler(ProblemHandler):
    """
    Generic problem handler for any arbitrary problem.
    
    In the new design:
    - Developer agent builds evaluation in kapso_evaluation/
    - Developer agent runs evaluation and reports results
    - FeedbackGenerator decides when to stop
    
    This handler provides:
    - Problem context/description
    
    Args:
        problem_description: Main problem description/prompt
        eval_dir: Optional evaluation directory path (copied to kapso_evaluation/)
        data_dir: Optional data directory path (copied to kapso_datasets/)
        
    Examples:
        # Simple - just provide problem description
        handler = GenericProblemHandler(
            problem_description="Write a prime number finder..."
        )
        
        # With eval and data directories
        handler = GenericProblemHandler(
            problem_description="Build a classifier...",
            eval_dir="./evaluation/",
            data_dir="./datasets/",
        )
    """
    
    # Always maximize scoring for generic handler
    maximize_scoring: bool = True
    
    def __init__(
        self,
        problem_description: str,
        eval_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
    ):
        """The brief as the engine's problem text, with where the
        evaluation and the data live when they were provided."""
        self.problem_description = problem_description
        self.eval_dir = eval_dir
        self.data_dir = data_dir
        self._problem_context = self._build_problem_context()

    def _build_problem_context(self) -> str:
        """The brief and the two reference lines, nothing else: the
        evaluation contract is the implementation prompt's, rendered once
        (docs/plans/redesign/wp4-config.md, the problem text)."""
        references = []
        if self.eval_dir and os.path.exists(self.eval_dir):
            references.append("The evaluation is provided in `kapso_evaluation/`.")
        if self.data_dir and os.path.exists(self.data_dir):
            references.append("The data is provided in `kapso_datasets/`.")
        parts = [self.problem_description, *(["", *references] if references else [])]
        return "\n".join(parts)
    
    def get_problem_context(self, budget_progress: float = 0, **kwargs) -> str:
        """Return problem context."""
        return self._problem_context
    
    def final_evaluate(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Final evaluation - returns empty dict (no separate test set)."""
        return {}
