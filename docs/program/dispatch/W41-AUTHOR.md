# W41-AUTHOR — the author of a decision, and two ports

**task_id:** `W41-AUTHOR` · **wave:** 41 (the debt wave) · **lane:** `gate-w41a`
**worktree:** `/root/w41author` · **branch:** `agent/w41-author` · **base:** `6aeda82` (`alpha-w40`)

## Frozen inputs

| | |
|---|---|
| contract | `contracts/api/v1/openapi.json` — **frozen. This task changes no contract.** 15 paths / 18 operations / 51 schemas |
| error catalog | `contracts/domain/v1/error-codes.json` — **22 codes, frozen.** Adding one is a reseal and the owner's |
| migration head | `0008_sign_in_throttle` — **frozen. This task adds no migration**; `expert_decision_event.author_label` already exists |
| `DecisionEvent.author_label` | already in the API schema, `min_length=1, max_length=128` (`src/auditmanager/api/schemas/models.py:561,594`) |

## allowed_paths

```
src/auditmanager/decisions/**
src/auditmanager/api/**
src/auditmanager/bootstrap/**
src/auditmanager/analysis/text/proxy.py
tests/**
docs/program/W41-AUTHOR.md
```

## forbidden_hotspots

`contracts/**` · `db/migrations/**` · `web/**` · `Makefile` · `pyproject.toml` · `uv.lock` ·
`package-lock.json` · `docs/program/DEBT_REGISTER.md` (the integrator owns it) ·
`docs/program/dispatch/**` except nothing — **you write only `docs/program/W41-AUTHOR.md`** ·
`.env` outside your own worktree · any container whose name does not begin `gate-w41a`.

Find something broken outside this grant: **report it in your report, do not repair it.**
That is how `D-72`, `D-74` and `D-76` reached the register.

---

## A1 — a decision is attributed to the reviewer who made it

`src/auditmanager/decisions/ledger.py:60`:

```python
CONFIGURED_AUTHOR_LABEL: Final[str] = "local-reviewer"
```

Every verdict by every reviewer is attributed identically. `OD-18` wants three to five named
experts in the alpha and `P04` exists to learn **whose** judgement was whose; with this constant
in place `P04` measures nothing it was built to measure.

**One rule beside that constant must survive the repair, and one is now false.**

- **Survives** — *"never taken from a request body; a client-supplied 'who did this' would be a
  subject identity in all but name."* Still exactly right. A request body naming an author is
  refused or ignored after your change exactly as before, and you write a test that says so.
- **False since wave 34** — *"PC-01 has no authentication."* It has. `src/auditmanager/api/security.py:403`
  builds `Subject(user_uid=..., login=..., token_epoch=...)` on every authenticated request —
  and `require_authorization` **returns `None`**, so no route can see it. That is the whole gap:
  the identity is established and then discarded.

**Build:** make the verified `Subject` reachable by the decision command surface, and have the
ledger take `author_label` from it.

Two constraints, both testable:

1. **Fail-closed.** A decision recorded with no authenticated subject is a **refusal**, not an
   anonymous row. Do not leave `"local-reviewer"` as a default that a missing subject falls back
   into — that is `D-66`'s exact shape, a fail-closed default nothing holds.
2. **Server-derived only.** The value comes from the verified credential. Measure first what the
   command surface currently accepts and prove the body cannot influence it.

**What the label *is* is your decision to make and to argue in the report.** The account's
`login` is the obvious answer and probably the right one. Say why, and say what it means that a
reviewer's login becomes visible to every other reviewer on every decision they read. Today
there is exactly one account, so nothing new is exposed to anybody; the question arrives with
the second account, which is owner-blocked work. **Register that consequence in your report and
do not design around it.**

**Prove it, do not assert it:** two different credentials record two decisions and the ledger
distinguishes them. Then mutate — pin the label back to a constant — and show the suite red.
`W12-DEC` recorded mutation `M21` (`"local-reviewer"` → `"someone-else"`) as **deliberately
green**. After this task it must be red, and your report quotes both states.

