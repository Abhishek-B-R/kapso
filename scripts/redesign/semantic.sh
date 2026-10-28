#!/usr/bin/env bash
# The semantic suite's runner (docs/plans/redesign/wp9-semantic-suite.md,
# change 12): one test, one host, from one line. It preflights every
# role's route with a real call, provisions a fresh machine with the
# test's run cap, installs one environment that holds the wheel built from
# this branch and the fixtures' dependencies, runs the driver under an
# immutable run id, fetches the whole run, verifies the record is present,
# only then deletes the machine, and finally judges and renders the report
# on the development box — the report's exit status is the runner's.
#
#   scripts/redesign/semantic.sh <s1|s2|s4|s5|s6|author> <host> [--machine <id>] [--advisory "<reason>"] [-- <driver flags>]
#
# --advisory runs on the development box under a fresh Linux user that
# holds nothing of the checkout (the flow, not its smoothness) and marks
# the record; a test whose roles need Codex credit the machine lacks runs
# this way until the credit exists. The judge always runs on the
# development box (its Vertex route), never on the machine.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SUITE="$ROOT/tests/semantic/suite.json"
FRESH="$HERE/fresh_machine.sh"
RUNS="$HERE/runs/wp9"
REPORTS="$ROOT/tests/semantic/reports"
PROJECT="${KAPSO_FRESH_PROJECT:-trans-density-437811-p2}"
ZONE="${KAPSO_FRESH_ZONE:-us-central1-a}"
CODEX_SESSION_HOME="${KAPSO_CODEX_SESSION_HOME:-/home/ubuntu/.codex-semantic}"   # the device-auth ChatGPT session that holds the Codex credit

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

# The suite's machine.max_run key is lowercase for the author, uppercase
# for the numbered tests.
[ "$TEST" = author ] && SUITE_KEY=author || SUITE_KEY="$(echo "$TEST" | tr 'a-z' 'A-Z')"
suite_get() { python3 -c "import json,sys; print(json.load(open('$SUITE'))$1)"; }
RELEASED="$(suite_get "['released']['version']")"   # the tag whose docs ride in the pack (S1's retrospective baseline)
RUN_ID="${MACHINE:-wp9-$TEST-$HOST-$(date -u +%Y%m%dT%H%M%S)}"
RUN_DIR="$RUNS/$RUN_ID"
mkdir -p "$RUN_DIR" "$REPORTS"

# Which host roles a test exercises, so the preflight gates only the
# routes the run needs (the persona is the OTHER vendor; S2 is the only
# persona test; a run needs Codex credit when any of its roles is Codex).
PERSONA_VENDOR=""; NEEDS_CODEX_CREDIT=""; NEEDS_PLUGIN=""
[ "$HOST" = codex ] && NEEDS_CODEX_CREDIT=1
# S6's learning crews grade on Codex (gpt-5.6-sol), so it needs Codex credit
# even on the Claude host.
[ "$TEST" = s6 ] && NEEDS_CODEX_CREDIT=1
if [ "$TEST" = s2 ]; then
  [ "$HOST" = claude_code ] && PERSONA_VENDOR=codex || PERSONA_VENDOR=claude_code
  [ "$PERSONA_VENDOR" = codex ] && NEEDS_CODEX_CREDIT=1
fi
# S5 drives the operating skill, so the plugin must be installed; S2
# installs it itself as a step, and S1/S4/S6/author use cold sessions.
[ "$TEST" = s5 ] && NEEDS_PLUGIN=1

WHEEL_NAME=""   # the wheel's basename, set by build_wheel; on the machine it is /tmp/$WHEEL_NAME

