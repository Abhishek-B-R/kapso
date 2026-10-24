Objective    Optimize the PyTorch Model in module.py for maximum speedup on
             CUDA. The model performs a matrix multiplication, a division,
             a summation and a scaling. Fuse operations, consider
             torch.compile, cut memory traffic, use in-place operations
             where they are safe.
Measured by  python evaluate.py --path module.py --device cuda, in the
             repository: numerical correctness (max float difference below
             1e-5) and the speedup over the baseline, which is the score
Baseline     1.0x, the shipped module
Target       a speedup above 1.0x, the higher the better
Rules
  - the Model class keeps its interface: the same __init__ and forward signatures
  - results stay numerically correct: max float difference below 1e-5
  - the module runs on CUDA devices
  - evaluate.py is never modified
Budget       minutes=60 experiments=8
