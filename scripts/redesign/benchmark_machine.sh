#!/usr/bin/env bash
# A GCP machine for a benchmark reproduction (docs/plans/redesign/wp8-harness-ports.md):
# the fresh-machine script's shape with a GPU, the wheel and the benchmark
# tree at this commit, the benchmark's own stack, and the run archived.
#
#   scripts/redesign/benchmark_machine.sh create  <run-id> gpu|gpu4|cpu
#   scripts/redesign/benchmark_machine.sh install <run-id> <wheel-path> <benchmark>   # relbench | mle | ale | ioai2026
#   scripts/redesign/benchmark_machine.sh run     <run-id> "<command>"               # from ~/bench, the venv on PATH, the secrets in the environment
#   scripts/redesign/benchmark_machine.sh fetch   <run-id> <remote-path>              # into runs/<run-id>/fetched/
#   scripts/redesign/benchmark_machine.sh delete  <run-id>
#   scripts/redesign/benchmark_machine.sh status
#
# gpu: a spot a2-highgpu-1g (one A100 40 GB); gpu4: a spot a2-highgpu-4g
# (four A100 40 GB, the shape the RelBench lanes recorded; inside the
# project's preemptible A100 quota); both on a driver-bearing image, tried
# zone by zone; cpu: an e2-standard-8 for the Docker scorer. All auto-delete
# after MAX_RUN. The secrets travel on ssh stdin only, as in fresh_machine.sh;
# the Kaggle credential too, for the benchmarks that download or submit
# through it.
set -euo pipefail

PROJECT="${KAPSO_FRESH_PROJECT:-trans-density-437811-p2}"
GPU_ZONES="${KAPSO_BENCH_GPU_ZONES:-us-central1-a us-central1-b us-central1-f}"
CPU_ZONE="${KAPSO_FRESH_ZONE:-us-central1-a}"
GPU_MACHINE_TYPE="a2-highgpu-1g"
GPU4_MACHINE_TYPE="a2-highgpu-4g"
GPU_IMAGE_FAMILY="common-cu129-ubuntu-2204-nvidia-580"
GPU_IMAGE_PROJECT="deeplearning-platform-release"
CPU_MACHINE_TYPE="e2-standard-8"
CPU_IMAGE_FAMILY="ubuntu-2404-lts-amd64"
CPU_IMAGE_PROJECT="ubuntu-os-cloud"
MAX_RUN="${KAPSO_BENCH_MAX_RUN:-14h}"
GPU_HOURLY_USD="1.30"    # the spot a2-highgpu-1g price in us-central1 when this was written; the record carries the bill
GPU4_HOURLY_USD="5.20"   # four times that, the spot a2-highgpu-4g
CPU_HOURLY_USD="0.27"
LABEL="purpose=kapso-bench"
CLAUDE_SECRET="${KAPSO_FRESH_CLAUDE_SECRET:-claude-oauth-token-3}"
OPENAI_SECRET="openai-api-key"
CODEX_SESSION="${KAPSO_CODEX_SESSION:-/home/ubuntu/.codex-semantic/auth.json}"
KAGGLE_CREDENTIAL="${KAPSO_KAGGLE_CREDENTIAL:-$HOME/.kaggle/kaggle.json}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNS="$HERE/runs"

usage() { sed -n 2,15p "$0" | sed 's/^# \{0,1\}//'; exit 2; }

name_of() { echo "kapso-bench-$1"; }

zone_of() { cat "$RUNS/$1/zone"; }

ssh_run() {   # ssh_run <run-id> <command>  (stdin passes through)
  gcloud compute ssh "ubuntu@$(name_of "$1")" --project "$PROJECT" --zone "$(zone_of "$1")" --quiet \
    --ssh-flag="-o ConnectTimeout=30" --ssh-flag="-o StrictHostKeyChecking=no" \
    --command "$2"
}

wait_for_ssh() {
  local id="$1" tries=0
  until ssh_run "$id" "true" 2>/dev/null; do
    tries=$((tries + 1))
    if [ "$tries" -ge 40 ]; then echo "ssh never came up on $(name_of "$id")" >&2; exit 1; fi
    sleep 15
  done
}

push_secret() {   # push_secret <run-id> <VAR> <secret-name>
  { printf '%s=' "$2"; gcloud secrets versions access latest --secret="$3" --project "$PROJECT"; printf '\n'; } \
    | ssh_run "$1" "umask 077; mkdir -p ~/.secrets; cat >> ~/.secrets/env"
}

