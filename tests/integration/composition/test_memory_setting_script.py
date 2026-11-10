"""`D-511` -- every refusal `infra/deploy/memory-setting.sh` makes, and every one shown able to fail.

The convention is `test_erase_project_script.py`'s (`R-4`: a guard on an operator tool that has never been shown to fail is the most expensive kind
of green):

1. an invocation that should trip a guard exits **3**, says why, and -- for the guards that run before any connection -- makes **no `docker`
   call at all**;
2. the same invocation against a **copy of the script with exactly that guard block deleted** no longer produces that refusal (and, where the
   guard sat in front of a step, the copy is shown reaching it);
3. a behaviour that is not a guard (the owner's url, the operator's uid, the five mounts, stdin, the order look-ask-write-look) is pinned by a test
   **and** by a text mutation of the script that turns it red.

Nothing here touches a stand: `docker` is a stub on `PATH` (`tests/support/wrapper_rig.py`). The module behind it -- the settings journal, the
backlog refusal of `D-496`, the lock -- is `tests/integration/recovery/test_memory_setting.py`; the meeting of the two, with the real module
behind a `docker` shim, is `tests/integration/recovery/test_memory_ops_wrappers.py`. This file drives the wrapper's ORDER, ARGUMENTS and EXIT CODES.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from auditmanager.decision_memory.public import SETTING_VALUES
from tests.support.wrapper_rig import ROOT, Rig, Wrapper, env_without, guard_names, modules_imported_by

SCRIPT = ROOT / "infra/deploy/memory-setting.sh"
MODULES = ("memory_setting", "project_erase", "product_purge", "schema_coverage", "blob_reference_audit")

INSTANCE, DATABASE, BUCKET, USER = "an-instance", "the_configured_database", "the-configured-bucket", "the_user"
REFUSED, FAILED, USAGE = 3, 4, 2
ACTOR = "an.administrator@example.org"
REF = "owner mail of 2026-11-09, kept in the release record"

#: The application role's url (`DATABASE_URL`) and the owner's (`MIGRATOR_DATABASE_URL`) are DIFFERENT strings, so a test can tell which one the
#: wrapper hands the one-off container (`PROD-04-DB-ROLES-01`).
APP_URL = f"postgresql+psycopg://the_application_role:an-application-db-password-0001@postgres:5432/{DATABASE}"
MIGRATOR_URL = f"postgresql+psycopg://{USER}:an-owner-db-password-0002@postgres:5432/{DATABASE}"
ENV_TEXT = (f"ALPHA_INSTANCE={INSTANCE}\nPOSTGRES_DB={DATABASE}\nPOSTGRES_USER={USER}\nS3_BUCKET={BUCKET}\n"
            f"DATABASE_URL={APP_URL}\nMIGRATOR_DATABASE_URL={MIGRATOR_URL}\n")
WRAPPER = Wrapper(script=SCRIPT, tool="scripts.recovery.memory_setting", flavour="setting", env_text=ENV_TEXT,
                  module_env="ALPHA_MEMORY_MODULE_DIR")

DB = ("--database", DATABASE)
SET_CLASS = (*DB, "set", "data_class", "real", "--actor", ACTOR)
SET_TRAINING = (*DB, "set", "training_use", "on", "--actor", ACTOR, "--owner-permission-ref", REF)
TYPED_REAL = "real\n"


SHOW_MEMBERS = ("data_class", "data_class_revision", "data_class_default", "training_use", "training_use_revision", "training_use_default",
                "uncaptured_decisions")


def screen(*, data_class: str = "test", training: str = "off", backlog: int = 0, data_class_revision: int | None = None,
           training_revision: int | None = None) -> str:
    """What `memory_setting show --json` prints (`scripts/recovery/memory_setting.py`, `SHOW_JSON_KEYS`): ONE line. A revision of 0 is
    "nothing journalled yet", which is what a value equal to its default means unless a revision is given."""
    def revision(value: str, default: str, given: int | None) -> int:
        return given if given is not None else (0 if value == default else 1)
    members = {"data_class": data_class, "data_class_revision": revision(data_class, "test", data_class_revision),
               "data_class_default": "test", "training_use": training,
               "training_use_revision": revision(training, "off", training_revision), "training_use_default": "off",
               "uncaptured_decisions": backlog}
    assert tuple(members) == SHOW_MEMBERS
    return json.dumps(members) + "\n"


WRITTEN = "memory-setting: data_class: test -> real (revision 1).\n  Cases already captured keep the class they were captured with.\n"


def healthy() -> dict[str, object]:
    return {"show": [{"stdout": screen()}, {"stdout": screen(data_class="real")}], "set": {"stdout": WRITTEN}}


@pytest.fixture()
def rig(tmp_path: Path) -> Rig:
    built = Rig(tmp_path, WRAPPER)
    built.answers = healthy()
    return built


# --- the guards that run before any connection ------------------------------------------------

#: (guard, arguments, the refusal's words, whether the copy without the guard goes on to the docker stub)
CASES: tuple[tuple[str, tuple[str, ...], str, bool], ...] = (
    ("known-options", (*DB, "show", "--bogus"), "unrecognised option: --bogus", False),
    ("known-options", ("show", "--database"), "--database needs a value", False),
    ("known-options", (*DB, "set", "data_class", "real", "--actor"), "--actor needs a value", False),
    ("command-shape", (*DB,), "the command is show or set", True),
    ("command-shape", (*DB, "forget"), "the command is show or set", True),
    ("command-shape", (*DB, "show", "extra"), "show takes no further word", True),
    ("command-shape", (*DB, "set", "data_class", "--actor", ACTOR), "set takes a setting and a value", False),
    ("command-shape", (*DB, "set", "data_class", "real", "now", "--actor", ACTOR), "set takes a setting and a value", True),
    ("setting-and-value", (*DB, "set", "data_class", "production", "--actor", ACTOR), "data_class admits test and real", True),
    ("setting-and-value", (*DB, "set", "retention", "on", "--actor", ACTOR), "data_class admits test and real", True),
    ("setting-and-value", (*DB, "set", "training_use", "real", "--actor", ACTOR), "data_class admits test and real", True),
    ("setting-and-value", (*DB, "set", "data_class", "on", "--actor", ACTOR), "data_class admits test and real", True),
    ("options-match-the-command", (*DB, "show", "--actor", ACTOR), "belong to set, and the command is show", True),
    ("options-match-the-command", (*DB, "show", "--owner-permission-ref", REF), "belong to set, and the command is show", True),
    ("options-match-the-command", (*DB, "show", "--owner-permission-ref", ""), "belong to set, and the command is show", False),
    ("names-required", ("show",), "--database is required", False),
    ("actor-required", (*DB, "set", "data_class", "real"), "--actor must be the login", True),
    ("actor-required", (*DB, "set", "data_class", "real", "--actor", ""), "--actor must be the login", True),
    ("actor-required", (*DB, "set", "data_class", "real", "--actor", "two words"), "--actor must be the login", True),
    ("actor-required", (*DB, "set", "data_class", "real", "--actor", "-x"), "--actor must be the login", True),
    ("actor-required", (*DB, "set", "data_class", "real", "--actor", "x" * 255), "--actor must be the login", True),
    ("permission-ref-shape", (*SET_CLASS, "--owner-permission-ref", "   "), "--owner-permission-ref must be one line", True),
    ("permission-ref-shape", (*SET_CLASS, "--owner-permission-ref", "x" * 201), "--owner-permission-ref must be one line", True),
    ("permission-ref-shape", (*SET_CLASS, "--owner-permission-ref", "line one\nline two"), "--owner-permission-ref must be one line", True),
    # `F4`: argparse of the module reads a value that begins with "-" (and has no space) as an option, so the wrapper refuses it first
    ("permission-ref-shape", (*SET_CLASS, "--owner-permission-ref", "-ticket42"), "--owner-permission-ref must not begin with '-'", True),
    ("permission-ref-shape", (*SET_CLASS, "--owner-permission-ref", "  - see mail"), "--owner-permission-ref must not begin with '-'", True),
    ("permission-ref-shape", (*SET_CLASS, "--owner-permission-ref", "-"), "--owner-permission-ref must not begin with '-'", True),
    ("training-needs-permission", (*DB, "set", "training_use", "on", "--actor", ACTOR), "--owner-permission-ref is required", True),
    ("database-matches", ("--database", "some_other_database", "show"), "not the configured alpha database", True),
)


@pytest.mark.parametrize(("guard", "args", "says", "reaches"), CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_it_refuses_says_why_and_never_calls_docker(guard: str, args: tuple[str, ...], says: str, reaches: bool, rig: Rig) -> None:
    completed = rig.run(*args)
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert says in completed.stderr, completed.stderr
    assert not rig.log.exists(), f"{guard} refused, but only after running docker: {rig.calls}"


@pytest.mark.parametrize(("guard", "args", "says", "reaches"), CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_deleting_the_guard_removes_the_refusal(guard: str, args: tuple[str, ...], says: str, reaches: bool, rig: Rig) -> None:
    broken = rig.mutant(guard)
    completed = broken.run(*args)
    assert says not in completed.stderr, (
        f"the {guard} guard was deleted and the refusal happened anyway: it was never testing that guard")
    if reaches:
        assert broken.log.exists(), f"with {guard} gone the script should have gone on to the stack: {completed.stderr}"


def test_a_missing_environment_file_is_refused_and_the_guard_can_fail(rig: Rig, tmp_path: Path) -> None:
    args = (*DB, "show", "--env-file", str(tmp_path / "not-there.env"))
    completed = rig.run(*args)
    assert completed.returncode == REFUSED and "missing or unreadable" in completed.stderr and not rig.log.exists()
    assert "missing or unreadable" not in rig.mutant("env-file-present").run(*args).stderr


def test_a_half_configured_instance_is_refused_and_the_guard_can_fail(rig: Rig) -> None:
    rig.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    completed = rig.run(*DB, "show")
    assert completed.returncode == REFUSED and "names no ALPHA_INSTANCE" in completed.stderr and not rig.log.exists()
    broken = rig.mutant("instance-configured")
    broken.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    assert "names no ALPHA_INSTANCE" not in broken.run(*DB, "show").stderr


@pytest.mark.parametrize("line", [
    "", "MIGRATOR_DATABASE_URL=\n", "MIGRATOR_DATABASE_URL=postgresql://u:p@postgres:5432/d\n", "MIGRATOR_DATABASE_URL=not a url\n",
], ids=["absent", "empty", "wrong-scheme", "not-a-url"])
def test_a_missing_or_malformed_owner_url_is_refused_and_the_guard_can_fail(rig: Rig, line: str) -> None:
    """`PROD-04`: the journal is written by the OWNER, so the one-off container is handed the owner's url; an environment that has none is refused
    before any connection, in a sentence, and not by the tool after one."""
    rig.env_file.write_text(env_without(ENV_TEXT, "MIGRATOR_DATABASE_URL") + line, encoding="utf-8")
    completed = rig.run(*DB, "show")
    assert completed.returncode == REFUSED and "[migrator_url_unset]" in completed.stderr, completed.stderr
    assert not rig.log.exists(), "the refusal came after docker was touched"
    cut = rig.mutant("migrator-url-configured")
    cut.env_file.write_text(env_without(ENV_TEXT, "MIGRATOR_DATABASE_URL") + line, encoding="utf-8")
    assert "[migrator_url_unset]" not in cut.run(*DB, "show").stderr


def test_a_missing_compose_file_is_refused_and_the_guard_can_fail(tmp_path: Path) -> None:
    bare = Rig(tmp_path / "a", WRAPPER, compose=False)
    completed = bare.run(*DB, "show")
    assert completed.returncode == REFUSED and "compose.server.yml is missing" in completed.stderr and not bare.log.exists()
    broken = Rig(tmp_path / "b", WRAPPER).mutant("compose-file-present")
    (broken.deploy / "compose.server.yml").unlink()
    assert "compose.server.yml is missing" not in broken.run(*DB, "show").stderr


@pytest.mark.parametrize("absent", MODULES)
def test_a_checkout_without_one_of_the_five_modules_is_refused_and_the_guard_can_fail(absent: str, tmp_path: Path) -> None:
    partial = tmp_path / "partial"
    partial.mkdir()
    for module in MODULES:
        if module != absent:
            (partial / f"{module}.py").write_text("", encoding="utf-8")
    bare = Rig(tmp_path / "rig", WRAPPER, module_dir=partial)
    completed = bare.run(*DB, "show")
    assert completed.returncode == REFUSED and f"lacks {absent}.py" in completed.stderr, completed.stderr
    assert not bare.log.exists()
    assert f"lacks {absent}.py" not in bare.mutant("modules-present").run(*DB, "show").stderr


def test_help_is_a_usage_error_with_its_own_status(rig: Rig) -> None:
    completed = rig.run("--help")
    assert completed.returncode == USAGE and "usage: memory-setting.sh" in completed.stderr
    assert "no override" in completed.stderr
    assert not rig.log.exists()


# --- show -------------------------------------------------------------------------------------


def test_show_is_one_read_only_call_that_asks_nothing(rig: Rig) -> None:
    completed = rig.run(*DB, "show")
    assert completed.returncode == 0, completed.stderr
    assert len(rig.calls) == 1
    assert rig.tool_args(rig.tool_calls()[0]) == ["--database", DATABASE, "show", "--json"]
    assert completed.stdout.splitlines()[2:] == [
        "data_class: test (default; default test)", "training_use: off (default; default off)",
        "uncaptured-decisions: 0 (ledger accept/reject events with no memory decision; a data_class change is refused until this is 0)"]
    assert f"database   {DATABASE}" in completed.stdout and "retype" not in completed.stdout


@pytest.mark.parametrize(("status", "words", "code"), (
    (3, "the show was refused (reason above)", REFUSED), (4, "the show failed (status 4)", FAILED),
), ids=["refused", "failed"])
def test_a_show_that_did_not_complete_is_a_stop_with_the_tools_words_and_its_own_status(status: int, words: str, code: int, rig: Rig) -> None:
    rig.answers["show"] = {"stdout": "", "stderr": "memory_setting: REFUSED: the database is at migration X\n", "status": status}
    completed = rig.run(*DB, "show")
    assert completed.returncode == code and words in completed.stderr
    assert "the database is at migration X" in completed.stderr, "the tool's own words reach the operator"


# --- set: look, ask, write, look again ----------------------------------------------------------


def test_a_set_looks_first_asks_for_the_value_writes_and_looks_again(rig: Rig) -> None:
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    first, second, third = rig.tool_calls()
    assert rig.tool_args(first) == ["--database", DATABASE, "show", "--json"]
    assert rig.tool_args(second) == ["--database", DATABASE, "set", "data_class", "real", "--actor", ACTOR]
    assert rig.tool_args(third) == ["--database", DATABASE, "show", "--json"]
    assert len(rig.calls) == 3, rig.calls
    out = completed.stdout
    assert out.index("in force now") < out.index("retype the new value of data_class") < out.index("changing data_class to real")
    assert "THIS CHANGES data_class FROM test TO real" in out and "uncaptured-decisions above is not 0" in out
    assert "data_class: real (revision 1; default test)" in out.split("changing data_class to real", 1)[1]
    assert "done. data_class is now real" in out and "release record" in out


def test_training_use_on_carries_the_permission_to_the_tool_and_says_what_it_releases(rig: Rig) -> None:
    rig.answers["show"] = [{"stdout": screen()}, {"stdout": screen(training="on")}]
    completed = rig.run(*SET_TRAINING, typed="on\n")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert rig.tool_args(rig.tool_calls()[1]) == [
        "--database", DATABASE, "set", "training_use", "on", "--actor", ACTOR, "--owner-permission-ref", REF]
    assert "client-derived content off this host" in completed.stdout and f"owner's permission: {REF}" in completed.stdout


def test_a_permission_given_for_data_class_is_forwarded_and_one_that_was_not_is_not(rig: Rig) -> None:
    rig.run(*SET_CLASS, "--owner-permission-ref", REF, typed=TYPED_REAL)
    assert rig.tool_args(rig.tool_calls()[1])[-2:] == ["--owner-permission-ref", REF]
    plain = Rig(rig.tmp / "plain", WRAPPER)
    plain.answers = healthy()
    plain.run(*SET_CLASS, typed=TYPED_REAL)
    assert "--owner-permission-ref" not in plain.tool_args(plain.tool_calls()[1])


def test_a_value_already_in_force_is_nothing_to_do_and_asks_nothing(rig: Rig) -> None:
    rig.answers["show"] = {"stdout": screen(data_class="real")}
    completed = rig.run(*SET_CLASS)
    assert completed.returncode == 0, completed.stderr
    assert "data_class is already real; nothing to do. Nothing was changed." in completed.stdout
    assert len(rig.calls) == 1 and "retype" not in completed.stdout


@pytest.mark.parametrize("typed", ("", "\n", "test\n", "REAL\n", "real \n", " real\n", "yes\n"),
                         ids=["nothing", "blank", "the-old-value", "upper-case", "trailing-space", "leading-space", "yes"])
def test_what_is_retyped_must_be_the_new_value_and_the_guard_can_fail(typed: str, rig: Rig) -> None:
    completed = rig.run(*SET_CLASS, typed=typed)
    assert completed.returncode == REFUSED and "what was retyped is not the new value of data_class" in completed.stderr, completed.stderr
    assert len(rig.tool_calls()) == 1, "only the look before; nothing was written"
    broken = rig.mutant("retyped-confirmation")
    completed = broken.run(*SET_CLASS, typed=typed)
    assert "what was retyped is not the new value" not in completed.stderr
    assert any("set" in broken.tool_args(call) for call in broken.tool_calls()), "with the guard gone the change runs on an answer nobody gave"


def test_the_answer_comes_from_the_keyboard_not_from_the_command_line(rig: Rig) -> None:
    completed = rig.run(*SET_CLASS, "--yes")
    assert completed.returncode == REFUSED and "unrecognised option: --yes" in completed.stderr
    completed = rig.run(*SET_CLASS)  # no input at all: an end of input is no answer
    assert completed.returncode == REFUSED and "retyped" in completed.stderr
    assert not any("set" in rig.tool_args(call) for call in rig.tool_calls())


GOOD = json.loads(screen())
NOT_THE_LINE = {
    "some-other-screen": "some other screen\n",
    "the-text-screen-of-before": ("data_class: test (default; default test)\ntraining_use: off (default; default off)\n"
                                  "uncaptured-decisions: 0 (ledger accept/reject events with no memory decision)\n"),
    "two-lines": screen() + screen(),
    "empty": "",
    "no-uncaptured-count": json.dumps({k: v for k, v in GOOD.items() if k != "uncaptured_decisions"}) + "\n",
    "no-data-class": json.dumps({k: v for k, v in GOOD.items() if k != "data_class"}) + "\n",
    "a-revision-that-is-a-word": json.dumps({**GOOD, "data_class_revision": "one"}) + "\n",
    "a-negative-count": json.dumps({**GOOD, "uncaptured_decisions": -1}) + "\n",
    "a-value-in-capitals": json.dumps({**GOOD, "data_class": "REAL"}) + "\n",
}


@pytest.mark.parametrize("printed", NOT_THE_LINE.values(), ids=NOT_THE_LINE.keys())
def test_a_look_that_is_not_the_one_line_the_script_reads_stops_before_anything_is_asked(printed: str, rig: Rig) -> None:
    """`D-517`: the wrapper decides from the members of the module's `show --json` and from nothing else; a look it cannot read is a failure,
    not a guess, and it is one before the operator is asked to retype anything."""
    rig.answers["show"] = {"stdout": printed}
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == FAILED and "did not print the settings in the form this script reads" in completed.stderr, completed.stderr
    assert "Nothing was changed" in completed.stderr
    assert len(rig.tool_calls()) == 1 and "retype" not in completed.stdout
    shown = rig.run(*DB, "show")
    assert shown.returncode == FAILED and "did not print the settings in the form this script reads" in shown.stderr


def test_a_read_back_that_is_not_the_line_is_a_failure_that_says_the_change_may_have_been_made(rig: Rig) -> None:
    rig.answers["show"] = [{"stdout": screen()}, {"stdout": NOT_THE_LINE["the-text-screen-of-before"]}]
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == FAILED and "the show after the change did not print the settings" in completed.stderr
    assert "The change may have been made" in completed.stderr and "Nothing was changed" not in completed.stderr
    assert "done. data_class is now real" not in completed.stdout


def test_the_screen_is_printed_from_the_members_that_were_read_and_each_member_is_read(rig: Rig) -> None:
    """Every member of the line reaches the screen: a revision, a default, a backlog and both values, each different from its neighbours, so a
    parse that swapped two members would print the wrong word."""
    rig.answers["show"] = {"stdout": json.dumps({
        "data_class": "real", "data_class_revision": 7, "data_class_default": "test",
        "training_use": "on", "training_use_revision": 3, "training_use_default": "off", "uncaptured_decisions": 12345}) + "\n"}
    completed = rig.run(*DB, "show")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines()[2:] == [
        "data_class: real (revision 7; default test)", "training_use: on (revision 3; default off)",
        "uncaptured-decisions: 12345 (ledger accept/reject events with no memory decision; a data_class change is refused until this is 0)"]


def declared_members(script_text: str) -> tuple[str, ...]:
    """The `SHOW_MEMBERS=(...)` array of the wrapper's source."""
    return tuple(re.search(r"^SHOW_MEMBERS=\(([^)]*)\)", script_text, re.MULTILINE).group(1).split())  # type: ignore[union-attr]


