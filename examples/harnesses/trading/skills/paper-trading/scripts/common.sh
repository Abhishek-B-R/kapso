# Shared by the paper-trading scripts: the runner's files and how to
# start it. Sourced, never run.
RUNNER="deploy/run_paper.py"
PID_FILE="deploy/paper.pid"
LOG_FILE="deploy/paper.log"

runner_alive() {
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2> /dev/null
}

start_runner() {
  if [ ! -f "$RUNNER" ]; then
    echo "no $RUNNER in the workspace: write it as the paper-trading skill says" >&2
    return 1
  fi
  if runner_alive; then
    echo "the paper runner already runs (pid $(cat "$PID_FILE"))"
    return 0
  fi
  nohup "$KAPSO_INTERPRETER" "$RUNNER" --loop >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1
  if ! runner_alive; then
    echo "the paper runner ended at once; its log:" >&2
    tail -n 20 "$LOG_FILE" >&2
    return 1
  fi
  echo "the paper runner runs (pid $(cat "$PID_FILE")), its log at $LOG_FILE"
}
