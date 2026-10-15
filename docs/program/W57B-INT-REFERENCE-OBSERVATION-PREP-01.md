# W57B-INT-REFERENCE-OBSERVATION-PREP-01 — result

Pure W57b planning now produces one `NewerEditionCandidate` for each newer
catalogue edition in the resolver report. Evidence spans are checked against
the exact supplied PDF text and converted from page-local to document-global
Unicode code-point offsets. The other four outcomes remain report-only. The
candidate carries the fixed rule ID and matched document identity, with no
proposed severity or side effect.

## Changed files

- `src/auditmanager/norms/references/observation_plan.py`
- `tests/integration/norms/references/test_observation_plan.py`
- `docs/program/tasks/W57B-INT-REFERENCE-OBSERVATION-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-OBSERVATION-PREP-01.md`

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_observation_plan.py tests/integration/norms/references/test_reference_resolution.py` — 29 passed.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/norms/references/observation_plan.py tests/integration/norms/references/test_observation_plan.py` — passed.
- Direct `governance_findings` on the task — `[]`.
- `git diff --check` — passed.
- No complete `make gate` under R-135; no database or corpus promotion was used.

## Contracts and limits

No contract, migration, stage registry, provider lock or runtime route changed.
The future W57b stage must bind the same text-layer pages to extraction and
planning, provide the pinned catalogue and snapshot, and publish each candidate
transactionally with the prescribed rule provenance. This preparation does not
verify legal applicability, promote the corpus or activate normative findings.

## Integration note

Integrate only the four task-owned paths. The task's forbidden hotspots are
untouched; the later W57b stage/publication owner may consume this pure plan
after its own seal and verified-set grant.