def test_the_members_the_wrapper_reads_are_the_ones_the_module_prints_and_the_check_can_fail() -> None:
    """`D-517`: the module's `SHOW_JSON_KEYS` and the wrapper's `SHOW_MEMBERS` are one list, and this test's own `screen()` prints it too."""
    from scripts.recovery import memory_setting

    text = SCRIPT.read_text(encoding="utf-8")
    declared = declared_members(text)
    assert declared == memory_setting.SHOW_JSON_KEYS == SHOW_MEMBERS == tuple(GOOD)
    # The comparison can fail: the wrapper that lost its last member, or reads two in the other order, declares a list that is not the module's.
    lost = text.replace(" uncaptured_decisions)", ")")
    swapped = text.replace("(data_class data_class_revision ", "(data_class_revision data_class ")
    for broken in (lost, swapped):
        assert broken != text, "the mutation did not apply: the line of the script has changed"
        assert declared_members(broken) != memory_setting.SHOW_JSON_KEYS, "the comparison cannot tell a changed list from the module's"


# --- the tool's own refusals and failures ------------------------------------------------------

BACKLOG = ("memory_setting: REFUSED: 2 accept/reject decision(s) of the ledger are not captured by the decision memory yet. "
           "Let the worker's sweep finish, then run this again. There is no override. Nothing was changed.\n")


