# Test sshd for the executor SSH transport (EXEC-SSH-01). Not an image anyone deploys.
#
# Key-only authentication, one account (`runner`), and one forced command with `restrict`:
# exactly the shape the runbook installs on a real machine (plan T-6), but the command is a
# tiny script that echoes its stdin as JSON and can sleep, fail, print too much or answer like
# `claude -p`. A stub HTTP model listens on 127.0.0.1:8080 inside the container, reachable only
# through the key's `permitopen`, to prove the tunnel.
FROM alpine:3.20

RUN apk add --no-cache openssh-server openssh-keygen jq \
 && adduser -D -s /bin/sh runner \
 && sed -i 's/^runner:!:/runner:*:/' /etc/shadow

COPY sshd_config /etc/ssh/sshd_config
COPY forced-command.sh /usr/local/bin/forced-command.sh
COPY rotate-host-key.sh /usr/local/bin/rotate-host-key
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/forced-command.sh /usr/local/bin/rotate-host-key /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
