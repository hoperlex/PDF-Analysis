# W56A-INT-PROMPT-MATERIAL-PREP-01 — deterministic AR v2 request material

`prompt_material.py` joins only the six digest-verified source prompt blocks
into a system string. Its fixed instructions require text-only, same-object
comparisons, verbatim PDF quotations, an empty result when nothing is
grounded, and a model-proposed severity that is not an expert decision.
The user string JSON-quotes each PDF page and appends the already selected
OCR context under its explicit «не цитировать» marker. An OCR page absent
from the PDF text layer is refused.

The material fingerprint binds the reviewed source corpus, sealed response
schema, fixed instructions and representative page/OCR rendering. Its
current SHA-256 is
`01bee01f8c7f1c59227ff6c17398f1034f5094c9c3b8e26fc66ab5130a4ca610`.
It is an input for a later immutable prompt/profile identity, not that
identity itself. Generation parameters, run-row binding, budget accounting
and live provider selection remain with `W56A-PROFILES-01` and PROVIDER.

Checks: 38 focused AR v2 material/OCR/parser/schema/content tests passed;
the module compiled; direct task governance returned no findings;
`git diff --check` and exact allowed-path proof passed. The tests also
confirm that v1's profile hash is unchanged. Pytest emitted only unrelated
old `/tmp` cleanup warnings. No full local gate, paid call, service-backed
acceptance or `origin/main` publication was run.

Changed paths: new `analysis/profiles/ar_v2/prompt_material.py`, one focused
test, this task/report and the top development status in `CURRENT_STATE.md`.
No shared contract, migration, provider lock, existing runtime module,
dependency, composition root, style, recording, stand file, `VERSION` or
release ref changed. Rollback is a revert before profile wiring; after
wiring a changed hash needs a new prompt/profile revision and recordings.

MODEL-PIN remains blocked because the available stand route selects a
stub and the separate recording route is unidentified. This material is
offline preparation, not a beta or model-quality verdict.
