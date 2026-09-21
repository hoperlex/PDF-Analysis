# `W26-HOST` — everything the owner's VPS will need, prepared before it exists

**Opened 2026-09-21, on `agent/w26-host` from `origin/dev` `7535a17`.** This file is opened
before the first edit and filled as the work lands, which is why the sections below arrive
in the order they were driven rather than in the order they read.

`R-15` names this wave: *"everything that can be prepared **before** a VPS exists: a TLS
block that activates when a certificate appears, the deployment runbook, and the disk
headroom figure."*

## 0. What this session may not touch

`W26-OPS` is live in `deploy.sh`, `reset.sh`, `verify-deployed.sh` and
`compose.server.yml`. **Every one of those is read here and none is written**, which is the
constraint that shapes section 2: the TLS path cannot add a port or a mount to the compose
file, so it adds neither.

_(sections follow as they are driven)_