def test_the_backlog_refusal_of_the_tool_reaches_the_operator_unchanged_with_exit_3(rig: Rig) -> None:
    """`D-496`: the wrapper keeps the tool's refusal and adds none of its own after the connection: no override, no second opinion."""
    rig.answers["show"] = {"stdout": screen(backlog=2)}
    rig.answers["set"] = {"stderr": BACKLOG, "status": 3}
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert "2 accept/reject decision(s) of the ledger are not captured" in completed.stderr and "There is no override" in completed.stderr
    assert "the change was refused (reason above)" in completed.stderr and "Nothing was changed" in completed.stderr
    assert len(rig.tool_calls()) == 2, "no read-back after a refusal"
    assert "uncaptured-decisions: 2" in completed.stdout, "the count was on the screen before the answer was asked for"


def test_a_failed_write_exits_4_and_sends_the_operator_to_show(rig: Rig) -> None:
    rig.answers["set"] = {"stderr": "memory_setting: FAILED: OperationalError: connection reset\n", "status": FAILED}
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == FAILED and "the change failed (status 4)" in completed.stderr
    assert "one transaction" in completed.stderr and "show" in completed.stderr
    assert "Nothing was changed" not in completed.stderr, "after a failed write the script cannot promise that"
    assert len(rig.tool_calls()) == 2


