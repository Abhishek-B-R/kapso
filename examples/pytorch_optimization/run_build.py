"""
PyTorch Operation Optimization Example using Kapso

This example demonstrates using Kapso's build() function to optimize
a simple PyTorch model that performs matrix multiplication, division,
summation, and scaling operations.

The goal is to fuse operations for maximum speedup while maintaining
numerical correctness.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kapso import Kapso


def main():
    # Initialize Kapso
    kapso = Kapso()
    
    # Define the optimization goal
    goal = """
Optimize the PyTorch Model in `module.py` for maximum speedup.

The model performs: matrix multiplication -> division -> summation -> scaling.

## Constraints
- Must maintain the same Model class interface (same __init__ and forward signatures)
- Must produce numerically correct results (max float diff < 1e-5)
- Must work on CUDA devices

## Optimization Hints
- Fuse operations in the forward method
- Consider using torch.compile() for JIT compilation
- Look for opportunities to reduce memory operations
- Consider using in-place operations where safe

## Evaluation
Run: python evaluate.py --path module.py --device cuda

## Success Criteria
- Numerical correctness: max diff < 1e-5
- Performance: speedup > 1.0x (higher score = better)

## Environment
Use the `kapso` conda environment which has PyTorch and CUDA pre-installed:
  conda activate kapso
"""

    # Get the directory containing the starter code
    initial_repo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_repo")
    
    # Run a build to optimize the PyTorch operations
    solution = kapso.build(
        goal,
        # Start from the initial repo
        repo=initial_repo_dir,
        # Output the optimized solution
        output="./examples/pytorch_optimization/pytorch_optimized",
    )
    
    print("\n" + "=" * 60)
    print("PyTorch Optimization Complete!")
    print("=" * 60)
    print(f"\nFinal score (speedup): {solution.score}")
    print(f"Goal achieved: {solution.succeeded}")
    print(f"\nTo evaluate the result:")
    print(f"  cd {solution.trace}")
    print(f"  python evaluate.py --path module.py --device cuda")


if __name__ == "__main__":
    main()
