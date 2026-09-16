# Wave 11 plan — repair what wave 10 found

Written 2026-09-16 by the integrator. Base `30d129c`, published as `origin/dev`. Gate:
1264 passed / 5 skipped / 116 subtests.

## 1. Three streams, and the wave is smaller than wave 10

| Stream | Repairs | Instance |
|---|---|---|
| `W11-RD` | the read path does not verify what the manifest promised | `gate-w11a` 55630 / 59230 / 59231 |
| `W11-FIX` | two false comments, an undercounted docstring, `cost_basis` on the wrong path, a filename property with no consumer | `gate-w11b` 55640 / 59240 / 59241 |
| integrator | the quarantined suite that reads as coverage | `gate-w3` 55550 / 59150 / 59151 |

Wave 10 ran five streams; this one runs three, because that is how much work there is. Four
of the five product defects are small and one of them turned out smaller than its own
description once I checked the contract. **Inflating a wave to look symmetric would be the
same failure as padding a sweep.**

## 2. What is different from wave 10

Wave 10's streams wrote tests and were forbidden to touch `src/`. **These streams write
product code.** So:

- **every repair needs a guard that reddens without it** — mutated back to the defect and
  watched fail, not merely green afterwards;
- **no stream certifies its own repair.** A later session re-certifies PC-01;
- **behaviour changes carry re-certification debt**, so each stream says what an operator or
  a stored row would observe differently.

## 3. Verified before dispatch, and one item shrank

Each defect was checked against the tree while writing the briefs, not taken from the wave-10
reports:

- **The read path** — confirmed line by line. `read_source_bytes` holds `entry.sha256` and
  never compares it; `s3.read` compares against the object's **own** metadata digest and
  skips the check when that metadata is absent. Still not inducible through the twelve
  operations, so both PC-01 certifications stand and the brief says so explicitly.
- **`cost_basis`** — confirmed. The overrun branch carries it, the success branch does not,
  and the module's own comment shows this is the unfinished half of a repair already begun.
- **The filename** — **shrank on inspection.** `openapi.json` says the download name is
  "presentation only and is never an identity" and pins no value, so the UI and the header
  differing is *permitted*. The defect is only the dead property that reads as the source of
  truth. A brief written from the wave-10 summary would have sent a session to reconcile
  three names across three trees for no reason.
- **The comments** — confirmed, including that my own wave-10 brief said "seven forbidden
  shapes" when there are six. That brief is why `W11-FIX` is told to count rather than
  believe.

## 4. What the integrator takes

**The quarantined suite that reads as coverage** — `W10-API`'s finding, and the single
largest systematic reason its surface yielded 36 unreddenable rules from 77.

`tests/contract` exercises five of the six forbidden shapes and both identifier catalogs.
`make gate` ignores it. `PROTOTYPE_PROFILE.md` §6.3 quarantines it as red before any wave
starts. So the repository contains tests that look like evidence, are findable by grep, and
protect nothing — and a reviewer who checks whether a rule is covered will be told yes.

This is governance rather than product, which is why it is mine and not dispatched.

## 5. Carried into every brief from what wave 10 cost

- `make mutation-copy`, replacing the prose recipe that was wrong since wave 3 and
  **manufactured reds**.
- Baseline the unmutated copy before trusting any red — the instruction that matters more
  than the directory list.
- Pin literals; wave 10 found the third form of that failure, where a test derives its
  *input* from the constant it tests and raising the constant is an out-of-memory kill rather
  than a red test.
- Read the mutated line back for **meaning**: four wave-10 streams wrote mutations that did
  not mutate.
- A session-unique scratch directory for logs; the five wave-10 streams shared one and read
  each other's gate output.
- Commit as you go; wave 10's first attempt lost four sessions to a restart.

## 6. After this wave

Wave 12 is the re-certification. `src/` changes here for the first time since `c0d7daf`, so
`W6-CERT`'s certification stops describing the tree the moment `W11-RD` lands.

## 7. Still owner-blocked

`OD-18` (experts, and `P4-BHV-01` waits on it alone), `OD-17` (the next corpus shape), the
21st error code, and whether `origin/main` advances.