def test_a_value_that_does_not_read_back_is_a_failure_and_the_guard_can_fail(rig: Rig) -> None:
    rig.answers["show"] = [{"stdout": screen()}, {"stdout": screen()}]  # the write was reported, the setting did not move
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == FAILED and "THE CHANGE WAS REPORTED DONE" in completed.stderr, (completed.stdout, completed.stderr)
    assert "done. data_class is now real" not in completed.stdout
    broken = rig.mutant("readback-verified")
    completed = broken.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == 0 and "done. data_class is now real" in completed.stdout, (
        "with the guard gone the operator is told to record a change that never reads back")


def test_a_read_back_that_cannot_be_made_is_a_failure_that_says_the_change_may_have_been(rig: Rig) -> None:
    rig.answers["show"] = [{"stdout": screen()}, {"stderr": "boom\n", "status": FAILED}]
    completed = rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == FAILED and "the show after the change failed" in completed.stderr
    assert "settings in force say whether it was made" in completed.stderr


# --- what the container is given -----------------------------------------------------------------


def test_the_five_modules_are_mounted_read_only_and_nothing_else_of_the_checkout(rig: Rig) -> None:
    rig.run(*SET_CLASS, typed=TYPED_REAL)
    module_dir = rig.module_dir
    for call in rig.tool_calls():
        argv = [str(item) for item in call["argv"]]
        mounts = sorted(argv[i + 1] for i, item in enumerate(argv) if item == "-v")
        assert mounts == sorted(f"{module_dir}/{m}.py:/purge/scripts/recovery/{m}.py:ro" for m in MODULES), mounts
        assert "PYTHONPATH=/app/src:/purge" in argv
        at = argv.index("--entrypoint")
        assert argv[at + 1:at + 5] == ["python", "api", "-m", "scripts.recovery.memory_setting"]
        assert {"run", "--rm", "--no-deps", "-T"} <= set(argv)
        assert argv[argv.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}"


