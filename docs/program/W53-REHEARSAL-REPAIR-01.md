# W53-REHEARSAL-REPAIR-01 — S3-source rollback correction

Assigned branch `agent/w53-rehearsal-repair-01`, exact base
`b110b804a381602630d9ad0a207335591732493a`. This addendum corrects
the unrun full procedure in `W53-REHEARSAL-01.md`; it does not change that
report's historical observations.

## 1. Changed files

- `scripts/rehearsal/w53/minio_upgrade.py`: page through all upgraded S3
  object versions, read each version's bytes and metadata, export in oldest to
  newest order per key, and restore that export to the fresh old-image volume.
  Compare the export with the new-image read, then compare restored logical
  history and metadata with the original baseline. New S3 VersionIds are
  expected on restore.
- `docs/program/W53-REHEARSAL-REPAIR-01.md`: this addendum and handback.

## 2. Checks and observations

`/root/projects/PDF-Analysis/.venv/bin/python -m py_compile
scripts/rehearsal/w53/minio_upgrade.py`: PASS. `git diff --check`: PASS.

The pure regression command was
`PYTHONPATH=scripts/rehearsal/w53 /root/projects/PDF-Analysis/.venv/bin/python
/tmp/w53-rehearsal-repair-01/fake_source.py`. The script SHA-256 is
`0285e2308a9109b60feafc0f30a43538228837d47c65f0c02e42a6140431d2d0`;
the log `/tmp/w53-rehearsal-repair-01/fake-source.log` SHA-256 is
`47f0f2a9c0787a3cecbef51c3222cb21782f3fd00f5ea91dfaaeb30923579e24`.
It returned two PASS lines. A paginated fake new-image S3 source returned
`alpha.txt` v1 and v2 plus an empty object. The v2 source held
`changed by upgraded source` and metadata `stage=upgraded`, deliberately
different from the original in-memory fixture. The fake old-image target
received those exact bytes and metadata in v1 then v2 order. A second target
that substituted the original fixture bytes for v2 failed `manifest()` as
expected. This directly exercises the export and restore dataflow, not a
claim of actual image compatibility.

No Docker container or image build was launched for this repair. The new
pinned image is unavailable and `W53-REHEARSAL-01` records that its remaining
build peak plus disk margin has no credible bound. `--full` and `--old-only`
were not rerun; no live or working-stand result is inferred.

Frozen SHA-256 readback: `contracts/api/v1/openapi.json` is
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
`contracts/domain/v1/state-machines.json` is
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.

## 3. Contracts

No API, domain, migration, image pin, release or product behavior contract
changed. The rehearsal procedure now requires the restored bytes to come
from the upgraded server's S3 API, including every listed version and its
metadata. A truncated listing without a next key marker, a repeated marker,
or a delete marker fails the procedure.

## 4. Risks and limits

The real new-image read, S3 restore and old-image rollback remain unproved
under `D-119`/`D-123`. The export holds object bodies in memory; this
disposable four-version fixture is bounded, while a larger recovery rehearsal
would need a streaming export design. No W53 database or working-stand backup
grant exists; it belongs to a separate beta wave.

## 5. Integrator instructions

Cherry-pick the clean repair HEAD after the exact-path audit. Keep the
MinIO upgrade and rollback stop condition open. On a later private slot with
the exact image and an AGENTS.md §8 disk preflight showing a credible peak
and margin, run `minio_upgrade.py --full` and retain its complete log. Do not
use this fake-source result as runtime acceptance.

## 6. Allowed paths and forbidden hotspots

The base-to-HEAD diff is exactly the script and this addendum, both listed
in `tasks/W53-REHEARSAL-REPAIR-01.md` allowed paths. The historical report,
`contracts/**`, migration, root dependency/lock, composition root, global
styles, image pin, backup/deploy paths and working stand are untouched.
No ref or tag is published.
