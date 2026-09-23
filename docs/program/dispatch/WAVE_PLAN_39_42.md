# Waves 39–42, planned 2026-09-23 under `R-29`

**Written into the tree rather than held in a session**, because a session that restarts loses
its plan and this programme has lost one that way: wave 33 was laid out as three worktrees and
the session driving them died before dispatching, leaving branches nobody could account for.

`R-29` lets the integrator run these without asking. **It stops at two things: spending above
about $5 in a wave, and anything that changes who can reach the system.** Each wave below says
which of its parts could hit either.

## W39 — revocation and password change, and the corpus cleaned

**`R-26`'s first half, and it is the half that cannot be added later.** Revocation makes an
already-issued credential stoppable; every other guard in `R-26` can be bolted on afterwards
and this one cannot reach backwards.

| stream | owns | notes |
|---|---|---|
| `W39-REVOKE` | `contracts/api/v1/openapi.json`, the lock, `src/auditmanager/access/**`, `db/migrations/**`, `web/src` | a reseal **and** a migration. One stream carries both, because wave 34 proved a reseal splits badly |
| `W39-CORPUS` | `src/auditmanager/norms/**`, `tests/**` | `D-59`, `R-27`: re-recognise the 79 pages with the stand's key. **$2.58–$3.17** — inside the ceiling, and the only spend in this wave |

**What would stop it and come back to the owner:** if revocation needs the stand published, or
a default account changed, `R-29`'s second clause applies. Building what `R-26` ruled does not.

## W40 — rate limit, lockout, and the two inconsistencies

`R-26`'s second half: state around the token endpoint, no contract change expected.

Beside it, the rows that are decisions rather than work and that `R-29` now lets the integrator
take: **`D-67`** — two of nine collection operations answer `200` with an empty page where
seven answer `404`; pick the rule and change the minority. **`D-66`** — the fail-closed default
nothing holds, and `hmac.compare_digest` replaceable with `!=` without a red; one test each.

## W41 — the host, if it is there

**`R-28` says the machine is expected the same day**, so this wave is written two ways and the
integrator picks on the morning:

- **it arrived** — deploy from a clean clone, the certificate, TLS, and the **fifth**
  `PA-01` certification. Criteria 1 and 2 have been `cannot be established` for four
  certifications and both close here. `W26-HOST` left nothing to author: the TLS block is inert
  until a certificate appears and the runbook is written.
- **it did not** — the debt wave below moves up and W42 becomes the host wave.

## W42 — the debt wave

The cadence says every third wave closes debts and removes blockers, and waves 39–41 are all
building. Candidates, in the order the register measures them: the blind-guard tally (`D-69`'s
five instances in five waves — the pattern is now the subject), `D-68`'s selector, `D-58`,
`D-50`, and the `D-60` token count that must be taken with a real tokeniser before anything is
embedded.

**`D-9` is not here.** `R-9` placed the norms corpus after the owner's own manual pass, and
that pass has not happened. Nothing on this side is in the way — the stand is current, Russian
and reachable over a tunnel — so it enters whichever wave follows the owner saying they have
driven it.

## Lanes

Recorded in `PORT_REGISTRY.md` before each stream starts, per the defect that cost a gate run
when two waves improvised into one range.
