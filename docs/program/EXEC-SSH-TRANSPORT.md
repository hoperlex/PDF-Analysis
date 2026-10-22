STATUS: 1/5 ssh_transport.py written, probed against real ssh client (12:04 +05)

# EXEC-SSH-TRANSPORT - progress and report

Lane: agent/exec-ssh-01 (base c00b276a). Standalone SSH transport for executor connections
(EXEC-SSH-01 Work 1-4, transport half). Owner rulings: R-144e (elapsed time governs), R-144b
(basic functional checks only).

Steps: 1 ssh_transport.py, 2 claude_output.py, 3 Dockerfile.api, 4 tests/fixtures/sshd,
5 tests (unit + sshd integration).
