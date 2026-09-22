# Port registry

**A lane's ports are a shared resource and nobody held the list. This file is the list.**

Read it before writing a lane into a brief, and add the row in the same commit that dispatches
the stream. A range with no row is free; a row with no stream is stale and may be taken.

## Why this file exists

On 2026-09-22 the integrator allocated `56140` to a wave-35 stream. It was already held by
`gate-w34dom-postgres`, a container belonging to a **different session's** wave. The stream hit
`Bind for 127.0.0.1:56140 failed: port is already allocated`, **did not touch the other lane's
container**, moved itself to `56148` and re-ran clean — which is the behaviour
`OPERATING_CONSTRAINTS.md` §4.5 asks for, and it cost a gate run.

The two sessions then traded ranges in messages. That works once and does not scale, and the
structural fault is §4.5's one layer up: **§4.5 records that a refusal about a shared resource
is information other lanes need. An allocation is the same thing and nothing recorded it.**

The other half was an ownership gap rather than a collision: wave 33's streams were handed
explicit ports and wave 34's were handed none, so wave 34's streams **chose their own** and
improvised into a range another session was handing out. **A brief that does not name a lane
delegates the choice to a session that cannot see the other lanes.**

## Held

| range | held by | since | free when |
|---|---|---|---|
| `55460`, `59060/59061` | `gate-b0` — the main checkout's own `.env` | standing | never; this is the integrator's lane |
| `55470`, `59100/59101` | `gate-w34api` | 2026-09-22 | wave 34 merges |
| `55480`, `59110/59111` | `gate-w34judge` | 2026-09-22 | wave 34 merges |
| `56140` | `gate-w34dom` | 2026-09-22 | wave 34 merges |
| `56148`, `59740/59741` | `gate-w35a` | 2026-09-22 | wave 35 merged; **released** |
| `31500` | the owner's alpha stand, `auditmanager-w19a` | standing | never |

**Reserved by convention, so a brief can allocate without asking:** `55470–55490` and
`59100–59120` are wave 34's until it merges. New lanes should take `561xx` with S3 at `597xx`,
and **must put their row here before the stream starts.**

## Check

```
ss -ltn | grep -oE '127.0.0.1:(55|56|59)[0-9]{3}' | sort -u
docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E '^gate-'
```

A port bound by a container this file does not list is a stale row or an unlisted lane, and
either way the answer is to measure before allocating rather than to assume the file is right.
**This file is a convenience, not an authority — the host is the authority.**
