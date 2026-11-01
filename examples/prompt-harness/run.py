"""Prompt engineering: a better AIME prompt, scored by the repository's evaluate.py."""
from kapso import Kapso, Brief

solution = Kapso().build(Brief.read("kapso-brief.md"), repo="repo", output="campaign")
print(solution.explain())
