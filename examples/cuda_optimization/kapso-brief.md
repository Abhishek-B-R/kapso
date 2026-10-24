Objective    Optimize the multi-head self-attention implementation in
             module.py for maximum speedup on CUDA.
Measured by  python evaluate.py --path module.py, in the repository:
             numerical correctness (max float difference below 1e-5) and
             the speedup over the baseline, which is the score
Baseline     1.0x, the shipped module
Target       a speedup above 1.0x; 2x to 4x is reachable with flash
             attention or a Triton kernel
Rules
  - the Model class keeps its interface: the same __init__ and forward signatures
  - results stay numerically correct: max float difference below 1e-5
  - the module runs on CUDA devices
  - evaluate.py is never modified
Budget       minutes=90 experiments=8
