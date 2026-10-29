#!/usr/bin/env bash
# Runs ON the benchmark machine (piped over ssh by benchmark_machine.sh install):
# system tooling, the two coding-agent CLIs, one virtual environment under
# ~/bench/venv holding the Kapso wheel and the benchmark's own stack (the
# candidates' code runs in the handler's interpreter, so both live in one
# environment), and the benchmark tree under ~/bench/benchmarks.
# Arguments: the wheel's file name under /tmp, the benchmark, the machine kind (gpu|gpu4|cpu).
# The benchmark libraries are pinned at the revisions the development
# environment runs; the ALE judge image is the one its problems name.
set -euo pipefail
WHEEL="/tmp/$1"
BENCHMARK="$2"
KIND="$3"

sudo apt-get update -qq
sudo apt-get install -y -qq git git-lfs curl ca-certificates build-essential python3-venv python3-dev >/dev/null
if [ "$BENCHMARK" = ale ]; then
  # The heuristic-optimisation judge runs in Docker; the library renders with cairo.
  sudo apt-get install -y -qq docker.io libcairo2-dev >/dev/null
  sudo usermod -aG docker "$USER"
fi

curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null
sudo apt-get install -y -qq nodejs >/dev/null
sudo npm install -g --silent @anthropic-ai/claude-code @openai/codex

mkdir -p "$HOME/bench"
tar -C "$HOME/bench" -xzf /tmp/benchmark.tgz
# One interpreter on every machine kind — the development environment's
# Python 3.12, managed by uv (the images ship 3.10 or 3.12; the MLE library
# needs 3.11 or later) — seeded with pip for the installs below.
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
export PATH="$HOME/.local/bin:$PATH"
rm -rf "$HOME/bench/venv"
uv venv --python 3.12 --seed "$HOME/bench/venv" >/dev/null 2>&1
# shellcheck disable=SC1091
. "$HOME/bench/venv/bin/activate"
pip install -q --upgrade pip
pip install -q "$WHEEL"
# The bundled harnesses' own requirements (the engine refuses a build whose
# harness needs are unmet, with this very line as the fix).
for harness_requirements in "$HOME"/bench/venv/lib/python*/site-packages/kapso/harness/bundled/*/requirements.txt; do
  [ -f "$harness_requirements" ] && pip install -q -r "$harness_requirements"
done
if [ -f "$HOME/bench/benchmarks/$BENCHMARK/requirements.txt" ]; then
  pip install -q -r "$HOME/bench/benchmarks/$BENCHMARK/requirements.txt"
fi
case "$BENCHMARK" in
  relbench)
    # The modelling stack the benchmark's requirements name in their notes.
    pip install -q torch
    pip install -q "relbench[full]==2.1.2" sentence-transformers lightgbm xgboost catboost tqdm scikit-learn pooch
    ;;
  mle)
    # The MLE-bench library at the development environment's revision (507f92e1138b); its
    # leaderboards (the medal thresholds) are LFS files, pulled for every competition.
    git lfs install --skip-repo >/dev/null
    [ -d "$HOME/bench/mle-bench" ] || git clone -q https://github.com/openai/mle-bench.git "$HOME/bench/mle-bench"
    git -C "$HOME/bench/mle-bench" checkout -q 507f92e1138b
    git -C "$HOME/bench/mle-bench" lfs pull --include='mlebench/competitions/*/*.csv'
    pip install -q -e "$HOME/bench/mle-bench" kaggle torch
    ;;
  ale)
    # The ALE-Bench library at v1.6.1 with its evaluation extras and the judge image.
    [ -d "$HOME/bench/ALE-Bench" ] || git clone -q https://github.com/SakanaAI/ALE-Bench.git "$HOME/bench/ALE-Bench"
    git -C "$HOME/bench/ALE-Bench" checkout -q v1.6.1
    pip install -q "$HOME/bench/ALE-Bench" "$HOME/bench/ALE-Bench[eval]"
    # The library's MCP tool wrappers pull mcp 2; the engine's gates need mcp 1
    # and the runner uses the library's session, not its wrappers.
    pip install -q "mcp<2,>=1.9"
    (cd "$HOME/bench/ALE-Bench" && sg docker -c "bash ./scripts/docker_build_202301.sh $(id -u) $(id -g)" >/dev/null)
    sg docker -c "docker images" | grep -- 'ale-bench'
    ;;
  ioai2026)
    # The sessions train on this machine before a kernel is pushed.
    pip install -q kaggle torch
    ;;
  *)
    echo "unknown benchmark $BENCHMARK" >&2; exit 1 ;;
esac

if [ "$KIND" != cpu ]; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || echo "no GPU visible yet (the driver installs at first boot; reboot if this persists)"
  python -c "import importlib.util as u; import sys; sys.exit(0 if u.find_spec('torch') else 1)" \
    && python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" \
    || echo "torch is not part of this benchmark's stack"
fi
echo "kapso $(kapso --version 2>/dev/null || echo installed)  python $(python --version)"
echo "claude $(claude --version 2>/dev/null | head -1)"
echo "codex $(codex --version 2>/dev/null | head -1)"
