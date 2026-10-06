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
| `55470–55490`, `59100–59120`, `56140` | wave 34 | 2026-09-22 | **released** — wave 34 merged at `31a8a53` |
| `56150`, `59750/59751` | `gate-w37a` | 2026-09-22 | wave 37 merges |
| `56160`, `59760/59761` | `gate-w37b` | 2026-09-22 | wave 37 merges |
| `56170`, `59770/59771` | `gate-w38a` | 2026-09-22 | wave 38 merges |
| `56180`, `59780/59781` | `gate-w39a` | 2026-09-23 | wave 39 merges |
| `56190`, `59790/59791` | `gate-w39b` | 2026-09-23 | wave 39 merges |
| `56180–56210`, `59780–59811` | waves 39 and 40 | 2026-09-23 | **released** — both merged at `6aeda82`; containers, volumes and networks removed by the integrator |
| `56220`, `59820/59821` | `gate-w41a` — `W41-AUTHOR` | 2026-09-23 | wave 41 merges |
| `56220–56230`, `59820–59831` | wave 41 | 2026-09-23 | **released** — merged at `6b5b500`, tagged `alpha-w41`; containers and volumes removed |
| `56240`, `59840/59841` | `gate-w42a` — `W42-SEAL` | 2026-09-23 | wave 42 merges |
| `56240–56250`, `59840–59851` | wave 42 | 2026-09-23 | **released** — merged at `01421b7`, tagged `alpha-w42` |
| `56260`, `59860/59861` | `gate-w43a` — `W43-COMPARE` | 2026-09-24 | wave 43 merges |
| `56270`, `59870/59871` | `gate-w43b` — `W43-PREP` | 2026-09-24 | wave 43 merges |
| `56260–56280`, `59860–59881` | wave 43 | 2026-09-24 | **released** — merged, tagged `alpha-w43.1` |
| `56290`, `59890/59891` | `gate-w44a` — `W44-JOURNEY` | 2026-09-24 | wave 44 merges |
| `56300`, `59900/59901` | `gate-w44b` — `W44-SEE` | 2026-09-24 | wave 44 merges |
| `56310`, `59910/59911` | `gate-w44j` — `W44-JUDGE-A`, then cross-judge **X** | 2026-09-24 | wave 44 closes |
| `56290–56320`, `59890–59921` | wave 44 | 2026-09-24 | **released** — merged, tagged `alpha-w44` |
| `56330`, `59930/59931` | `gate-w45a` — `W45-POS` | 2026-09-24 | wave 45 merges |
| `56340`, `59940/59941` | `gate-w45b` — `W45-READY` | 2026-09-24 | wave 45 merges |
| `56350`, `59950/59951` | `gate-w45j` — judge A, then cross-judge X | 2026-09-24 | wave 45 closes |
| `56330–56360`, `59930–59961` | wave 45 | 2026-09-25 | **released** — merged, tagged `alpha-w45` |
| `56370`, `59970/59971` | `gate-w46a` — `W46-SEAL` | 2026-09-25 | wave 46 merges |
| `56380`, `59980/59981` | `gate-w46b` — `W46-DASH` | 2026-09-25 | wave 46 merges |
| `56390`, `59990/59991` | `gate-w46j` — judge A, then cross-judge X | 2026-09-25 | wave 46 closes |
| `56400`, `60000/60001` | `gate-w46k` — cross-judge Y | 2026-09-25 | wave 46 closes |
| `56370`, `59970/59971`; API `56371` | `gate-w46a` — `W46-SPEND`, sub-stage B | 2026-09-28 | wave 46 merges |
| `56380`, `59980/59981`; API `56381`, Next `56383` | `gate-w46b` — `W46-WIRE`, sub-stage B | 2026-09-28 | wave 46 merges |
| `56390`, `59990/59991`; API `56391`, Next `56393` | `gate-w46j` — `W46-JUDGE-X` (judge A's databases `audit_w46j_judge`, `audit_w46j_judge2` still in it) | 2026-09-28 | wave 46 closes |
| `56400`, `60000/60001`; API `56401`, Next `56403` | `gate-w46k` — `W46-JUDGE-Y` | 2026-09-28 | wave 46 closes |
| `56370`, `59970/59971` | `gate-w46a` — `W46-GUARD`, sub-stage C | 2026-09-29 | wave 46 merges |
| `56380`, `59980/59981`; API `56381`, Next `56383` | `gate-w46b` — `W46-CLIENT`, sub-stage C | 2026-09-29 | wave 46 merges |
| `56390`, `59990/59991`; API `56391`, Next `56393` | `gate-w46j` — `W46-JUDGE-Z`, sub-stage C | 2026-09-29 | wave 46 closes |
| `56370–56400`, `59970–60001` | wave 46 | 2026-09-29 | **released** — tagged `alpha-w46` (local); containers, volumes and networks removed; `w46seal`/`w46dash` moved to wave 47 |
| `56410`, `60010/60011`; API `56411` | `gate-w47a` — `W47-GATE` | 2026-09-29 | wave 47 merges |
| `56420`, `60020/60021`; API `56421`, Next `56423` | `gate-w47b` — `W47-PASS` | 2026-09-29 | wave 47 merges |
| `56430`, `60030/60031`; API `56431`, Next `56433` | `gate-w47j` — judge A, then cross-judge X | 2026-09-29 | wave 47 closes |
| `56440`, `60040/60041`; API `56441`, Next `56443` | `gate-w47k` — cross-judge Y | 2026-09-29 | wave 47 closes |
| `56290–56320`, `59890–59921` | wave 44 | 2026-09-24 | **released** — streams and two cross-judges merged; containers, volumes and worktrees removed |
| `31500` | the owner's alpha stand, `auditmanager-w19a` | standing | never |
| `56450`, `60050/60051`; API `56451`, Next `56453` | `gate-w48dj2` — `W48-DURABLE-JUDGE-2` | 2026-10-05 | judge hands back |
| `56460`, `60060/60061`; API `56461`, Next `56463` | `gate-w48df2` — `W48-DURABLE-FIX-2` | 2026-10-05 | merged into W48 closure |
| `56470`, `60070/60071`; API `56471`, Next `56473` | `gate-w48g2` — `W48-GUARDS-2` | 2026-10-05 | merged into W48 closure |
| `56480`, `60080/60081`; API `56481`, Next `56483` | `gate-w48tails` — `W48-TAILS` | 2026-10-05 | merged into W48 closure |
| `56490`, `60090/60091`; API `56491`, Next `56493` | `gate-w48public` — `W48-PUBLIC-01` | 2026-10-05 | merged into W48 closure |
| `56500`, `60100/60101`; API `56501`, Next `56503` | `gate-w48judgez` — `W48-JUDGE-Z` | 2026-10-05 | W48 closes |
| `56510`, `60110/60111`; API `56511`, Next `56513` | `gate-w48close` — `W48-INT-CLOSE` | 2026-10-05 | candidate published to `origin/dev` |
| `56520`, `60120/60121`; API `58520/58521`, web `53020` | `gate-w48judgez` — `W48-JUDGE-Z` as actually run (the `56500` row was allocated, not used) | 2026-10-05 | **released** — stand stopped by the judge |
| `56530`, `60130/60131` | `gate-w48fixc` — `W48-FIX-C` | 2026-10-05 | **released** — merged at `70f6c9e`, `make down` |
| `56540`, `60140/60141` | `gate-w49int` — W49 integration and its gates | 2026-10-05 | W49 closes |
| `56550`, `60150/60151` | `gate-w49access` — `W49-ACCESS-01` | 2026-10-05 | merged |
| `56560`, `60160/60161` | `gate-w49dec` — `W49-DECISIONS-01` | 2026-10-05 | merged |
| `56570`, `60170/60171` | `gate-w49seal` — `W49-SEAL-01` | 2026-10-05 | merged |
| `56580`, `60180/60181` | `gate-w49bff` — `W49-BFF-01` | 2026-10-05 | merged |
| `56590`, `60190/60191` | `gate-w49edge` — `W49-EDGE-01` | 2026-10-05 | merged |
| `56600`, `60200/60201` | `gate-w49qa` — `W49-QA-01` | 2026-10-05 | merged |
| `56610`, `60210/60211` | `gate-w49jx` — `W49-JUDGE-X` | 2026-10-05 | W49 closes |
| `56620`, `60220/60221` | `gate-w49jy` — `W49-JUDGE-Y` | 2026-10-05 | W49 closes |
| `56630`, `60230/60231` | `gate-w49fix` — `W49-FIX` | 2026-10-06 | merged |

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
