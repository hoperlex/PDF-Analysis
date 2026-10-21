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
are in `docs/program/reviews/W28-GUARD.md`. `W44-JOURNEY` added twelve more for the
sign-in section (`D-92`), the declared viewport (`D-93`) and the refusal drive's own
controls; its figures are in `docs/program/W44-JOURNEY.md`.

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


def step(m, name):
    """A write step by name. Position moved when `classify-version` joined the half (W59), and
    ten of the original mutations then mutated the wrong step while still going red."""
    return next(x for x in m['write']['steps'] if x['name'] == name)


def without_steps(m, predicate):
    m['write']['steps'] = [x for x in m['write']['steps'] if not predicate(x)]

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
   lambda m: step(m, 'start-run')['expects_api'][0].__setitem__('operationId','beginRun'),
   "test_every_api_call_the_journey_declares_is_in_the_contract"),
  ("point create-project at a screen the read walk does not cover",
   lambda m: step(m, 'create-project').__setitem__('at','/nowhere'),
   "test_every_write_step_stands_on_a_screen_the_read_walk_also_covers"),
  ("rename the project-name input's id",
   lambda m: step(m, 'create-project')['actions'][0].__setitem__('selector','#project-name-box'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("relabel the Start run button",
   lambda m: step(m, 'start-run')['actions'][0].__setitem__('text','Run the audit'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("drop the data-run-outcome marker",
   lambda m: step(m, 'start-run')['await_terminal'].__setitem__('outcome_selector','[data-run-verdict]'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("point the fixture at a PDF that is not there",
   lambda m: m['write'].__setitem__('fixture','fixtures/synthetic/ar/no_such.pdf'),
   "test_the_write_half_uploads_a_fixture_that_is_on_disk"),
  ("declare startRun answers 201",
   lambda m: step(m, 'start-run')['expects_api'][0].__setitem__('expect_status',201),
   "test_every_status_the_write_half_declares_is_one_the_contract_publishes"),
  ("remove the bound on the terminal wait",
   lambda m: step(m, 'start-run')['await_terminal'].pop('bound_ms'),
   "test_every_wait_in_the_write_half_carries_a_positive_bound"),
  ("accept `succeeded` as a run terminal",
   lambda m: step(m, 'start-run')['await_terminal'].__setitem__('accept',['succeeded']),
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
   "test_every_refusal_fixture_the_journey_declares_is_on_disk_or_generated"),
  # `W55B-INGEST-01`: two of the six refusal files are generated, and the set is declared three
  # times (the cases, `refusals.generated.files`, the tool's `--list`).
  ("declare a generated file the tool does not write",
   lambda m: m['refusals']['generated']['files'].append('bundle_502_pages.zip'),
   "test_the_generated_set_is_declared_once_and_agrees_everywhere"),
  ("call a committed refusal file generated",
   lambda m: m['refusals']['cases'][1].__setitem__('generated', True),
   "test_every_refusal_fixture_the_journey_declares_is_on_disk_or_generated"),
  ("name a refusal file the bundle rules made stale",
   lambda m: m['refusals']['cases'][5].__setitem__('fixture', 'too_many_pages.pdf'),
   "test_no_refusal_names_a_file_the_bundle_rules_made_stale"),
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
  # D-61, third instance. The check these two drive was rewritten by `W41-BLIND`: its
  # subject moved from a concatenation of the whole of `web/src` to the import closure of
  # the `control_module` the manifest itself names, over authored STRINGS only. Both
  # mutations redden it for the same reason they always should have.
  ("require a sentence no screen renders",
   lambda m: m['refusals']['cases'][2].__setitem__(
       'expects_rendered',['Enter the document password to continue']),
   "test_every_sentence_the_journey_requires_is_authored_by_the_control_it_presses"),
  ("reword the write half's own panel",
   lambda m: step(m, 'create-project').__setitem__('expects_rendered',['Project made']),
   "test_every_sentence_the_journey_requires_is_authored_by_the_control_it_presses"),
  # D-61 itself, as the manifest actually carried it: a sentence that IS in `web/src` and
  # is an identifier rather than a label. The old check passed this.
  ("declare a sentence that is only an identifier in the source",
   lambda m: step(m, 'create-project').__setitem__('expects_rendered',['Run']),
   "test_every_sentence_the_journey_requires_is_authored_by_the_control_it_presses"),
  # The other half: a sentence the screen renders whether or not the step ran. It is
  # checked against RENDERED output, in web/tests/guards/rendered-language.guard.test.ts,
  # so this one is driven there rather than here and is named in the report.
  ("require an envelope sentence its own constraint contradicts",
   lambda m: m['refusals']['cases'][3].__setitem__('constraint','a_constraint_no_envelope_carries'),
   "test_every_envelope_sentence_a_refusal_requires_is_part_of_its_own_constraint"),
  ("surrender a named fault to the generic classification",
   lambda m: m['refusals']['cases'][4].__setitem__('failure_kind','server_error'),
   "test_no_refusal_declares_the_generic_classification_it_exists_to_rule_out"),
  # --- `W44-JOURNEY`. The sign-in (`D-92`), the declared width (`D-93`), and the refusal
  # --- drive's own controls, which `W28-GUARD` left in a file the gate cannot read.
  ("drop the sign-in section",
   lambda m: m.pop('session'),
   "test_the_manifest_has_a_session_half_at_all"),
  ("type the password into the manifest",
   lambda m: m['session']['actions'][1].__setitem__('value','hunter2'),
   "test_no_session_action_carries_a_credential"),
  ("fill a field the environment does not supply",
   lambda m: m['session']['actions'][0].__setitem__('from','totp'),
   "test_no_session_action_carries_a_credential"),
  ("move the sign-in to a screen the read walk does not cover",
   lambda m: m['session'].__setitem__('at','/sign-in'),
   "test_the_session_stands_on_a_screen_the_read_walk_also_covers"),
  ("rename the password input's id",
   lambda m: m['session']['actions'][1].__setitem__('selector','#sign-in-secret'),
   "test_every_control_the_sign_in_presses_still_exists_in_the_application"),
  ("relabel the sign-in button",
   lambda m: m['session']['actions'][2].__setitem__('text','Log in'),
   "test_every_control_the_sign_in_presses_still_exists_in_the_application"),
  ("rename the session cookie",
   lambda m: m['session'].__setitem__('cookie','am_sess'),
   "test_the_session_cookie_and_mount_are_the_ones_the_application_uses"),
  ("remove the bound on the sign-in wait",
   lambda m: m['session'].__setitem__('bound_ms',0),
   "test_the_manifest_has_a_session_half_at_all"),
  ("drop the declared viewport",
   lambda m: m.pop('viewport'),
   "test_the_viewport_declares_a_width_every_route_is_held_to"),
  ("declare a width the wave-43 bar already fitted inside",
   lambda m: m['viewport'].__setitem__('width',1024),
   "test_the_viewport_declares_a_width_every_route_is_held_to"),
  ("relabel the upload control the refusals press",
   lambda m: m['refusals']['controls'].__setitem__('submit_label','Upload'),
   "test_every_control_the_refusals_press_still_exists_in_the_application"),
  ("rename the file input the refusals attach to",
   lambda m: m['refusals']['controls'].__setitem__('file_input','#document-file'),
   "test_every_control_the_refusals_press_still_exists_in_the_application"),
  # --- `BETA-LIVE-JOURNEY-01`. The night window's steps, their accounts and their vocabulary.
  ("drop the accounts roster",
   lambda m: m.pop('accounts'),
   "test_the_accounts_a_refusal_by_role_needs_are_made_through_screens_that_exist"),
  ("make the roster's expert an administrator too",
   lambda m: m['accounts']['roster'][0].__setitem__('roles', ['expert', 'admin']),
   "test_the_accounts_a_refusal_by_role_needs_are_made_through_screens_that_exist"),
  ("rename the registration form's e-mail field",
   lambda m: m['accounts']['register']['fields'].__setitem__('login', '#register-mail'),
   "test_the_accounts_a_refusal_by_role_needs_are_made_through_screens_that_exist"),
  ("run a step as an account the roster does not name",
   lambda m: step(m, 'assign-work').__setitem__('as', 'ghost'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("drop the screen a night step belongs to",
   lambda m: step(m, 'assign-work').pop('screen'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("remove every step that refuses something on the dispatcher",
   lambda m: without_steps(m, lambda x: x.get('screen') == 'dispatcher' and x.get('case') == 'refused'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("remove every step that acts on the price lists",
   lambda m: without_steps(m, lambda x: x.get('screen') == 'price-lists' and x.get('case') == 'action'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("never designate a norms snapshot",
   lambda m: without_steps(m, lambda x: x['name'] == 'norms-designate-the-current-snapshot'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("rename the operation that creates an assignment",
   lambda m: step(m, 'assign-work')['expects_api'][0].__setitem__('operationId', 'makeAssignment'),
   "test_every_api_call_the_journey_declares_is_in_the_contract"),
  ("declare a status createAssignment does not publish",
   lambda m: step(m, 'assign-work')['expects_api'][0].__setitem__('expect_status', 201),
   "test_every_status_the_write_half_declares_is_one_the_contract_publishes"),
  ("rename the creation form's submit marker",
   lambda m: step(m, 'assign-work')['actions'][-1].__setitem__('selector', '[data-create-assign-submit]'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("relabel «Назначить»",
   lambda m: step(m, 'assign-work')['actions'][-1].__setitem__('text', 'Assign'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("relabel the select the expert is chosen in",
   lambda m: step(m, 'assign-work')['actions'][4].__setitem__('label', 'Assignee'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("expect a marker the dispatcher no longer draws",
   lambda m: step(m, 'dispatcher-expert-sees-only-the-own-work')['expects_present'].append(
       {'selector': '[data-dispatcher-queue]'}),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("forbid a control under a renamed marker",
   lambda m: step(m, 'dispatcher-expert-sees-only-the-own-work')['forbids_rendered'].__setitem__(0, '[data-dispatcher-form]'),
   "test_every_control_the_write_half_presses_still_exists_in_the_application"),
  ("name a price-list fixture that is not there",
   lambda m: step(m, 'price-list-upload')['actions'][1].__setitem__('fixture', 'tests/e2e/pc01/journey/fixtures/optimisation/none.csv'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("use an identifier no earlier step captured",
   lambda m: step(m, 'my-tasks-take-the-work')['expects_api'][0].__setitem__('path', '/assignments/{assignment_id}/transitions'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("capture the assignment under another name",
   lambda m: step(m, 'assign-work')['captures'][0].__setitem__('as', ['assignment']),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("name a section the contract does not publish",
   lambda m: step(m, 'section-form7').__setitem__('constants', {'section_code': 'ZZ'}),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("expect an error code the contract does not publish",
   lambda m: step(m, 'price-list-without-columns-refused')['expects_api'][0].__setitem__('expect_error_code', 'teapot'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("declare a call absent that is no operation of the contract",
   lambda m: step(m, 'my-tasks-return-needs-a-reason')['expects_not_called'][0].__setitem__('path', '/assignments/{assignment_uid}/returns'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("press with a click count the instrument does not support",
   lambda m: step(m, 'assign-work')['actions'][-1].__setitem__('times', 7),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("leave a wait with no bound",
   lambda m: step(m, 'assign-work')['actions'][1].pop('bound_ms'),
   "test_the_night_window_steps_agree_with_the_contract_and_with_each_other"),
  ("send a step to a route the read walk does not cover",
   lambda m: step(m, 'norms-catalogue').__setitem__('route', '/catalogue'),
   "test_every_write_step_stands_on_a_screen_the_read_walk_also_covers"),
  ("select an option by the name the run stamped",
   lambda m: step(m, 'assign-work')['actions'][0].__setitem__('option_text', 'W22-E2E write half %STAMP%'),
   "test_every_hand_off_the_night_window_makes_to_the_dispatcher_selects_by_value"),
  ("make a read-walk route's constant an identifier the contract has no enumeration for",
   lambda m: [r.__setitem__('constants', {'section_code': 'ZZ'}) for r in m['routes'] if r['name'] == 'section-optimisation'],
   "test_the_read_walk_s_constants_are_members_of_a_contract_enumeration"),
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
