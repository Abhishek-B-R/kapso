#!/usr/bin/env bash
# Runs ON the benchmark machine (piped over ssh by benchmark_machine.sh install):
# system tooling, the two coding-agent CLIs, one virtual environment under
# ~/bench/venv holding the Kapso wheel and the benchmark's own stack (the
# candidates' code runs in the handler's interpreter, so both live in one
# environment), and the benchmark tree under ~/bench/benchmarks.
# Arguments: the wheel's file name under /tmp, the benchmark, the machine kind (gpu|cpu).
set -euo pipefail
WHEEL="/tmp/$1"
BENCHMARK="$2"
KIND="$3"

sudo apt-get update -qq
sudo apt-get install -y -qq git curl ca-certificates build-essential python3-venv python3-dev >/dev/null
if [ "$KIND" = cpu ]; then
  # The heuristic-optimisation scorer runs in Docker.
  sudo apt-get install -y -qq docker.io >/dev/null
  sudo usermod -aG docker "$USER"
fi

curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null
sudo apt-get install -y -qq nodejs >/dev/null
sudo npm install -g --silent @anthropic-ai/claude-code @openai/codex

mkdir -p "$HOME/bench"
tar -C "$HOME/bench" -xzf /tmp/benchmark.tgz
python3 -m venv "$HOME/bench/venv"
# shellcheck disable=SC1091
. "$HOME/bench/venv/bin/activate"
pip install -q --upgrade pip
pip install -q "$WHEEL"
pip install -q -r "$HOME/bench/benchmarks/$BENCHMARK/requirements.txt"
case "$BENCHMARK" in
  relbench)
    # The modelling stack the benchmark's requirements name in their notes.
    pip install -q torch
    pip install -q "relbench[full]" sentence-transformers lightgbm xgboost catboost tqdm scikit-learn pooch
    ;;
  mle)
    pip install -q torch
    ;;
  ale|ioai2026)
    ;;
  *)
    echo "unknown benchmark $BENCHMARK" >&2; exit 1 ;;
esac

if [ "$KIND" = gpu ]; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || echo "no GPU visible yet (the driver installs at first boot; reboot if this persists)"
  python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
fi
echo "kapso $(kapso --version 2>/dev/null || echo installed)  python $(python --version)"
echo "claude $(claude --version 2>/dev/null | head -1)"
echo "codex $(codex --version 2>/dev/null | head -1)"
