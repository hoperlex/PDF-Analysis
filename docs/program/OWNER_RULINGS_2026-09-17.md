# Owner rulings, 2026-09-17

Recorded by the integrator the day they were given, against the tree at `431d753`. Four
answered by direct poll, three given in conversation before it.

`ALPHA_ROADMAP.md` is a **draft and a recommendation**; the ADRs and the architecture corpus
are the primary source of truth. That is itself one of the rulings below and it governs how
every other one is read.

## Given in conversation

| # | Ruling |
|---|---|
| **A** | **The ADRs are the primary source of truth.** A roadmap is a draft and a recommendation. |
| **B** | **FastAPI is core stack and its refusal was unjustified.** `ADR-0002`, `TECHNOLOGY_BASELINE.md`, `ARCHITECTURE_BIBLE.md` P-05 and `PROTOTYPE_PROFILE.md` §2 all name it. `api/README.md`'s "there is no HTTP framework, and that is deliberate" justified an absence from a lane-level pin set; corrected at `8805659`. |
| **C** | **The destination is a public application requiring HTTPS and authorization tokens**, not a single-operator localhost tool. |

## Answered by poll

| # | Question | Ruling |
|---|---|---|
| **R-1** | where it runs, and who reaches it | **The owner's own VPS host.** So TLS, DNS and hosting are in scope. |
| **R-2** | the FastAPI pin set | **Full set, with a licence named beside each pin.** §2 below is that diff, measured. |
| **R-3** | the contract reseal | **Tokens *and* the storage code.** `D-7`'s collision is settled at the reseal rather than left. |
| **R-4** | real client documents | **Permitted, wiped at the end of the pilot.** |

## 2. The R-2 pin set, measured rather than recalled

Licences read from each wheel's own `METADATA`, not from memory. Versions are today's latest;
the pin commit fixes them exactly.

**The addition is smaller than "a web framework" sounds**, because `anthropic` already pulled
FastAPI's and Starlette's cores into the closure.

| Distribution | Version | Licence | Status |
|---|---|---|---|
| `fastapi` | 0.141.1 | **MIT** | new |
| `starlette` | 1.6.0 | **BSD-3-Clause** | new |
| `uvicorn` | 0.53.0 | **BSD-3-Clause** | new |
| `click` | 8.5.0 | **BSD-3-Clause** | new — `uvicorn`'s only unmet requirement |
| `python-multipart` | 0.0.32 | **Apache-2.0** | new |

**Already satisfied by the existing closure**, so not additions: `pydantic` 2.13.5 (fastapi
needs ≥2.9.0), `typing_extensions` 4.16.0 (≥4.8.0), `anyio` 4.15.1 (starlette needs <5,≥3.6.2),
`h11` 0.16.0 (uvicorn needs ≥0.8).

**Five distributions. All permissive, none copyleft.**

### The test client is a sixth pin, and this needs the owner's eye

`starlette.testclient` does `import httpx`. **`httpx` is not importable in this venv** — what
is installed is `httpx2` 2.12.0, a *different distribution* providing a different module. So a
test client is not free:

| Option | Cost |
|---|---|
| pin `httpx` 0.28.1 (**BSD-3-Clause**) | one more distribution, plus `certifi` and `httpcore` if absent. Gives `TestClient` and `ASGITransport`, so the transport seam gets automated tests |
| drive the ASGI app directly over `anyio` | **zero new pins**, more test code, and the tests exercise the app rather than a client's view of it |

**Recommendation: pin `httpx`.** `D-5` is a 500 on the transport seam that only a socket
exposed, and the argument for pinning is that the seam gets automated coverage rather than
another manual harness outside the tree. But it is a sixth licence on a list the owner asked to
see, so it is named here rather than folded in.

## 3. What each ruling unblocks, and what it still needs

- **R-1** unblocks the deploy wave once the host details exist. **Still needed from the owner:**
  host name or address, who holds root, which ports may be opened, whether the provider proxy
  is reachable from it, and when access appears. **No secret belongs in a chat message** — the
  credential goes on that host's disk, by the owner, as `LIVE_RUN_INSTRUCTIONS.md` §2 already
  says for this repository.
- **R-2** unblocks the pin commit — a single-owner task under `FF-01` §2.8. The diff above is
  ready; the sixth-pin question is the only open part.
- **R-3** unblocks the reseal: a security scheme across all twelve operations, and a code for
  the storage refusal so one 403 stops meaning two things. `D-8` matters here — the catalog
  declares `"frozen": false, "status": "draft_candidate"`, so this is **an addition to a draft
  candidate, not a freeze-break**.
- **R-4** unblocks real-document sessions. **Still needed:** who uploads, and what event counts
  as "the end of the pilot" and therefore triggers the wipe. Nothing in this repository may hold
  such a document under any of the answers.

## 4. Still open, and still the owner's

- **`OD-18`** — three to five named experts with committed slots; `P4-BHV-01` waits on it alone.
- **`OD-17`** — the next corpus shape.
- **Whether `origin/main` advances.** It has been six waves behind. `W12-CERT` certified
  `e6eae1e`, so the condition `DEBT_REGISTER.md` §3 named is met; the certification holds **with
  one named exception**, `D-1.5`, which is about what a user sees rather than what the system
  does.