## A2 — `D-72`: a URL with no host is not a retryable dependency failure

`ProxySettings.__post_init__` (`src/auditmanager/analysis/text/proxy.py:61`) validates only the
`http://` / `https://` prefix. So `http://:59990` — no hostname — constructs successfully and
fails later as **`dependency_unavailable`, which the frozen catalog marks `retryable: true`**.
A lane pointed at nowhere retries a ladder against a configuration error.

This is not hypothetical: `infra/deploy/env/provider.env` on the owner's stand carries exactly
that URL today (`D-70`), so **this is what `D-70` looks like from inside the product.**

Reject a host-less URL at construction, in the same shape the two checks above it already use —
`DomainError(ErrorCode.INTERNAL_ERROR, message=...)`. **Do not add an error code.** If you
conclude the correct answer needs a new one, stop and report it; that is a reseal and the
owner's.

Prove both halves: the current code path really does end in a `retryable: true` code, and after
the change construction refuses.

## A3 — `D-74`: a parent-existence check costs a full parent read

`RunAdapter.get_run_status` assembles an entire `RunStatus` — run, stages, cost — to answer
*"does this run exist"*. `FindingAdapter.get_finding` reads evidence, verdict **and the decision
history**, which `listDecisionHistory` then reads a second time.

A narrow existence method on the ports (`src/auditmanager/api/routers/ports.py`) is the right
shape. **The hazard is the one that makes this a debt row rather than a chore:** a router calling
a method an implementation lacks is an `AttributeError` and a `500`. So the acceptance is that
**every** implementation has it — and you enumerate them by searching the tree, not by trusting
this brief. This brief says there are implementations in `src/auditmanager/bootstrap/adapters.py`
and `tests/integration/api/conftest.py`. **This brief has been wrong about file counts before.
Count them yourself.**

---

## Deliverables

1. The three repairs, each committed separately, each with its tests.
2. `docs/program/W41-AUTHOR.md` — the report. Open it **before** the first measurement.
3. Every guard you add **shown to fail**: mutate → red → revert → green, with the exact mutation
   and the exact failing assertion quoted. A mutation that reddens nothing is a coverage report,
   not a clean bill — and if one comes back green, **that is your finding**, not a formality to
   work around. Seven waves running, a quietly-dying mutation was the only thing that found a
   blind guard.
4. Anything outside the grant: reported, not repaired.

## Verification

```
cd /root/w41author
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
.venv/bin/python -c "import boto3"        # bootstrap has silently half-succeeded before
npm --prefix web ci
make gate > /root/w41a-gate.log 2>&1; echo "exit=$?"
grep -c 'GATE OK' /root/w41a-gate.log
```

**Read the result from the `GATE OK` line in the log, never from a status a harness hands you**
(`OPERATING_CONSTRAINTS.md` §4.62). Report the battery / foundation / frontend counts **with the
commit they were taken at**. Set `PYTHONDONTWRITEBYTECODE=1` for mutation runs — `__pycache__`
validates by mtime in whole seconds and has faked a green.

## Integration contract

You own nothing shared. No contract, no migration, no lockfile, no composition-root signature
that another lane reads. `W41-BLIND` runs beside you in `/root/w41blind` on `web/tests/**` and
`tests/e2e/**` — **`tests/e2e/**` is theirs, the rest of `tests/**` is yours.**

## Rollback

No feature flag. Every change here is either a refusal that did not exist (A1's fail-closed path,
A2) or a narrowing of a read (A3). Reverting is `git revert` of the three commits.

## Discipline

**Commit each step as you finish it.** A session that dies loses its worktree's uncommitted work
and this programme has lost a wave that way. Do not tag, do not push to `main`, do not merge —
the integrator does that.