def test_the_mounted_list_is_the_modules_own_import_closure_and_the_check_can_fail() -> None:
    """The api image does not carry `scripts/recovery`, so a module that gains an import without the list gaining a file fails in the container
    and nowhere else. The closure is read from the sources, transitively."""
    closure = modules_imported_by("memory_setting")
    declared = set(re.search(r"^MODULES=\(([^)]*)\)", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE).group(1).split())  # type: ignore[union-attr]
    assert declared == closure == set(MODULES)
    assert declared - {"blob_reference_audit"} != closure, "the comparison cannot tell a list that lacks a module from the closure"


def test_the_python_half_is_handed_the_owners_url_at_every_step_and_never_the_applications(rig: Rig) -> None:
    ambient = "postgresql+psycopg://ambient:ambient@elsewhere:5432/ambient"
    env = {"DATABASE_URL": ambient, "PGHOST": "elsewhere", "PGPASSWORD": "ambient-secret", "PGSERVICE": "x"}
    assert rig.run(*SET_CLASS, env=env, typed=TYPED_REAL).returncode == 0
    assert [r["database_url"] for r in rig.tool_calls()] == [MIGRATOR_URL] * 3
    assert APP_URL not in "".join(str(r["database_url"]) for r in rig.records)
    for record in rig.tool_calls():
        argv = [str(item) for item in record["argv"]]
        assert not any(item.startswith("PG") or "=PG" in item for item in argv), argv
        assert not any("postgresql+psycopg://" in item or "an-owner-db-password-0002" in item or "ambient-secret" in item for item in argv), argv


