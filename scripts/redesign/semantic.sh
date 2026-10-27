#!/usr/bin/env bash
# The semantic suite's runner (docs/plans/redesign/wp9-semantic-suite.md,
# change 12): one test, one host, from one line. It preflights every
# role's route, provisions a fresh machine with the test's run cap,
# installs the wheel built from this branch and the fixtures' dependency
# venv first on PATH, runs the driver under an immutable run id, archives
# the whole run, verifies the archive is fetched, deletes the machine,
# then judges and renders the report on the development box.
#
#   scripts/redesign/semantic.sh <s1|s2|s4|s5|s6|author> <host> [--machine <id>] [--advisory "<reason>"] [-- <driver flags>]
#
# --advisory runs on the development box under a fresh Linux user that
# holds nothing of the checkout (the flow, not its smoothness) and marks
# the record; a test whose roles need Codex credit the machine lacks runs
# this way until the credit exists. The judge always runs on the
# development box (its Vertex route), never on the machine.
set -o pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SUITE="$ROOT/tests/semantic/suite.json"
FRESH="$HERE/fresh_machine.sh"
RUNS="$HERE/runs/wp9"
REPORTS="$ROOT/tests/semantic/reports"

TEST="${1:-}"; HOST="${2:-}"
case "$TEST" in s1|s2|s4|s5|s6|author) ;; *) echo "usage: semantic.sh <s1|s2|s4|s5|s6|author> <host> [--machine id] [--advisory reason] [-- driver flags]" >&2; exit 2 ;; esac
case "$HOST" in claude_code|codex) ;; *) echo "host is claude_code or codex" >&2; exit 2 ;; esac
shift 2

MACHINE=""; ADVISORY=""; DRIVER_FLAGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --machine) MACHINE="$2"; shift 2 ;;
    --advisory) ADVISORY="$2"; shift 2 ;;
    --) shift; DRIVER_FLAGS=("$@"); break ;;
    *) echo "unknown flag $1" >&2; exit 2 ;;
  esac
done

TEST_UPPER="$(echo "$TEST" | tr 'a-z' 'A-Z')"
suite_get() { python3 -c "import json,sys; print(json.load(open('$SUITE'))$1)"; }
RUN_ID="${MACHINE:-wp9-$TEST-$HOST-$(date -u +%Y%m%dT%H%M%S)}"
RUN_DIR="$RUNS/$RUN_ID"
mkdir -p "$RUN_DIR" "$REPORTS"

# ---- the driver command, per test (cwd ~/kapso-clone, out ~/out) ----
driver_cmd() {
  case "$TEST" in
    s1)     echo "python3 scripts/redesign/s1_cold_engineer.py --clone \$PWD --out ~/out --host $HOST" ;;
    s2)     echo "python3 scripts/redesign/plugin_proof.py --clone \$PWD --out ~/out --host $HOST --user persona:ml-engineer" ;;
    s5)     echo "python3 scripts/redesign/s5_injections.py --clone \$PWD --out ~/out" ;;
    s6)     echo "python3 scripts/redesign/s6_experience.py --clone \$PWD --out ~/out" ;;
    author) echo "python3 scripts/redesign/author_test.py --clone \$PWD --out ~/out --host $HOST" ;;
    s4)     echo "python3 scripts/redesign/s4_reading.py --clone \$PWD --out ~/out --campaign ~/tampering-campaign" ;;
  esac
}
RUBRIC=""   # the tests whose record a judge settles
case "$TEST" in s1) RUBRIC=s1 ;; s2) RUBRIC=s2 ;; s4) RUBRIC=s4 ;; author) RUBRIC=author ;; esac

# ---- the harness the machine needs (not the product: the test scaffold) ----
pack_harness() {   # a partial checkout: the drivers, the suite, the examples, the docs
  tar -C "$ROOT" -czf "$1" scripts/redesign tests/semantic tests/fixtures/semantic_transcripts examples docs
}

preflight() {
  echo "== preflight the routes" | tee "$RUN_DIR/preflight.log"
  python3 "$HERE/judge.py" --preflight 2>&1 | tee -a "$RUN_DIR/preflight.log"   # the judge's Vertex route
  case "$HOST" in
    claude_code) claude --version >/dev/null 2>&1 && echo "claude: on PATH" | tee -a "$RUN_DIR/preflight.log" ;;
    codex)       codex --version  >/dev/null 2>&1 && echo "codex: on PATH"  | tee -a "$RUN_DIR/preflight.log" ;;
  esac
  # The Codex key's credit, one small call, statuses only (never the key):
  if [ -n "${OPENAI_API_KEY:-}" ]; then
    local status
    status="$(curl -s -o /dev/null -w '%{http_code}' https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY")"
    echo "codex key: models endpoint $status (a response call may still 429 on credit)" | tee -a "$RUN_DIR/preflight.log"
  fi
}