# ---- the driver command, per test (cwd ~/kapso-clone, out ~/out) ----
driver_cmd() {
  local wheel_flag=""
  [ -n "$WHEEL_NAME" ] && wheel_flag="--wheel /tmp/$WHEEL_NAME"
  case "$TEST" in
    s1)     echo "python3 scripts/redesign/s1_cold_engineer.py --clone \$PWD --out ~/out --host $HOST $wheel_flag" ;;
    s2)     echo "python3 scripts/redesign/plugin_proof.py --clone \$PWD --out ~/out --host $HOST --user persona:ml-engineer $wheel_flag" ;;
    s5)     echo "python3 scripts/redesign/s5_injections.py --clone \$PWD --out ~/out" ;;
    s6)     echo "python3 scripts/redesign/s6_experience.py --clone \$PWD --out ~/out" ;;
    author) echo "python3 scripts/redesign/author_test.py --clone \$PWD --out ~/out --host $HOST" ;;
    s4)     echo "python3 scripts/redesign/s4_reading.py --clone \$PWD --out ~/out --campaign ~/tampering-campaign" ;;
  esac
}
RUBRIC=""   # the tests whose record a judge settles
case "$TEST" in s1) RUBRIC=s1 ;; s2) RUBRIC=s2 ;; s4) RUBRIC=s4 ;; author) RUBRIC=author ;; esac

# ---- the harness the machine needs (not the product: the test scaffold) ----
pack_harness() {   # a partial checkout: the drivers, the suite, the fixtures, the plugin, the docs navigation
  # Exclude runs/ (the local run archives, where this very tar is written —
  # self-inclusion makes tar exit 1 on "file changed as we read it") and caches.
  # The released tag's docs ride along as released-docs/ (S1's retrospective
  # baseline reads them): the pack carries no .git, so they are staged here.
  rm -rf "$RUN_DIR/released-docs"; mkdir -p "$RUN_DIR/released-docs"
  git -C "$ROOT" archive "v$RELEASED" docs docs.json | tar -x -C "$RUN_DIR/released-docs"
  tar --exclude='scripts/redesign/runs' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' -czf "$1" \
    -C "$ROOT" scripts/redesign tests/semantic tests/fixtures/semantic_transcripts \
    examples docs docs.json .claude-plugin plugin \
    -C "$RUN_DIR" released-docs
}

route_ok() {   # a real one-token generation on the host CLI, so a dead login stops us before provisioning
  local cli="$1"
  if [ "$cli" = claude_code ]; then
    claude -p "reply with the word ok" --model claude-fable-5 --output-format text >/dev/null 2>&1
  else
    codex exec -m gpt-6-astra --sandbox read-only --skip-git-repo-check "reply with the word ok" >/dev/null 2>&1
  fi
}

preflight() {
  echo "== preflight the routes" | tee "$RUN_DIR/preflight.log"
  python3 "$HERE/judge.py" --preflight 2>&1 | tee -a "$RUN_DIR/preflight.log"   # the judge's Vertex route, a real call
  route_ok "$HOST" || { echo "host $HOST: a one-token call did not answer; fix the login before provisioning" >&2; exit 3; }
  echo "host $HOST: a one-token call answered" | tee -a "$RUN_DIR/preflight.log"
  if [ -n "$PERSONA_VENDOR" ]; then
    route_ok "$PERSONA_VENDOR" || { echo "persona $PERSONA_VENDOR: a one-token call did not answer" >&2; exit 3; }
    echo "persona $PERSONA_VENDOR: a one-token call answered" | tee -a "$RUN_DIR/preflight.log"
  fi
  if [ -n "$NEEDS_CODEX_CREDIT" ]; then
    # The credit is the device-auth ChatGPT session (the api key is credit
    # exhausted); verify it answers here before provisioning -- it is exactly
    # what fresh_machine.sh installs on the machine. A real one-token call.
    CODEX_HOME="$CODEX_SESSION_HOME" codex exec -m gpt-5.6-sol --sandbox read-only --skip-git-repo-check "reply with the word ok" >/dev/null 2>&1 \
      || { echo "the device-auth Codex session is not answering; re-login (codex login --device-auth) before provisioning" >&2; exit 3; }
    echo "codex: the device-auth session answered" | tee -a "$RUN_DIR/preflight.log"
  fi
}

