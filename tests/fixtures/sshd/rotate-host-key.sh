#!/bin/sh
# Replace the server's host key and make sshd load it: the "changed host key" case.
set -eu
rm -f /etc/ssh/ssh_host_ed25519_key /etc/ssh/ssh_host_ed25519_key.pub
ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key
kill -HUP "$(cat /run/sshd.pid)"
sleep 1
