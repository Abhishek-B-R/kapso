# Search Strategy Factory
#
# Factory for creating search strategies with auto-discovery.

import importlib
from pathlib import Path
from typing import Dict, Type, Any, Optional, List, TYPE_CHECKING
import yaml

from kapso.execution.search_strategies.base import (
    SearchStrategy, 
    SearchStrategyConfig
)
from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.environment.handlers.base import ProblemHandler

if TYPE_CHECKING:
    from kapso.execution.search_strategies.generic import FeedbackGenerator


class SearchStrategyFactory:
    """
    Factory for creating search strategies.
    
    Strategies are auto-discovered from the search_strategies/ directory
    when first accessed; their parameters are the config's
    `search_strategy.params` (docs/reference/configuration.mdx).
    
    Usage:
        # Create strategy
        strategy = SearchStrategyFactory.create("generic", ...)
        
        # List available
        SearchStrategyFactory.list_available()
    """
    
    # Class-level state
    _registry: Dict[str, Type[SearchStrategy]] = {}
    _default_type: str = "generic"
    _initialized: bool = False
    
    
    # =========================================================================
    # Initialization
    # =========================================================================
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """Lazy initialization of registry and configs."""
        if cls._initialized:
            return
        cls._auto_discover()
        cls._initialized = True
    
    @classmethod
    def _auto_discover(cls) -> None:
        """Auto-import all strategy modules in this directory."""
        module_dir = Path(__file__).parent
        
        for py_file in module_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name in ("base.py", "factory.py"):
                continue
            
            module_name = f"kapso.execution.search_strategies.{py_file.stem}"
            try:
                importlib.import_module(module_name)
            except (ImportError, Exception):
                pass
    
    # =========================================================================
    # Registration
    # =========================================================================
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[SearchStrategy]) -> None:
        """Register a strategy class."""
        cls._registry[name.lower()] = strategy_class
    
    # =========================================================================
    # Factory Methods
    # =========================================================================
    
    @classmethod
    def create(
        cls,
        strategy_type: str,
        problem_handler: ProblemHandler,
        llm: Any,
        coding_agent_config: CodingAgentConfig,
        params: Optional[Dict[str, Any]] = None,
        hosts: Optional[Dict[str, Dict[str, Any]]] = None,
        workspace_dir: Optional[str] = None,
        start_from_checkpoint: bool = False,
        initial_repo: Optional[str] = None,
        eval_dir: Optional[str] = None,
        data_dir: Optional[str] = None,
        evaluation_manifest: Optional[Dict[str, str]] = None,
        feedback_generator: Optional["FeedbackGenerator"] = None,
        goal: str = "",
        status_heartbeat_seconds: Optional[float] = None,
        harness: Optional[Any] = None,
        experience: Optional[List[Dict[str, Any]]] = None,
    ) -> SearchStrategy:
        """
        Create a search strategy instance.
        
        Args:
            strategy_type: Name of registered strategy (e.g., "generic")
            problem_handler: Problem handler instance
            llm: LLM backend
            coding_agent_config: Config for coding agent
            params: Strategy-specific parameters (the config's search_strategy.params)
            hosts: The config's hosts table the strategy's roles resolve over
            workspace_dir: Path to workspace directory (optional)
            start_from_checkpoint: Whether to import from checkpoint
            initial_repo: Path to initial repository to seed workspace
            eval_dir: Path to evaluation files (copied to kapso_evaluation/)
            data_dir: Path to data files (copied to kapso_datasets/)
            evaluation_manifest: Prevalidated provided-suite file hashes
            feedback_generator: FeedbackGenerator for generating feedback after experiments
            goal: Goal string for feedback generation
            status_heartbeat_seconds: The campaign status file's heartbeat cadence
            harness: The loaded harness (kapso.harness.Harness), staged into the sessions
            experience: The loaded sources as recorded (ExperienceRef dicts), named in the status file

        Returns:
            Configured SearchStrategy instance
        """
        cls._ensure_initialized()
        
        strategy_type_lower = strategy_type.lower()
        
        if strategy_type_lower not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Unknown strategy: '{strategy_type}'. "
                f"Available: {available or 'none registered'}"
            )
        
        config = SearchStrategyConfig(
            problem_handler=problem_handler,
            llm=llm,
            coding_agent_config=coding_agent_config,
            params=params or {},
            hosts=dict(hosts or {}),
            initial_repo=initial_repo,
            eval_dir=eval_dir,
            evaluation_manifest=evaluation_manifest,
            data_dir=data_dir,
            feedback_generator=feedback_generator,
            goal=goal,
            status_heartbeat_seconds=status_heartbeat_seconds,
            harness=harness,
            experience=[dict(source) for source in experience or []],
        )

        return cls._registry[strategy_type_lower](
            config,
            workspace_dir=workspace_dir,
            import_from_checkpoint=start_from_checkpoint,
        )
    
    @classmethod
    def get_default_type(cls) -> str:
        """Get the default strategy type."""
        cls._ensure_initialized()
        return cls._default_type
    
    # =========================================================================
    # Registry Access
    # =========================================================================
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all registered strategies."""
        cls._ensure_initialized()
        return sorted(cls._registry.keys())
    
    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if a strategy is registered."""
        cls._ensure_initialized()
        return name.lower() in cls._registry
    
    @classmethod
    def get_strategy_class(cls, name: str) -> Type[SearchStrategy]:
        """Get the strategy class for a given name."""
        cls._ensure_initialized()
        
        name_lower = name.lower()
        if name_lower not in cls._registry:
            raise ValueError(f"Strategy '{name}' not registered")
        return cls._registry[name_lower]


def register_strategy(name: str):
    """
    Decorator to register a search strategy.
    
    Usage:
        @register_strategy("generic")
        class GenericSearch(SearchStrategy):
            ...
    """
    def decorator(cls: Type[SearchStrategy]) -> Type[SearchStrategy]:
        SearchStrategyFactory.register(name, cls)
        return cls
    return decorator