build_wheel() {   # diagnostics to stderr, only the path on stdout
  echo "== build the wheel from this branch" >&2
  rm -rf "$RUN_DIR/dist"
  ( cd "$ROOT" && uv build --wheel -o "$RUN_DIR/dist" ) >&2
  ls "$RUN_DIR/dist"/*.whl | head -1
}

venv_command() {   # on the machine: one environment with the wheel (kapso + litellm + pyyaml) and the fixtures' deps
  cat <<VENV
set -e
python3 -m venv ~/env
~/env/bin/pip install -q --upgrade pip
~/env/bin/pip install -q "/tmp/$WHEEL_NAME"
for req in ~/kapso-clone/examples/*/requirements.txt; do ~/env/bin/pip install -q -r "\$req"; done
~/env/bin/python -c 'import numpy,pandas,litellm,yaml,kapso; print("env ok: kapso + litellm + yaml + numpy + pandas")'
VENV
}

provision_plugin() {   # install the operating plugin the way a user does (S5 uses the skill, does not test installing it)
  [ -n "$NEEDS_PLUGIN" ] || return 0
  if [ "$HOST" = claude_code ]; then
    "$FRESH" run "$RUN_ID" "claude plugin marketplace add ~/kapso-clone && claude plugin install kapso@kapso"
  fi
}

judge_and_report() {   # on the development box, over the fetched record; the report's exit status is the runner's
  local fetched="$RUN_DIR/fetched/out"
  [ -f "$fetched/record.json" ] || { echo "no record at $fetched/record.json: the run produced none" >&2; exit 1; }
  echo "== archive verified: $fetched/record.json present" | tee "$RUN_DIR/verify.log"
  if [ -n "$RUBRIC" ]; then
    local inputs=()
    case "$TEST" in
      s1)     inputs=(--inputs artifacts/comprehension-answers.txt) ;;
      s4)     inputs=(--inputs judge/reading-claude_code.md judge/reading-codex.md) ;;
      author) inputs=(--inputs artifacts/round-1-harness.md artifacts/round-2-harness.md) ;;
    esac
    python3 "$HERE/judge.py" "$fetched" --rubric "$RUBRIC" "${inputs[@]}" 2>&1 | tee "$RUN_DIR/judge.log"
    case "$TEST" in
      s1)     python3 "$HERE/s1_cold_engineer.py" --out "$fetched" --grade ;;
      s4)     python3 "$HERE/s4_reading.py" --out "$fetched" --grade ;;
      author) python3 "$HERE/author_test.py" --out "$fetched" --clone "$ROOT" --grade ;;
    esac
  fi
  local report="$REPORTS/$RUN_ID.md" status
  python3 "$ROOT/tests/semantic/report.py" "$fetched/record.json" "$report" && status=0 || status=$?
  echo "report: $report (verdict exit $status)"
  exit "$status"
}

preflight

