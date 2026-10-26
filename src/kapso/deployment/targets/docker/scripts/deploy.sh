# The docker target's deployment: the image built from the workspace, the
# container run with the env file, the port and the GPU request, and
# /health answering. Run from the workspace.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
touch .dockerignore
# Out of the image: the env file, the repositories and the hosts' own
# directories, the sealed evaluation, and the prepared mounts (a link into
# the campaign, which the image cannot follow).
for line in .env .git .claude .agents .codex '.kapso*' __pycache__ '*.pyc' kapso_evaluation prepared; do
  grep -qxF -- "$line" .dockerignore || echo "$line" >> .dockerignore
done
docker rm -f "$NAME" > /dev/null 2>&1 || true
docker build -t "$NAME" .
run_container > /dev/null
wait_for_health
echo "the container $NAME answers on port $KAPSO_PORT"
