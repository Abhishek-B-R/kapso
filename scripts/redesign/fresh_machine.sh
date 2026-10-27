#!/usr/bin/env bash
# A fresh GCP machine for proof runs and semantic tests: nothing from the
# development checkout is on it, so a flow that works there works for a user.
#
#   scripts/redesign/fresh_machine.sh create  <run-id>
#   scripts/redesign/fresh_machine.sh install <run-id> <wheel-path>
#   scripts/redesign/fresh_machine.sh run     <run-id> "<command>"
#   scripts/redesign/fresh_machine.sh fetch   <run-id> <remote-path>     # into runs/<run-id>/fetched/
#   scripts/redesign/fresh_machine.sh delete  <run-id>
#   scripts/redesign/fresh_machine.sh status
#
# See README.md beside this script for the machine, the secrets it reads and
# the guarantees (auto-delete after MAX_RUN, idempotent delete, verified).
set -euo pipefail

PROJECT="${KAPSO_FRESH_PROJECT:-trans-density-437811-p2}"
ZONE="${KAPSO_FRESH_ZONE:-us-central1-a}"
MACHINE_TYPE="e2-standard-4"
IMAGE_FAMILY="ubuntu-2404-lts-amd64"
IMAGE_PROJECT="ubuntu-os-cloud"
MAX_RUN="${KAPSO_FRESH_MAX_RUN:-4h}"   # a longer round sets it (the plugin round: 5h)
HOURLY_USD="0.134"
LABEL="purpose=kapso-fresh"
CLAUDE_SECRET="${KAPSO_FRESH_CLAUDE_SECRET:-claude-oauth-token-3}"   # the token rule's answer, when another login has the headroom
OPENAI_SECRET="openai-api-key"
HERE="$(cd "$(dirname "$0")" && pwd)"
RUNS="$HERE/runs"

usage() { sed -n 2,12p "$0" | sed 's/^# \{0,1\}//'; exit 2; }

name_of() { echo "kapso-fresh-$1"; }

ssh_run() {   # ssh_run <name> <command>  (stdin passes through)
  gcloud compute ssh "ubuntu@$1" --project "$PROJECT" --zone "$ZONE" --quiet \
    --ssh-flag="-o ConnectTimeout=30" --ssh-flag="-o StrictHostKeyChecking=no" \
    --command "$2"
}

wait_for_ssh() {
  local name="$1" tries=0
  until ssh_run "$name" "true" 2>/dev/null; do
    tries=$((tries + 1))
    if [ "$tries" -ge 30 ]; then echo "ssh never came up on $name" >&2; exit 1; fi
    sleep 10
  done
}

push_secret() {   # push_secret <name> <VAR> <secret-name>: value travels on ssh stdin only
  { printf '%s=' "$2"; gcloud secrets versions access latest --secret="$3" --project "$PROJECT"; printf '\n'; } \
    | ssh_run "$1" "umask 077; mkdir -p ~/.secrets; cat >> ~/.secrets/env"
}

cmd_create() {
  local id="$1" name; name="$(name_of "$id")"
  mkdir -p "$RUNS/$id"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$RUNS/$id/created_at"
  gcloud compute instances create "$name" --project "$PROJECT" --zone "$ZONE" \
    --machine-type "$MACHINE_TYPE" --image-family "$IMAGE_FAMILY" --image-project "$IMAGE_PROJECT" \
    --boot-disk-size 50GB --labels "$LABEL,run=$id" \
    --max-run-duration "$MAX_RUN" --instance-termination-action DELETE \
    --scopes default --quiet | tee "$RUNS/$id/create.log"
  wait_for_ssh "$name"
  echo "created $name in $ZONE (auto-deletes after $MAX_RUN)"
}

cmd_install() {
  local id="$1" wheel="$2" name; name="$(name_of "$id")"
  if [ ! -f "$wheel" ]; then echo "no wheel at $wheel" >&2; exit 1; fi
  sha256sum "$wheel" | tee "$RUNS/$id/wheel.sha256"
  gcloud compute scp "$wheel" "ubuntu@$name:/tmp/$(basename "$wheel")" --project "$PROJECT" --zone "$ZONE" --quiet
  ssh_run "$name" "bash -s -- $(basename "$wheel")" < "$HERE/fresh_machine_install.sh" 2>&1 | tee "$RUNS/$id/install.log"
  push_secret "$name" CLAUDE_CODE_OAUTH_TOKEN "$CLAUDE_SECRET"
  push_secret "$name" OPENAI_API_KEY "$OPENAI_SECRET"
  ssh_run "$name" "set -a; . ~/.secrets/env; set +a; printenv OPENAI_API_KEY | codex login --with-api-key >/dev/null && echo 'codex: logged in with the API key'"
  echo "installed $(basename "$wheel") on $name"
}