create_in_zone() {   # create_in_zone <run-id> <kind> <zone>
  local id="$1" kind="$2" zone="$3" name; name="$(name_of "$id")"
  if [ "$kind" = gpu ] || [ "$kind" = gpu4 ]; then
    local machine_type="$GPU_MACHINE_TYPE" gpus=1
    if [ "$kind" = gpu4 ]; then machine_type="$GPU4_MACHINE_TYPE"; gpus=4; fi
    gcloud compute instances create "$name" --project "$PROJECT" --zone "$zone" \
      --machine-type "$machine_type" --accelerator "type=nvidia-tesla-a100,count=$gpus" --maintenance-policy TERMINATE \
      --provisioning-model SPOT --instance-termination-action DELETE --max-run-duration "$MAX_RUN" \
      --image-family "$GPU_IMAGE_FAMILY" --image-project "$GPU_IMAGE_PROJECT" \
      --boot-disk-size 300GB --boot-disk-type pd-balanced --metadata install-nvidia-driver=True \
      --labels "$LABEL,run=$id,kind=$kind" --scopes default --quiet
  else
    gcloud compute instances create "$name" --project "$PROJECT" --zone "$zone" \
      --machine-type "$CPU_MACHINE_TYPE" --image-family "$CPU_IMAGE_FAMILY" --image-project "$CPU_IMAGE_PROJECT" \
      --boot-disk-size 100GB --max-run-duration "$MAX_RUN" --instance-termination-action DELETE \
      --labels "$LABEL,run=$id,kind=cpu" --scopes default --quiet
  fi
}

cmd_create() {
  local id="$1" kind="$2"
  case "$kind" in gpu|gpu4|cpu) ;; *) usage ;; esac
  mkdir -p "$RUNS/$id"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$RUNS/$id/created_at"
  echo "$kind" > "$RUNS/$id/kind"
  local zones="$CPU_ZONE"; [ "$kind" != cpu ] && zones="$GPU_ZONES"
  local zone created=""
  for zone in $zones; do
    if create_in_zone "$id" "$kind" "$zone" 2>&1 | tee -a "$RUNS/$id/create.log"; then
      if gcloud compute instances describe "$(name_of "$id")" --project "$PROJECT" --zone "$zone" >/dev/null 2>&1; then
        created="$zone"; break
      fi
    fi
    echo "zone $zone did not give a machine; trying the next" | tee -a "$RUNS/$id/create.log"
  done
  if [ -z "$created" ]; then echo "no zone could create $(name_of "$id")" >&2; exit 1; fi
  echo "$created" > "$RUNS/$id/zone"
  wait_for_ssh "$id"
  echo "created $(name_of "$id") in $created ($kind; auto-deletes after $MAX_RUN)"
}

cmd_install() {
  local id="$1" wheel="$2" benchmark="$3"
  if [ ! -f "$wheel" ]; then echo "no wheel at $wheel" >&2; exit 1; fi
  if [ ! -d "$ROOT/benchmarks/$benchmark" ]; then echo "no benchmark at benchmarks/$benchmark" >&2; exit 1; fi
  sha256sum "$wheel" | tee "$RUNS/$id/wheel.sha256"
  # The benchmark tree as it is in the working copy at this commit: the
  # runner is repository code, not part of the wheel.
  tar -C "$ROOT" -czf "$RUNS/$id/benchmark.tgz" --exclude='__pycache__' --exclude='*.pyc' "benchmarks/__init__.py" "benchmarks/$benchmark"
  gcloud compute scp "$wheel" "$RUNS/$id/benchmark.tgz" "ubuntu@$(name_of "$id"):/tmp/" --project "$PROJECT" --zone "$(zone_of "$id")" --quiet
  ssh_run "$id" "bash -s -- $(basename "$wheel") $benchmark $(cat "$RUNS/$id/kind")" < "$HERE/benchmark_machine_install.sh" 2>&1 | tee "$RUNS/$id/install.log"
  push_secret "$id" CLAUDE_CODE_OAUTH_TOKEN "$CLAUDE_SECRET"
  push_secret "$id" OPENAI_API_KEY "$OPENAI_SECRET"
  [ -f "$CODEX_SESSION" ] || { echo "no Codex session at $CODEX_SESSION" >&2; exit 1; }
  cat "$CODEX_SESSION" | ssh_run "$id" "umask 077; mkdir -p ~/.codex && cat > ~/.codex/auth.json && echo 'the device-auth ChatGPT session of the owner, pushed by benchmark_machine.sh at $(date -u +%FT%TZ); no Codex credit of the run itself' > ~/.codex/SOURCE"
  case "$benchmark" in
    mle|ioai2026)
      [ -f "$KAGGLE_CREDENTIAL" ] || { echo "no Kaggle credential at $KAGGLE_CREDENTIAL" >&2; exit 1; }
      cat "$KAGGLE_CREDENTIAL" | ssh_run "$id" "umask 077; mkdir -p ~/.kaggle && cat > ~/.kaggle/kaggle.json"
      ;;
  esac
  echo "installed $(basename "$wheel") and benchmarks/$benchmark on $(name_of "$id")"
}

