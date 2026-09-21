"""Prove the conformance guard can fail -- against the REAL manifest, not a synthetic one.

    python tests/e2e/pc01/journey/prove_the_guard_can_fail.py

`W21-E2E` shipped a negative control that was vacuous when written and only running it
found that. The controls inside `tests/e2e/test_pc01_journey_conformance.py` are pure
functions over synthetic data, which makes them fast and copy-able anywhere -- and leaves
one thing unproven: that the checks, wired to the *real* `manifest.json`, the *real*
`web/src` and the *real* contract, actually go red. This does that. It is deliberately not
a pytest file: it rewrites `manifest.json` ten times, and a thing that writes the tree does
not belong inside `make gate`, where another lane may be measuring.

It restores the file after every mutation and again at the end. If it is interrupted,
`git checkout tests/e2e/pc01/journey/manifest.json` puts it back.

Measured 2026-09-19 on `agent/w22-e2e`: ten mutations, ten reds, zero vacuous checks.
`W28-GUARD` added thirteen more for the refusal half and the sentence check; its figures
are in `docs/program/reviews/W28-GUARD.md`.

Sibling: `tests/e2e/prove_the_headroom_guard_can_fail.py` does the same for `D-44`'s
guard, and never writes the tree at all -- the two files it would have to mutate,
`web/src` and `infra/deploy/proxy/nginx.conf`, are somebody else's.
"""

import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
M = ROOT / 'tests' / 'e2e' / 'pc01' / 'journey' / 'manifest.json'
PYTHON = ROOT / '.venv' / 'bin' / 'python'
orig = M.read_text()

def run(test):
    target = 'tests/e2e/test_pc01_journey_conformance.py'
    if test:
        target += '::' + test
    r = subprocess.run(
        [str(PYTHON), '-m', 'pytest', target, '-q', '--no-header', '-x'],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    return r.returncode, (r.stdout or '')

mutations = [
  ("drop the write section",
   lambda m: m.pop('write'),
   "test_the_manifest_has_a_write_half_at_all"),
  ("rename startRun's operationId",
   lambda m: m['write']['steps'][2]['expects_api'][0].__setitem__('operationId','beginRun'),
   "test_every_api_call_the_journey_declares_is_in_the_contract"),
  ("point create-project at a screen the read walk does not cover",
   lambda m: m['write']['steps'][0].__setitem__('at','/nowhere'),
   "test_every_write_step_stands_on_a_screen_the_read_walk_also_covers"),
  ("rename the project-name input's id",
   lambda m: m['write']['steps'][0]['actions'][0].__setitem__('selector','#project-name-box'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("relabel the Start run button",
   lambda m: m['write']['steps'][2]['actions'][0].__setitem__('text','Run the audit'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("drop the data-run-outcome marker",
   lambda m: m['write']['steps'][2]['await_terminal'].__setitem__('outcome_selector','[data-run-verdict]'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("point the fixture at a PDF that is not there",
   lambda m: m['write'].__setitem__('fixture','fixtures/synthetic/ar/no_such.pdf'),
   "test_the_write_half_uploads_a_fixture_that_is_on_disk"),
  ("declare startRun answers 201",
   lambda m: m['write']['steps'][2]['expects_api'][0].__setitem__('expect_status',201),
   "test_every_status_the_write_half_declares_is_one_the_contract_publishes"),
  ("remove the bound on the terminal wait",
   lambda m: m['write']['steps'][2]['await_terminal'].pop('bound_ms'),
   "test_every_wait_in_the_write_half_carries_a_positive_bound"),
  ("accept `succeeded` as a run terminal",
   lambda m: m['write']['steps'][2]['await_terminal'].__setitem__('accept',['succeeded']),
   "test_the_run_states_the_write_half_names_are_the_contract_s_own"),
  # --- the refusal half. `W28-GUARD`, over `W27-REFUSE`'s six measured drives. ---
  ("drop the refusal section",
   lambda m: m.pop('refusals'),
   "test_the_manifest_has_a_refusal_half_at_all"),
  ("declare every refusal happens at the server",
   lambda m: [c.__setitem__('refused_by','server') for c in m['refusals']['cases']],
   "test_the_manifest_has_a_refusal_half_at_all"),
  ("rename uploadDocument",
   lambda m: m['refusals']['api'].__setitem__('operationId','postDocument'),
   "test_every_api_call_the_journey_declares_is_in_the_contract"),
  ("point a refusal at a fixture that is not there",
   lambda m: m['refusals']['cases'][0].__setitem__('fixture','no_such_file.txt'),
   "test_every_refusal_fixture_the_journey_declares_is_on_disk"),
  ("move the refusals to a screen the read walk does not cover",
   lambda m: m['refusals'].__setitem__('at','/nowhere'),
   "test_every_refusal_stands_on_the_upload_screen_the_read_walk_covers"),
  ("call a client-side refusal a server one",
   lambda m: m['refusals']['cases'][0].__setitem__('refused_by','server'),
   "test_every_refusal_declares_the_fields_that_go_with_where_it_was_refused"),
  ("declare a status uploadDocument does not publish",
   lambda m: m['refusals']['cases'][3].__setitem__('expect_status',413),
   "test_every_status_a_refusal_declares_is_one_the_contract_publishes"),
  ("rename the pre-check marker value",
   lambda m: m['refusals']['cases'][2].__setitem__('precheck_problem','over_the_limit'),
   "test_every_marker_a_refusal_names_still_exists_in_the_application"),
  ("drop the upload-failure marker",
   lambda m: m['refusals'].__setitem__('failure_marker','data-upload-verdict'),
   "test_every_marker_a_refusal_names_still_exists_in_the_application"),
  ("require a sentence no screen renders",
   lambda m: m['refusals']['cases'][2].__setitem__(
       'expects_rendered',['Enter the document password to continue']),
   "test_every_sentence_the_journey_requires_still_appears_in_the_application"),
  ("reword the write half's own panel",
   lambda m: m['write']['steps'][0].__setitem__('expects_rendered',['Project made']),
   "test_every_sentence_the_journey_requires_still_appears_in_the_application"),
  ("require an envelope sentence its own constraint contradicts",
   lambda m: m['refusals']['cases'][3].__setitem__('constraint','a_constraint_no_envelope_carries'),
   "test_every_envelope_sentence_a_refusal_requires_is_part_of_its_own_constraint"),
  ("surrender a named fault to the generic classification",
   lambda m: m['refusals']['cases'][4].__setitem__('failure_kind','server_error'),
   "test_no_refusal_declares_the_generic_classification_it_exists_to_rule_out"),
]

ok = True
for label, mutate, test in mutations:
    m = json.loads(orig)
    mutate(m)
    M.write_text(json.dumps(m, indent=2) + "\n")
    code, out = run(test)
    M.write_text(orig)
    verdict = "RED (control works)" if code != 0 else "GREEN -- THE CHECK IS VACUOUS"
    if code == 0: ok = False
    print(f"{verdict:34} {label}  [{test}]")
# and the whole file must be green again
code, out = run("")
print("\nthe file with the manifest restored:", out.strip().splitlines()[-1] if out else code)
if code != 0:
    ok = False
sys.exit(0 if ok else 1)