cmd_run() {
  local id="$1" command="$2" name; name="$(name_of "$id")"
  local n; n="$(ls "$RUNS/$id" | grep -c '^run-' || true)"; n=$((n + 1))
  local log="$RUNS/$id/run-$n.log"
  echo "# $command" > "$log"
  ssh_run "$name" "set -a; . ~/.secrets/env; set +a; export PATH=\$HOME/.local/bin:\$PATH; $command" 2>&1 | tee -a "$log"
  echo "log: $log"
}

cmd_fetch() {
  local id="$1" remote="$2" name rel; name="$(name_of "$id")"; rel="${remote#\~/}"
  mkdir -p "$RUNS/$id/fetched"
  # One compressed stream, not a recursive scp. scp --recurse dereferences a
  # venv's lib64 -> lib symlink (copying site-packages twice) and pays a round
  # trip per tiny file -- an S1 run's throwaway venv alone is ~1 GB of bytecode.
  # tar keeps symlinks and drops the reproducible bulk (venvs, caches, .pyc)
  # the record never needs; every transcript and build artifact stays.
  gcloud compute ssh "ubuntu@$name" --project "$PROJECT" --zone "$ZONE" --quiet \
    --command "tar -C \"\$HOME\" -czf /tmp/fetch.tgz --exclude='*/venv' --exclude='*/.venv' --exclude='*/__pycache__' --exclude='*.pyc' --exclude='*/.cache' '$rel'"
  gcloud compute scp "ubuntu@$name:/tmp/fetch.tgz" "$RUNS/$id/fetched.tgz" --project "$PROJECT" --zone "$ZONE" --quiet
  tar -C "$RUNS/$id/fetched" -xzf "$RUNS/$id/fetched.tgz"
  rm -f "$RUNS/$id/fetched.tgz"
  echo "fetched $remote into $RUNS/$id/fetched/ (venvs, caches and bytecode excluded)"
}

cmd_delete() {
  local id="$1" name; name="$(name_of "$id")"
  if gcloud compute instances describe "$name" --project "$PROJECT" --zone "$ZONE" >/dev/null 2>&1; then
    gcloud compute instances delete "$name" --project "$PROJECT" --zone "$ZONE" --quiet
  fi
  local left; left="$(gcloud compute instances list --project "$PROJECT" --filter="name=$name" --format='value(name)')"
  if [ -n "$left" ]; then echo "STILL PRESENT: $left" >&2; exit 1; fi
  local disks; disks="$(gcloud compute disks list --project "$PROJECT" --filter="name~^$name\$" --format='value(name)')"
  if [ -n "$disks" ]; then echo "leftover disks: $disks" >&2; exit 1; fi
  if [ -f "$RUNS/$id/created_at" ]; then
    local start now hours cost
    start="$(date -u -d "$(cat "$RUNS/$id/created_at")" +%s)"; now="$(date -u +%s)"
    hours="$(awk -v s="$start" -v n="$now" 'BEGIN{printf "%.2f", (n-s)/3600}')"
    cost="$(awk -v h="$hours" -v r="$HOURLY_USD" 'BEGIN{printf "%.2f", h*r}')"
    echo "deleted $name after ${hours}h, about \$${cost} at \$${HOURLY_USD}/h" | tee "$RUNS/$id/deleted.txt"
  else
    echo "deleted $name"
  fi
}

cmd_status() {
  gcloud compute instances list --project "$PROJECT" --filter="labels.purpose=kapso-fresh" \
    --format='table(name,zone.basename(),status,creationTimestamp)'
}

case "${1:-}" in
  create)  [ $# -eq 2 ] || usage; cmd_create "$2" ;;
  install) [ $# -eq 3 ] || usage; cmd_install "$2" "$3" ;;
  run)     [ $# -eq 3 ] || usage; cmd_run "$2" "$3" ;;
  fetch)   [ $# -eq 3 ] || usage; cmd_fetch "$2" "$3" ;;
  delete)  [ $# -eq 2 ] || usage; cmd_delete "$2" ;;
  status)  cmd_status ;;
  *) usage ;;
esac