def test_the_owner_url_assertion_can_fail_without_the_environment_prefix(rig: Rig) -> None:
    ambient = "postgresql+psycopg://ambient:ambient@elsewhere:5432/ambient"
    broken = rig.edited('DATABASE_URL="$MIGRATOR_URL" compose run', "compose run")
    assert broken.run(*DB, "show", env={"DATABASE_URL": ambient}).returncode == 0
    assert {r["database_url"] for r in broken.tool_calls()} == {ambient}


# --- the lock timeout the operator sets (`D-515`) ---------------------------------------------------


def lock_timeout_items(call: dict[str, object]) -> list[str]:
    argv = [str(item) for item in call["argv"]]  # type: ignore[attr-defined]
    return [item for item in argv if item.startswith("MEMORY_") and "_LOCK_TIMEOUT" in item]


def test_the_lock_timeout_the_operator_sets_is_handed_to_every_container_run_and_the_other_wrappers_is_not(rig: Rig) -> None:
    completed = rig.run(*SET_CLASS, env={"MEMORY_SETTING_LOCK_TIMEOUT": "45s", "MEMORY_FORGET_LOCK_TIMEOUT": "99s"}, typed=TYPED_REAL)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert len(rig.tool_calls()) == 3
    for call in rig.tool_calls():
        argv = [str(item) for item in call["argv"]]
        assert lock_timeout_items(call) == ["MEMORY_SETTING_LOCK_TIMEOUT=45s"], argv
        assert argv[argv.index("MEMORY_SETTING_LOCK_TIMEOUT=45s") - 1] == "-e", "a variable of the one-off container is an -e of `compose run`"
        # an option of `compose run` after the service name would be the tool's argument
        assert argv.index("MEMORY_SETTING_LOCK_TIMEOUT=45s") < argv.index("--entrypoint")


