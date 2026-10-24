"""PyTorch optimization: a faster module.py on CUDA, scored by the repository's evaluate.py."""
from kapso import Kapso, Brief

solution = Kapso().build(Brief.read("kapso-brief.md"), repo="repo", output="build")
print(solution.explain())