build_wheel() {
  echo "== build the wheel from this branch" | tee "$RUN_DIR/wheel.log"
  rm -rf "$RUN_DIR/dist"
  ( cd "$ROOT" && uv build --wheel -o "$RUN_DIR/dist" ) 2>&1 | tee -a "$RUN_DIR/wheel.log"
  ls "$RUN_DIR/dist"/*.whl | head -1
}

venv_command() {   # on the machine: the fixtures' dependency venv first on PATH
  cat <<'VENV'
set -e
python3 -m venv ~/fixtures-venv
~/fixtures-venv/bin/pip install -q --upgrade pip
for req in ~/kapso-clone/examples/*/requirements.txt; do ~/fixtures-venv/bin/pip install -q -r "$req"; done
echo "fixtures venv: $(~/fixtures-venv/bin/python -c 'import numpy,pandas; print("numpy",numpy.__version__,"pandas",pandas.__version__)')"
VENV
}

judge_and_report() {   # on the development box, over the fetched record
  local fetched="$RUN_DIR/fetched/out"
  if [ ! -f "$fetched/record.json" ]; then echo "no record at $fetched/record.json" >&2; exit 1; fi
  echo "== archive verified: $fetched/record.json present" | tee "$RUN_DIR/verify.log"
  if [ -n "$RUBRIC" ]; then
    local inputs=()
    case "$TEST" in
      s4)     inputs=(--inputs judge/reading-claude_code.md judge/reading-codex.md) ;;
      author) inputs=(--inputs artifacts/round-1-harness.md artifacts/round-2-harness.md) ;;
    esac
    python3 "$HERE/judge.py" "$fetched" --rubric "$RUBRIC" "${inputs[@]}" 2>&1 | tee "$RUN_DIR/judge.log"
    case "$TEST" in
      s4)     python3 "$HERE/s4_reading.py" --out "$fetched" --grade ;;
      author) python3 "$HERE/author_test.py" --out "$fetched" --clone "$ROOT" --grade ;;
    esac
  fi
  local report="$REPORTS/$RUN_ID.md"
  python3 "$ROOT/tests/semantic/report.py" "$fetched/record.json" "$report"
  echo "report: $report (exit $?)"
}

preflight

if [ -n "$ADVISORY" ]; then
  # The development box, a fresh user with nothing of the checkout: the
  # harness scaffold unpacked into its home, the driver run there, the
  # out directory copied back, the user removed.
  USER_NAME="sem$TEST$$"
  HOME_DIR="/home/$USER_NAME"
  echo "== advisory on the development box as $USER_NAME: $ADVISORY" | tee "$RUN_DIR/advisory.log"
  pack_harness "$RUN_DIR/harness.tgz"
  sudo useradd -m "$USER_NAME"
  sudo cp "$RUN_DIR/harness.tgz" "$HOME_DIR/harness.tgz"
  sudo chown "$USER_NAME:$USER_NAME" "$HOME_DIR/harness.tgz"
  sudo -u "$USER_NAME" -H bash -lc "mkdir -p ~/kapso-clone ~/out && tar -C ~/kapso-clone -xzf ~/harness.tgz && cd ~/kapso-clone && $(driver_cmd) --advisory '$ADVISORY' ${DRIVER_FLAGS[*]}" 2>&1 | tee "$RUN_DIR/driver.log"
  mkdir -p "$RUN_DIR/fetched"
  sudo cp -r "$HOME_DIR/out" "$RUN_DIR/fetched/out"
  sudo chown -R "$(id -un):$(id -gn)" "$RUN_DIR/fetched"
  sudo userdel -r "$USER_NAME" 2>/dev/null || true
  judge_and_report
  exit 0
fi

# ---- a fresh machine ----
export KAPSO_FRESH_MAX_RUN="$(suite_get "['machine']['max_run']['$TEST_UPPER']")"
WHEEL="$(build_wheel)"
HARNESS="$RUN_DIR/harness.tgz"; pack_harness "$HARNESS"
"$FRESH" create "$RUN_ID"
"$FRESH" install "$RUN_ID" "$WHEEL"
gcloud compute scp "$HARNESS" "ubuntu@kapso-fresh-$RUN_ID:/tmp/harness.tgz" --project "${KAPSO_FRESH_PROJECT:-trans-density-437811-p2}" --zone "${KAPSO_FRESH_ZONE:-us-central1-a}" --quiet
"$FRESH" run "$RUN_ID" "mkdir -p ~/kapso-clone ~/out && tar -C ~/kapso-clone -xzf /tmp/harness.tgz"
"$FRESH" run "$RUN_ID" "$(venv_command)"
"$FRESH" run "$RUN_ID" "cd ~/kapso-clone && export PATH=~/fixtures-venv/bin:\$PATH && $(driver_cmd) ${DRIVER_FLAGS[*]}"
"$FRESH" fetch "$RUN_ID" '~/out'
"$FRESH" delete "$RUN_ID"
judge_and_report