def test_no_lock_timeout_is_passed_when_the_operator_set_none_and_the_default_stays_the_modules(rig: Rig) -> None:
    completed = rig.run(*SET_CLASS, env={"MEMORY_FORGET_LOCK_TIMEOUT": "99s"}, typed=TYPED_REAL)  # the other wrapper's variable is not ours
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert all(lock_timeout_items(call) == [] for call in rig.tool_calls()), [lock_timeout_items(c) for c in rig.tool_calls()]


def test_the_pass_through_of_the_lock_timeout_can_fail(rig: Rig) -> None:
    broken = rig.edited('"${LOCK_TIMEOUT_ENV[@]+"${LOCK_TIMEOUT_ENV[@]}"}" ', "")
    completed = broken.run(*SET_CLASS, env={"MEMORY_SETTING_LOCK_TIMEOUT": "45s"}, typed=TYPED_REAL)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert all(lock_timeout_items(call) == [] for call in broken.tool_calls()), (
        "with the pass-through removed the value still reached the container: the test above would prove nothing")


@pytest.mark.parametrize("value", ("15", "0s", "0ms", "-5s", "1 s", "1.5s", "15S", "1h", "1234567s", "15s; DROP TABLE x", "s", "", " 15s",
                                   "35792min", "36000min", "999999min"),  # `F3`: PostgreSQL's lock_timeout ends at 2147483647 ms, 35791 min
                         ids=lambda v: repr(v))
def test_a_lock_timeout_that_is_not_a_positive_duration_is_refused_before_any_connection_and_the_guard_can_fail(value: str, rig: Rig) -> None:
    completed = rig.run(*DB, "show", env={"MEMORY_SETTING_LOCK_TIMEOUT": value})
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert "MEMORY_SETTING_LOCK_TIMEOUT must be a positive number of ms, s or min" in completed.stderr, completed.stderr
    assert not rig.log.exists(), f"refused, but only after running docker: {rig.calls}"
    broken = rig.mutant("lock-timeout-shape")
    completed = broken.run(*DB, "show", env={"MEMORY_SETTING_LOCK_TIMEOUT": value})
    assert "must be a positive number" not in completed.stderr
    assert broken.log.exists() and any("MEMORY_SETTING_LOCK_TIMEOUT=" + value in item for call in broken.tool_calls() for item in call["argv"]), (
        "with the guard gone the bad value goes into the container as it is: this is why the guard exists")


