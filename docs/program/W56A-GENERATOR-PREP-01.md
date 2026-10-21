# W56A-GENERATOR-PREP-01 — synthetic AR v2 corpus

**Status:** implementation candidate on `w56a/generator`, based on published
`origin/dev=da355edabcc1282ea3a05a713372bbb25560ccf7`. The corpus is
synthetic and uses no provider or customer document.

## Result

- 10 two-page PDF portal bundles, 21 grounded positive cases (three in each
  of seven categories) and seven near-miss controls. Each category appears
  in at least two bundles. Two missing-content cases quote a supplied promise
  and name a sheet or section absent from the extracted supplied headers.
- `tools/fixtures/seeded/generate.py` rebuilds all bytes twice in `--check`
  mode and compares them with the committed files. Each PDF contains an
  embedded committed font; the portal bundles are validated by the W55b
  bundle validator. The first bundle contains a deliberate recognised-only
  decoy that is refused as a PDF citation.
- `expected_issues.json` records bundle IDs, categories, archetypes, exact
  page/quote evidence, control scopes, expected absence and individual byte
  digests. SHA-256 of the manifest:
  `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`.

## Fixture bytes

| Bundle | PDF SHA-256 | Portal ZIP SHA-256 |
| --- | --- | --- |
| `ar_v2_01` | `44543219474c19870ec2ec0efe55f14a0fd109782a82e27f0ebf757204a01b17` | `8348527aca92c1bc1cd5d8d07aceabe37c9ae6cbe8f9c1c138d411614900de86` |
| `ar_v2_02` | `e20dc71f3a0bc959d2f884f0379822c126d058813c0609d7bdad50c5d992edf1` | `3b17ec18d435c33e0b6110d8af7f8a433925251724931ec2a7a532b4e48b8fd0` |
| `ar_v2_03` | `b71eaf3f37d65ff2f48e2035278d3901792e663ea1185cf4042b0568ceedbb73` | `1830fc43dbfc8854886f88f2065bbc038f7f0906ed86c7f830cbb5a8abf6bbc5` |
| `ar_v2_04` | `9602093fb5f707eab06c726a3b573d4127861f3a94ac0b69b9209e4124840059` | `d110fd987adebdfdd45285c8075f5d469a3e171b4a4b2f9284038adf0880afd7` |
| `ar_v2_05` | `b97ddb3e3dc53df643c384aa5155b3a223b573f7896a02461094662137a5f528` | `50138df47d49d9da19757e16e1a831db80783b541b7ef984d59d759d10ab3a2a` |
| `ar_v2_06` | `cc4c7b76e187e96199160b35df10831df1a29478fa6649dfdecc851837e4864a` | `2b7ca5a2225ded543aa0c89e0f544b0bae7d5f6c368ae6a3242eb1212624e2c5` |
| `ar_v2_07` | `40a1e36c8f1a7b214eb53dc77e76fd22d1d19ea9563cd215d5a1f143911222ae` | `4feed0f300fdec2687caf61f769aff7edb3b55e6bf6c9aeb092203f1f6f4df00` |
| `ar_v2_08` | `df46ce4de28c09d5e7bf810334aa2804e66ea1a77a85f3478c0d199212247394` | `36df6758ec9dde91590f0bc554a3785e0957ae291161a4fd2aa1e798687dcebb` |
| `ar_v2_09` | `c8a0ca8b0b6cd58010a66213ba436343c462abca41eb4e7bf72c09ee14b13e52` | `3cc07d390d909a5526e14af624de376a2b6ed726e6f4da33f9310b5bee240e7b` |
| `ar_v2_10` | `80d4148cf381d3a7fc64ba62cb1dfe6fd4377184ce23703388ad7fca273dc963` | `fa2bc6fd05eb8a135936c326fed85820ed5bb15e268b5b136d04f7e1cf3cdc34` |

## Addressed checks

- `.venv/bin/python tools/fixtures/seeded/generate.py --check`: passed; two generations and every committed byte agree.
- `.venv/bin/python -m pytest tests/contract/fixtures_seeded -q`: **41 passed**. There is one planted quote mutation for each positive and control case; all 28 are rejected. Additional tests cover an absent-content promise, control reclassification and a portal-only quote.
- `git diff --check`: passed. No full local gate or live call ran.

## Changed files and ownership

- New source: `tools/fixtures/seeded/{__init__,cases,generate,validate}.py`.
- New tests: `tests/contract/fixtures_seeded/test_ar_v2_seeded.py`.
- New fixtures: `fixtures/evaluation/ar_v2/expected_issues.json` plus ten
  PDF and ten ZIP files under `bundles/`.
- This report is the only new documentation file.
- No existing fixture, contract, migration, runtime, web, root dependency,
  `P02_LOCK.json`, `baseline.json`, recording or forbidden hotspot changed.

## Integrator instruction and limits

Merge the exact branch after SEAL from `da355eda`, then publish only under a
dedicated `W56A-INT-GENERATOR-01` integration task. The later HARNESS task
owns recordings, matching and a measured baseline. These generated
expectations are not recall or precision measurements. The model identity
block remains in force; no beta or quality verdict is asserted.
