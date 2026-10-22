#!/bin/sh
# Starts the stub HTTP model and sshd. CLIENT_PUBLIC_KEY is the one public key the server accepts.
set -eu

[ -n "${CLIENT_PUBLIC_KEY:-}" ] || { echo "entrypoint: CLIENT_PUBLIC_KEY is required" >&2; exit 64; }

mkdir -p /etc/ssh/authorized_keys
# The line a runbook installs: restrict (no pty, no agent/X11 forwarding), a forced command that
# ignores whatever the client asks for, and -- for the tunnel test only -- one permitted forward.
printf 'restrict,port-forwarding,permitopen="127.0.0.1:8080",command="/usr/local/bin/forced-command.sh" %s\n' \
  "$CLIENT_PUBLIC_KEY" > /etc/ssh/authorized_keys/runner
chmod 0644 /etc/ssh/authorized_keys/runner

[ -f /etc/ssh/ssh_host_ed25519_key ] || ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key

mkdir -p /srv/www
printf '{"model":"stub-model","ok":true}' > /srv/www/ok.json
busybox httpd -f -p 127.0.0.1:8080 -h /srv/www &

# Absolute path: sshd re-executes itself on SIGHUP (rotate-host-key) and needs it.
exec /usr/sbin/sshd -D -e -f /etc/ssh/sshd_config
