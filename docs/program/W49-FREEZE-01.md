# W49-FREEZE-01 — completion report

## Result

**DONE.** W49 (identity) is frozen on code base `23e0579a2009d320011a87b2f0a5b429f87920ab`, the W48
closure candidate. Every lane starts from the commit that carries this report on
`integration/w49`.

```yaml
wave_id: W49
contract_set:
  domain: 1.0.0-draft.1 revision 8, 27 opaque identities
  api: 17 paths / 20 operations / 61 schemas
  api_sha256: f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585
  error_catalog: 22
migration_head: 0014_durable_analysis_effects
frozen_code_base: 23e0579a2009d320011a87b2f0a5b429f87920ab
rulings: R-55 … R-61 (OWNER_RULINGS §3.19, W49-RULE-01)
frozen_by: W49-FREEZE-01
```

## Entry conditions

- `W48-INT-CLOSE` done; full gate on the base `GATE OK` (recorded in `W49-RULE-01.md`).
- `R-55` … `R-61` recorded.
- Contract set measured on the base: triple 17 / 20 / 61, SHA-256 above, 22 codes, 27
  identities, revision 8, one migration head `0014_durable_analysis_effects`;
  `git diff --stat 6118e66 HEAD -- contracts` is empty.
- `origin/dev` is still `9b5219e`: publishing the base was refused by the session's permission
  layer and is the owner's step. Lanes branch from the local integration line meanwhile.

## Task files

`W49-ACCESS-01`, `W49-DECISIONS-01`, `W49-SEAL-01`, `W49-BFF-01`, `W49-EDGE-01`, `W49-QA-01`,
`W49-JUDGE-X`, `W49-JUDGE-Y` — generated from `docs/program/dispatch/W49-PLAN.md` §4 and
`docs/templates/TASK_TEMPLATE.md`; each premise re-measured on the base.

## Ports

`PORT_REGISTRY.md` rows `56540` … `56620` / `60140` … `60221`, measured free with `ss -ltn`
before allocation. The W48 judge and fix rows are corrected to the ports actually used.

## Checks

- `tests/contract/program/test_wave_governance.py` — green
- `git diff --check` — clean

## Forbidden-hotspot proof

Only task files, this report and `PORT_REGISTRY.md` change.
