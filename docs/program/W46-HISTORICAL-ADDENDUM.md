# Wave 46 historical evidence addendum

**Added 2026-10-02 by `W48-GOV`.** This file corrects and bounds the record defects registered
as `D-117`. It does not replace a wave-46 report and it does not turn a measurement that was
missing then into one performed then.

## Immutable sources

The six W46 source reports are byte-identical to the Stage-B frozen base
`fad3c28748ef52bc9b5f711191ff0130483e0055`. Captured 2026-10-02 with:

```text
for f in docs/program/W46-{DASH,WIRE,CLIENT,GUARD,SEAL,SPEND}.md; do
  sha256sum "$f"
  git show fad3c28748ef52bc9b5f711191ff0130483e0055:"$f" | sha256sum
done
```

| immutable report | SHA-256 at frozen base and current tree |
| --- | --- |
| `W46-DASH.md` | `f2040b4f70fdc6fc0884f8ed2adcac32d70fa8760e9a47e945fed9bd410b1078` |
| `W46-WIRE.md` | `1f7ee4a3226d901435efd53de685e07dc231d32b1bfd3e73c96c144b9d2d7791` |
| `W46-CLIENT.md` | `2c4dbd383563c4d80f0cbb81a5c388979df6c2a02634359a610163c35c1d4426` |
| `W46-GUARD.md` | `2dc708a5360d78b214c63d3502725037e37ca0e3736496955b8f6a900bfcbf03` |
| `W46-SEAL.md` | `d5da5c37c096ff765f011ad06c348f636fa0aa360c2786fb9e7b0c9cb8d4387c` |
| `W46-SPEND.md` | `f556467aed4a723e090490a466db4b9beb4bdadb1cc94c7c358ed6a3869884e9` |

The equality is executable in `tests/contract/program/test_wave_governance.py`; the hashes here
make the observation reviewable without trusting the test's conclusion.

## What the three incomplete reports can and cannot prove

### `W46-WIRE`

The source report ends after its live W4/W5 measurements and records no final gate. The merge
commit `1c38c526da53b31d4749a09487c5296d56449ba5` is more precise than the later register prose:
its message says the stream gate on `c26340f` was **red**, `2 failed / 2498 passed`, and that the
surface-prose red was repaired later at the join. `5bafb7ffc0b5638dda82ce71c7d69f630b26dece`
is that later prose repair.

On 2026-10-02 `/root/w46b-gate.log` hashes to
`c47df87a7f150b7b23f549bcda7baaf8bff6e92f648cd559f16feccc139631a7` and ends
`Makefile:1026: gate Terminated`, not `GATE OK`. Logs are mutable host evidence; this observation
does not prove what the path held on 2026-09-28. The durable conclusion is narrower: there is no
task-local final green gate in `W46-WIRE.md`, and this addendum does not invent one.

### `W46-CLIENT`

The source report ends by saying it will rerun the full gate and never appends the result. The
immutable merge commit `d56ae057fc895acf0ab4f7cb48f78bf9065fabbb` records the stream gate on
`c4e5575` as `GATE OK`, backend **2504**, frontend **1134 in 80 files**.

The host log was re-read on 2026-10-02, not assumed from its filename:

```text
/root/w46c-gate.log
2504 passed, 5 skipped, 4 warnings, 169 subtests passed
Test Files 80 passed (80)
Tests 1134 passed (1134)
GATE OK: battery, foundation, frontend and whitespace all pass
sha256 900df2d0ff562d9b68d77bbbce68c22bc08e4c244ae22636b760879f9c617153
```

This corroborates the commit message; it is new dated evidence, not a retroactive edit to the
stream report.

### `W46-GUARD`

The source report's `## 8. Final gate` still says `*(filled at the end)*`. The immutable merge
commit `08f0e7f066b0643098909fa850680364925bbafa` records the stream gate on `2c2be2b` as
`GATE OK`, backend **2516**, frontend **1118 in 79 files**.

Captured again on 2026-10-02:

```text
/root/w46g-gate.log
2516 passed, 5 skipped, 4 warnings, 169 subtests passed
Test Files 79 passed (79)
Tests 1118 passed (1118)
GATE OK: battery, foundation, frontend and whitespace all pass
sha256 be0a36a6ce222094d71c145fc71537abee2300e2e945dd249f896161203122db
```

## Two exact corrections

1. `W46-CLIENT.md` quotes the M5 neighbour-row mutation as
   `AR: expected 0 to be 3`. The independent re-run in `W46-JUDGE-Z.md` records the actual
   committed-fixture failure: `AI: expected 4 to be +0`. The repair itself is real; the stream's
   quoted output is not. The original quote stays visible in its source report.
2. The historical W46-GUARD paragraph in `web/FRONTEND_LOCK.json` says `069f656` made spend
   optional and absent-when-no-calls “in behaviour”. The behaviour landed in
   `f50e6565cbba324d8e832f1973afefc65db43458`; the contract reseal landed in
   `069f656b363c4a91b0f8f0df66dbc6359f9e18f6`. The digest, not `content_commit`, is the lock's
   conformance authority. This governance task does not own or rewrite that frozen lock.

`D-117` also records that two W46-GUARD proof tests may fail for the wrong reason if a future
cookie parameter legitimately declares `422`. That is a prospective test-design limitation, not
missing historical evidence, and this addendum does not claim to repair it.

## Wave-level closing evidence

Whatever the three stream reports omitted, wave 46 did receive a later integrated gate on exact
candidate `1196ca7f3e14cc4b944fa8d193d8cb1c8fc02f3f`. Re-read 2026-10-02:

```text
/root/w46-final-gate.log
2516 passed, 5 skipped, 4 warnings, 169 subtests passed
Test Files 80 passed (80)
Tests 1135 passed (1135)
GATE OK: battery, foundation, frontend and whitespace all pass
sha256 fa1b5bcc7a2f1b9e72aa73d731150e3124a1182add0cc96793af40be6f958642
```

Commit `e47d657250f869e62ecbcd977f701552fb9091ca` closed the state record and tagged
`alpha-w46`. This proves the integrated wave candidate, not a task-local gate the individual
authors failed to record. Keeping those two claims separate is the purpose of this addendum.