cmd_run() {
  local id="$1" command="$2"
  local n; n="$(ls "$RUNS/$id" | grep -c '^run-' || true)"; n=$((n + 1))
  local log="$RUNS/$id/run-$n.log"
  echo "# $command" > "$log"
  ssh_run "$id" "set -a; . ~/.secrets/env; set +a; export PATH=\$HOME/bench/venv/bin:\$HOME/.local/bin:\$PATH; cd ~/bench; $command" 2>&1 | tee -a "$log"
  echo "log: $log"
}

cmd_fetch() {
  local id="$1" remote="$2" rel; rel="${remote#\~/}"
  mkdir -p "$RUNS/$id/fetched"
  gcloud compute ssh "ubuntu@$(name_of "$id")" --project "$PROJECT" --zone "$(zone_of "$id")" --quiet \
    --command "tar -C \"\$HOME\" -czf /tmp/fetch.tgz --exclude='*/venv' --exclude='*/.venv' --exclude='*/__pycache__' --exclude='*.pyc' --exclude='*/.cache' '$rel'"
  gcloud compute scp "ubuntu@$(name_of "$id"):/tmp/fetch.tgz" "$RUNS/$id/fetched.tgz" --project "$PROJECT" --zone "$(zone_of "$id")" --quiet
  tar -C "$RUNS/$id/fetched" -xzf "$RUNS/$id/fetched.tgz"
  rm -f "$RUNS/$id/fetched.tgz"
  echo "fetched $remote into $RUNS/$id/fetched/ (venvs, caches and bytecode excluded)"
}

cmd_delete() {
  local id="$1" name zone; name="$(name_of "$id")"
  zone="$(cat "$RUNS/$id/zone" 2>/dev/null || echo "$CPU_ZONE")"
  if gcloud compute instances describe "$name" --project "$PROJECT" --zone "$zone" >/dev/null 2>&1; then
    gcloud compute instances delete "$name" --project "$PROJECT" --zone "$zone" --quiet
  fi
  local left; left="$(gcloud compute instances list --project "$PROJECT" --filter="name=$name" --format='value(name)')"
  if [ -n "$left" ]; then echo "STILL PRESENT: $left" >&2; exit 1; fi
  local disks; disks="$(gcloud compute disks list --project "$PROJECT" --filter="name~^$name\$" --format='value(name)')"
  if [ -n "$disks" ]; then echo "leftover disks: $disks" >&2; exit 1; fi
  if [ -f "$RUNS/$id/created_at" ]; then
    local rate="$CPU_HOURLY_USD"
    case "$(cat "$RUNS/$id/kind" 2>/dev/null)" in gpu) rate="$GPU_HOURLY_USD" ;; gpu4) rate="$GPU4_HOURLY_USD" ;; esac
    local start now hours cost
    start="$(date -u -d "$(cat "$RUNS/$id/created_at")" +%s)"; now="$(date -u +%s)"
    hours="$(awk -v s="$start" -v n="$now" 'BEGIN{printf "%.2f", (n-s)/3600}')"
    cost="$(awk -v h="$hours" -v r="$rate" 'BEGIN{printf "%.2f", h*r}')"
    echo "deleted $name after ${hours}h, about \$${cost} at \$${rate}/h" | tee "$RUNS/$id/deleted.txt"
  else
    echo "deleted $name"
  fi
}

cmd_status() {
  gcloud compute instances list --project "$PROJECT" --filter="labels.purpose=kapso-bench" \
    --format='table(name,zone.basename(),status,machineType.basename(),creationTimestamp)'
}

case "${1:-}" in
  create)  [ $# -eq 3 ] || usage; cmd_create "$2" "$3" ;;
  install) [ $# -eq 4 ] || usage; cmd_install "$2" "$3" "$4" ;;
  run)     [ $# -eq 3 ] || usage; cmd_run "$2" "$3" ;;
  fetch)   [ $# -eq 3 ] || usage; cmd_fetch "$2" "$3" ;;
  delete)  [ $# -eq 2 ] || usage; cmd_delete "$2" ;;
  status)  cmd_status ;;
  *) usage ;;
esac