@pytest.mark.parametrize("value", ("1ms", "250ms", "15s", "30s", "2min", "999999ms", "999999s", "35791min"), ids=lambda v: repr(v))
def test_a_lock_timeout_that_is_a_positive_duration_goes_through(value: str, rig: Rig) -> None:
    completed = rig.run(*SET_CLASS, env={"MEMORY_SETTING_LOCK_TIMEOUT": value}, typed=TYPED_REAL)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert all(lock_timeout_items(call) == ["MEMORY_SETTING_LOCK_TIMEOUT=" + value] for call in rig.tool_calls())


def test_docker_never_reads_the_answer_the_operator_types(rig: Rig) -> None:
    """`docker compose run` forwards stdin to the container, so a pipe feeding the retype would be eaten by the first look: the stub reads
    whatever stdin it is given, and must be given none."""
    assert rig.run(*SET_CLASS, typed=TYPED_REAL).returncode == 0
    assert [r["stdin_bytes"] for r in rig.records] == [0, 0, 0]
    broken = rig.edited('--entrypoint python api -m scripts.recovery.memory_setting --database "$DATABASE" "$@" </dev/null',
                        '--entrypoint python api -m scripts.recovery.memory_setting --database "$DATABASE" "$@"')
    completed = broken.run(*SET_CLASS, typed=TYPED_REAL)
    assert completed.returncode == REFUSED and "what was retyped is not the new value" in completed.stderr
    assert not any("set" in broken.tool_args(call) for call in broken.tool_calls())


def test_it_runs_the_module_and_nothing_else_and_stops_no_service(rig: Rig) -> None:
    rig.run(*SET_CLASS, typed=TYPED_REAL)
    assert all(call["argv"].count("run") == 1 and "scripts.recovery.memory_setting" in call["argv"] for call in rig.records)
    for record in rig.records:
        assert not {"stop", "up", "exec", "ps"} & set(record["argv"]), record["argv"]
        assert not any("pg_dump" in item or "pg_restore" in item or "mirror" in item for item in record["argv"]), record["argv"]


def test_the_option_order_does_not_matter(rig: Rig) -> None:
    shuffled = ("--actor", ACTOR, "set", "data_class", "real", "--database", DATABASE)
    assert rig.run(*shuffled, typed=TYPED_REAL).returncode == 0 and len(rig.tool_calls()) == 3


# --- the lists the wrapper copies from the module ---------------------------------------------


def test_the_closed_lists_are_the_modules_and_the_check_can_fail() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    listed = re.search(r'case "\$NAME:\$VALUE" in\n\s+([^)]+)\) ;;', text)
    assert listed is not None
    pairs = set(listed.group(1).split("|"))
    assert pairs == {f"{name}:{value}" for name, values in SETTING_VALUES.items() for value in values}
    assert pairs - {"training_use:on"} != {f"{name}:{value}" for name, values in SETTING_VALUES.items() for value in values}


# --- what this script is ----------------------------------------------------------------------


def test_the_script_is_executable_and_in_the_deploy_directory() -> None:
    assert SCRIPT.exists() and os.access(SCRIPT, os.X_OK)
    assert SCRIPT.parent == ROOT / "infra/deploy"


def test_the_copy_key_file_list_does_not_gain_this_script() -> None:
    """Runbook section 13 lists the five files the copy key installs. A settings change is an interactive act of an administrator and must not be
    reachable from an unattended key."""
    runbook = (ROOT / "docs/program/DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
    listing = re.search(r"for f in (copy-serve\.sh [^;]+); do", runbook)
    assert listing is not None and "memory-setting.sh" not in listing.group(1)
    assert "memory-setting" not in (ROOT / "infra/deploy/copy-serve.sh").read_text(encoding="utf-8")


def test_every_guard_in_the_script_has_a_case_here() -> None:
    markers = guard_names(SCRIPT)
    me = Path(__file__).read_text(encoding="utf-8")
    missing = sorted(name for name in markers if f'"{name}"' not in me)
    assert not missing, f"guards with no case: {missing}"
    assert len(markers) == 17, sorted(markers)
    text = SCRIPT.read_text(encoding="utf-8")
    for name in markers:
        assert len(re.findall(rf"^ *# <<< guard: {re.escape(name)}$", text, re.MULTILINE)) == 1
