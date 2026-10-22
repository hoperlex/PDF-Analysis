#!/bin/sh
# Build and start the fixture container, then print the environment test_ssh_sshd.py reads.
#   eval "$(tests/fixtures/sshd/up.sh)"
#   python3 -m pytest -q -p no:cacheprovider tests/integration/executors/test_ssh_sshd.py
#   tests/fixtures/sshd/down.sh
set -eu

here="$(cd "$(dirname "$0")" && pwd)"
name="${EXEC_SSHD_CONTAINER:-exec-ssh-sshd}"
port="${EXEC_SSHD_PORT:-52222}"
state="${EXEC_SSHD_STATE:-$(mktemp -d)}"

docker build -q -t "$name:fixture" "$here" >&2
mkdir -p "$state"
rm -f "$state/client_key" "$state/client_key.pub" "$state/refused_key" "$state/refused_key.pub"
ssh-keygen -q -t ed25519 -N '' -C exec-ssh-fixture-client -f "$state/client_key"
ssh-keygen -q -t ed25519 -N '' -C exec-ssh-fixture-refused -f "$state/refused_key"
docker run -d --name "$name" -p "127.0.0.1:$port:22" \
  -e "CLIENT_PUBLIC_KEY=$(cat "$state/client_key.pub")" "$name:fixture" >&2

i=0
until docker exec "$name" test -s /run/sshd.pid 2>/dev/null; do
  i=$((i + 1))
  [ "$i" -le 50 ] || { echo "sshd did not start" >&2; docker logs "$name" >&2; exit 1; }
  sleep 0.2
done

echo "export EXEC_SSHD_PORT=$port EXEC_SSHD_STATE=$state EXEC_SSHD_CONTAINER=$name"
