#!/bin/sh
# Remove the fixture container and image by their exact names (never by pattern).
set -eu
name="${EXEC_SSHD_CONTAINER:-exec-ssh-sshd}"
docker rm -f "$name" >/dev/null 2>&1 || true
docker rmi "$name:fixture" >/dev/null 2>&1 || true
