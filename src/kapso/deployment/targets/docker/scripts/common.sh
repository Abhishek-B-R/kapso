# Shared by the docker target's scripts: the names, the run arguments and
# the health wait. Sourced, never run.
NAME="kapso-$KAPSO_DEPLOYMENT_NAME"
CONTAINER_PORT="${KAPSO_VALUE_CONTAINER_PORT:-8000}"
GPU="${KAPSO_VALUE_GPU:-none}"
HEALTH_URL="http://localhost:$KAPSO_PORT/health"

run_container() {
  local args=(-d --name "$NAME" -p "$KAPSO_PORT:$CONTAINER_PORT" --restart unless-stopped)
  if [ -n "${KAPSO_ENV_FILE:-}" ]; then
    args+=(--env-file "$KAPSO_ENV_FILE")
  fi
  if [ "$GPU" != "none" ]; then
    args+=(--gpus "$GPU")
  fi
  docker run "${args[@]}" "$NAME"
}

wait_for_health() {
  # Up to two minutes for the app to answer /health.
  local attempt
  for attempt in $(seq 1 60); do
    if "$KAPSO_INTERPRETER" - "$HEALTH_URL" <<'PY'
import sys
import urllib.request

response = urllib.request.urlopen(sys.argv[1], timeout=2)
sys.exit(0 if response.status == 200 else 1)
PY
    then
      return 0
    fi
    sleep 2
  done
  echo "the container $NAME did not answer $HEALTH_URL within 120 s; its last lines:" >&2
  docker logs --tail 50 "$NAME" >&2 || true
  return 1
}