if [ -n "$ADVISORY" ]; then
  # The development box, a fresh user with nothing of the checkout: the
  # scaffold and one environment in its home, the host login written for
  # it, the driver run there, the out directory copied back, the user
  # removed. It proves the flow, not the smoothness.
  USER_NAME="sem${TEST}$$"; HOME_DIR="/home/$USER_NAME"
  echo "== advisory on the development box as $USER_NAME: $ADVISORY" | tee "$RUN_DIR/advisory.log"
  WHEEL="$(build_wheel)"; WHEEL_NAME="$(basename "$WHEEL")"
  pack_harness "$RUN_DIR/harness.tgz"
  sudo useradd -m "$USER_NAME"
  sudo cp "$RUN_DIR/harness.tgz" "$WHEEL" "$HOME_DIR/"
  [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$CLAUDE_CODE_OAUTH_TOKEN" | sudo tee "$HOME_DIR/.token" >/dev/null && sudo chmod 600 "$HOME_DIR/.token"
  sudo chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR"
  STAGE="mkdir -p ~/kapso-clone ~/out && tar -C ~/kapso-clone -xzf ~/harness.tgz && python3 -m venv ~/env && ~/env/bin/pip install -q '$HOME_DIR/$WHEEL_NAME' && for r in ~/kapso-clone/examples/*/requirements.txt; do ~/env/bin/pip install -q -r \$r; done"
  RUNCMD="[ -f ~/.token ] && set -a && . ~/.token && set +a; cd ~/kapso-clone && export PATH=~/env/bin:\$PATH && $(driver_cmd) --advisory '$ADVISORY' ${DRIVER_FLAGS[*]:-}"
  sudo -u "$USER_NAME" -H bash -lc "$STAGE && $RUNCMD" 2>&1 | tee "$RUN_DIR/driver.log"
  mkdir -p "$RUN_DIR/fetched"
  sudo cp -r "$HOME_DIR/out" "$RUN_DIR/fetched/out"
  sudo chown -R "$(id -un):$(id -gn)" "$RUN_DIR/fetched"
  sudo userdel -r "$USER_NAME" 2>/dev/null || true
  judge_and_report
fi

# ---- a fresh machine ----
export KAPSO_FRESH_MAX_RUN="$(suite_get "['machine']['max_run']['$SUITE_KEY']")"
WHEEL="$(build_wheel)"; WHEEL_NAME="$(basename "$WHEEL")"
HARNESS="$RUN_DIR/harness.tgz"; pack_harness "$HARNESS"
"$FRESH" create "$RUN_ID"
"$FRESH" install "$RUN_ID" "$WHEEL"
gcloud compute scp "$HARNESS" "ubuntu@kapso-fresh-$RUN_ID:/tmp/harness.tgz" --project "$PROJECT" --zone "$ZONE" --quiet
"$FRESH" run "$RUN_ID" "mkdir -p ~/kapso-clone ~/out && tar -C ~/kapso-clone -xzf /tmp/harness.tgz"
"$FRESH" run "$RUN_ID" "$(venv_command)"
provision_plugin
if [ "$TEST" = s4 ]; then
  # S4 reads S5's tampering campaign: an archived campaign directory passed
  # as the first driver flag, staged onto the machine before the run.
  CAMPAIGN="${DRIVER_FLAGS[0]:-}"
  [ -d "$CAMPAIGN" ] || { echo "s4 needs an S5 tampering campaign directory: semantic.sh s4 <host> -- <campaign-dir>" >&2; exit 2; }
  tar -C "$(dirname "$CAMPAIGN")" -czf "$RUN_DIR/campaign.tgz" "$(basename "$CAMPAIGN")"
  gcloud compute scp "$RUN_DIR/campaign.tgz" "ubuntu@kapso-fresh-$RUN_ID:/tmp/campaign.tgz" --project "$PROJECT" --zone "$ZONE" --quiet
  "$FRESH" run "$RUN_ID" "mkdir -p ~/tampering-campaign && tar -C ~/tampering-campaign --strip-components=1 -xzf /tmp/campaign.tgz"
  DRIVER_FLAGS=()
fi
"$FRESH" run "$RUN_ID" "cd ~/kapso-clone && export PATH=~/env/bin:\$PATH && $(driver_cmd) ${DRIVER_FLAGS[*]:-}"
"$FRESH" fetch "$RUN_ID" '~/out'
# fresh_machine.sh fetches into runs/<id>/fetched; the verified archive
# lives under this run's directory. Move it, verify, and only then delete.
[ -d "$HERE/runs/$RUN_ID/fetched" ] && rm -rf "$RUN_DIR/fetched" && mv "$HERE/runs/$RUN_ID/fetched" "$RUN_DIR/fetched"
[ -f "$RUN_DIR/fetched/out/record.json" ] || { echo "the archive has no record.json; keeping the machine $RUN_ID for inspection" >&2; exit 1; }
"$FRESH" delete "$RUN_ID"
judge_and_report
