# W57A-CORPUS-SOURCE-PREP-01 — local norm-source coverage

**Task:** `tasks/W57A-CORPUS-SOURCE-PREP-01.md`. **Base:**
`5f742b22c109b8f0b289962750d305495a3449c3`. This is a preparation
inventory for W57a, not `W57A-FREEZE-01` or `W57A-MAP-01`.

## 1. What was measured

The read-only bootstrap file
`/root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json` has SHA-256
`160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`.
Its `summary.documents` and actual `documents` length are both **674**. The
manifest was generated 2026-09-10. The report below matches exact document
family/edition prefixes in `slug`; it does not read or copy norm text.

For the ten present documents selected in §2, all manifest `blocks_count`
values total **546** and all 546 are marked `recognized`; each selected row's
`missing` list is empty. A recognized source block is not a reviewed canonical
paragraph, a verified custody binding, an effective edition or a sound clause
target. The 38 document metadata fields have only `block_status` among fields
whose names include status, edition, validity, effectiveness or replacement.

## 2. Exact family query and results

This query is deliberately anchored to one edition per family. It prints
`family`, matched row count, total source blocks, recognized blocks, and rows
with nonempty `missing`. Run against the manifest digest in §1:

```python
import json, re
from pathlib import Path

path = Path('/root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json')
docs = json.loads(path.read_text())['documents']
patterns = {
    'SP54-2022': r'^СП_54_13330_2022',
    'SP118-2022': r'^СП_118_13330_2022',
    'SP1-2020': r'^СП_1[._]13130[._]2020',
    'SP3-2009': r'^СП_3[._]13130[._]2009',
    'SP7-2013': r'^СП_7[._]13130[._]2013',
    'FZ123': r'^Федеральный_закон_от_22_07_2008_N_123-ФЗ',
    'SP59-2020': r'^СП_59_13330_2020',
    'SP50-2024': r'^СП_50_13330_2024',
    'SP51-2011': r'^СП_51_13330_2011',
    'SP51-amend3': r'^Изменение_N_3_к_СП_51_13330_2011',
    'SP2': r'^СП_2[._]13130',
    'SP4': r'^СП_4[._]13130',
    'SanPiN': r'^СанПиН_1[._]2[._]3685',
    'SP112': r'^СП_112[._]13330[._]2011',
}
for family, pattern in patterns.items():
    hits = [d for d in docs if re.search(pattern, d['slug'], re.I)]
    print(family, len(hits),
          sum(d.get('blocks_count', 0) for d in hits),
          sum(d.get('block_status', {}).get('recognized', 0) for d in hits),
          sum(bool(d.get('missing')) for d in hits), sep='\t')
```

```text
SP54-2022      1   52   52  0
SP118-2022     1   56   56  0
SP1-2020       1   67   67  0
SP3-2009       1   12   12  0
SP7-2013       1   45   45  0
FZ123          1  101  101  0
SP59-2020      1   55   55  0
SP50-2024      1   92   92  0
SP51-2011      1   65   65  0
SP51-amend3    1    1    1  0
SP2            0    0    0  0
SP4            0    0    0  0
SanPiN         0    0    0  0
SP112          1   32   32  0
```

These are manifest matches, not a claim that every selected source has a
usable paragraph span. The source `slug` identifies a bootstrap folder, not
the `ndoc_` id W57a will pin. The query's negative matches are limited to its
anchored family patterns and this manifest version.

## 3. Category and legacy-source routing

| Planned W57a category | Candidate bootstrap families present | Legacy АР cues for map review | Boundary |
| --- | --- | --- | --- |
| `evacuation` | СП 54.13330.2022, СП 118.13330.2022, СП 1.13130.2020 | `checklist.md` 19–22, 25; `AR.md` 25, 59 | Width, distance, exits and stair type need scoped verified paragraphs; the legacy thresholds are not inputs. |
| `fire_safety` | 123-ФЗ; СП 54, СП 118, СП 1, СП 3, СП 7 above | `checklist.md` 23–24, 58–59; `AR.md` 22 | СП 2/4.13130 are absent. СП 112.13330.2011 is present but explicitly excluded by W57 plan §A1. Fire-equipment ГОСТ candidates are not enumerated by this task. |
| `accessibility` | СП 59.13330.2020 | `checklist.md` 37–42; `AR.md` 83 | The object's scope and a cited paragraph must be established before any requirement is asserted. |
| `insulation` | СП 50.13330.2024 | `checklist.md` 30; `project_params.md` 11, 28–30, 53–55 | Compare an explicitly stated document value with a reviewed requirement; no independent thermal calculation. |
| `sound` | СП 51.13330.2011 and its Изменение №3 | `checklist.md` 5; `AR.md` 86 | The amendment is a separate manifest document, not a newer base edition; the owner resolves its applicability. |

The exact five category names and exclusions come from `W57-PLAN.md` §A1.
The legacy file identities and the broader W56a exclusion review are in
`W56A-LEGACY-SOURCE-01.md` §1–§2. This table is a search route for the map
owner, not a 22–25-item map or a target/paragraph decision. In particular,
the source line 14 on door widths may need both evacuation and accessibility
scope; no category assignment is made here.

## 4. Gaps and limitations

- The bootstrap manifest has no document legal-status or replacement field.
  A name/year match and recognized blocks cannot certify applicability,
  edition authority or a quoted requirement.
- СП 2.13130 and СП 4.13130 have zero matched rows. The plan excludes their
  subject clauses and those deferring to them. СП 112 is not a replacement.
- СанПиН 1.2.3685-21 also has zero matches, but insolation is deliberately
  after beta under W57 plan §A1. It is not a W57a map gap to fill by inference.
- The promoted database's reviewed `ns_` id, content key, embedding build,
  canonical paragraphs, `ndoc_`/`npar_` identifiers, reliability flags and
  custody bindings were not queried. A bootstrap manifest does not attest to
  any of them. Source blocks can be recognized while particular paragraphs
  remain unreliable or a target span exceeds the prompt budget.
- W55b acceptance, W56a close, W57a owner rulings/freeze and the required
  promotion-database review have not happened in this task.

## 5. Handoff, checks, contracts and rollback

`W57A-FREEZE-01` should re-run §2 on its accepted source and separately pin
the reviewed promotion snapshot, current/build identities and resources named
in the plan. `W57A-MAP-01` should start from §3's cues, remove every number and
legacy clause reference from candidate item text, resolve exact reliable
paragraph spans on that snapshot, list excluded items, reproduce vectors and
obtain the owner's item-by-item review. A family with zero rows stays excluded
until a separately reviewed corpus change supplies it.

The manifest/plan hashes and the §2 query were checked on the frozen inputs.
The exact post-commit two-path proof and `git diff --check` are in the task
handoff. This task changes no product contract, migration, dependency, code,
composition root, style, source corpus or legacy file. Revert its two documents
to roll it back; no feature flag is involved.
