# Task W57A-CORPUS-SOURCE-PREP-01 — inventory candidate norm-source coverage

task_id: W57A-CORPUS-SOURCE-PREP-01

## Outcome

The W57a map owner receives a reproducible, document-level inventory of the local
bootstrap corpus for the five planned normative categories, including the absent
families and the limits of what a manifest proves. It can be checked without W55b
acceptance, a promotion database, model calls or a profile contract change.

## Depends on

- `W56A-LEGACY-SOURCE-01` — completed at `5f742b22c109b8f0b289962750d305495a3449c3`;
  supplies the verified legacy АР file identities and item-line review map.

W56a close is a dependency of the future `W57A-FREEZE-01`, not this read-only
source inventory.

## Frozen inputs

- base commit: `5f742b22c109b8f0b289962750d305495a3449c3`, descended from W55b
  candidate `8c5a109bd98302b64fb47b364d4c639ff63c0eda`.
- domain contract: candidate revision 12; error catalogue SHA-256
  `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`.
- API contract: 47 paths / 54 operations / 123 schemas; OpenAPI SHA-256
  `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`.
- analysis contract: stage registry SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- migration head: `0021_portal_bundles`.
- W57 plan: `docs/program/dispatch/W57-PLAN.md` SHA-256
  `b6a814440bba63d9b0650e7323128f423d4d02d6a27d10a1193bf0cdf09b9ae5`,
  §A1, §A3.1 and §A4; the plan is future work, not a present code grant.
- local read-only bootstrap manifest: `/root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json`
  SHA-256 `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`.
- legacy АР six-file manifest: `docs/program/W56A-LEGACY-SOURCE-01.md` §1; source
  Git commit `32b9d903792b30506048a1d42b0e6b2d07aee403`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the pinned local bootstrap manifest contains 674 source documents,
  but its metadata alone cannot identify a reviewed W57a snapshot or legal status.

### P-01 — local manifest identity and scope

- captured_at: 2026-10-14
- command: `sha256sum /root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json; /root/projects/PDF-Analysis/.venv/bin/python -c 'import json,pathlib; d=json.loads(pathlib.Path("/root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json").read_text()); print(len(d["documents"]), d["summary"]["documents"]))'`
- captured_output:
  ```text
  160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b  /root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json
  674 674
  ```
- interpretation: this is a stable local file for this inventory. It is not a
  promoted `ns_` snapshot, a verified custody binding, or legal-status data.

### P-02 — no document legal-status field in this manifest

- captured_at: 2026-10-14
- command: `/root/projects/PDF-Analysis/.venv/bin/python - <<'PY'
import json
from pathlib import Path
x=json.loads(Path('/root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json').read_text())['documents']
keys=set().union(*(d.keys() for d in x))
print(len(keys), sorted(k for k in keys if any(t in k for t in ('status','edition','valid','effective','supersed','replac'))))
PY`
- captured_output:
  ```text
  38 ['block_status']
  ```
- interpretation: recognition status is present; document legal status and
  edition authority are not established by this manifest.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

This new inventory does not rewrite the historical W57 research or any source file.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-CORPUS-SOURCE-PREP-01.md`
- `docs/program/W57A-CORPUS-SOURCE-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, composition roots, global styles
- `AGENTS.md`, `CURRENT_STATE.md`, `OWNER_RULINGS_*.md`, existing plans and historical reviews
- local corpus files, legacy checkout, W55b refs/worktrees, promotion database, stand and credentials

## Non-goals

- `W57A-MAP-01`, item or clause selection, legal-status verification, paragraph
  resolution, query vectors, owner map review, freeze, contract/DB changes,
  paid calls, deployment or publication.

## Deliverables

- Task file and report with the manifest identity, a category-to-family coverage
  table, exact manifest slug/count evidence, absent and excluded families, and
  the W57a freeze/MAP handoff.

## Required tests

- command: `sha256sum /root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json docs/program/dispatch/W57-PLAN.md`.
- expected: the two frozen-input digests above.
- command: run the report §2 family-matching query against the exact manifest.
- expected: ten named present documents, zero СП 2.13130 / СП 4.13130 /
  СанПиН 1.2.3685, one excluded СП 112.13330.2011.
- command: `git diff --check <base>..HEAD` and `git diff --name-only <base>..HEAD`
  after commit.
- expected: exit 0 and exactly the two allowed paths.

## Integration contract

The W57a freeze owner may use this report to plan map review and corpus gaps,
but must remeasure on the promotion database's reviewed snapshot (`ns_`, content
key, embedding build). `W57A-MAP-01` alone resolves `ndoc_`/`npar_` targets and
obtains owner review. A bootstrap slug is never a production target identity.

## Failure/idempotency/security cases

- A changed manifest digest invalidates this inventory until remeasured.
- An absent family or unverified legal status is labelled as such; there is no
  substitution from another edition or a model-generated clause.
- No norm text, private document, credential or paid response is copied into Git.

## Rollback / feature flag

Revert the document-only commit. No runtime/data rollback or feature flag.

## Handoff

- changed files: see Allowed paths.
- commands/results: report §1–§3.
- known limits: report §4.
- integration notes: report §5.
