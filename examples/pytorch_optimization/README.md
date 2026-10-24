# PyTorch optimization: a faster module on CUDA

An hour-long build on a CUDA machine that makes the `Model` in
`repo/module.py` (a matrix multiplication, a division, a summation, a
scaling) faster than the shipped version while keeping its results within
1e-5, with the repository's own `evaluate.py` measuring correctness and
speedup.

Recorded result: not recorded yet.

## What you get

- `repo/module.py`, rewritten on a branch of its own inside `build/`:
  fused operations, `torch.compile`, in-place operations where safe, a
  Triton or CUDA kernel if the campaign goes that far.
- A score from `repo/evaluate.py --path module.py --device cuda`: the
  speedup over the baseline, after a correctness check.
- `build/.kapso/solution.json`, the record, read back by `Solution.open("build")`.

## Run it

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
kapso doctor build
kapso build --brief kapso-brief.md --repo repo --output build --detach
kapso watch build --follow
```

`python run.py` is the same build from Python. A CUDA device is required:
the evaluator runs on it.

## What to look at

- `kapso-brief.md`: the rules keep the class interface, the numerical
  tolerance and the CUDA requirement; the judge rejects a faster module
  that breaks any of them.
- `solution.diff()`: what changed in `module.py`.
- `cd build && python evaluate.py --path module.py --device cuda`: the
  speedup, re-measured by hand.

## Change it

- The target: `Target` in the brief is "above 1.0x"; state a number if you
  know what the hardware allows.
- The budget: the brief's `Budget minutes=60 iterations=8`, or the command's
  `--budget-minutes` and `--iterations`, which win over it.
- Protect the evaluator from the start by moving `evaluate.py` into a
  directory of its own and passing it with `--evaluation`.
