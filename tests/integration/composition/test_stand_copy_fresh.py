"""`PROD-03` (`R-146t`, `AD-03`, `AD-17`; `ADR-0021` section 5, commitment 9) -- `deploy.sh`'s `stand-copy-fresh` guard.

*"A migrating deploy follows a fresh copy receipt."* With the `real_data` marker present (the stand holds real
client data: the first attestation of a full copy writes it) and a migration pending (the checkout's highest
revision differs from `alembic_version`, read before `migrate`), `deploy.sh` refuses unless the copy record is
**open, has its dump, is attested for this commit and was quiesced at most 24 hours ago**. The receipt is the
record `copy-serve.sh dump-db` writes -- there is no second artefact -- and the guard sits on top of the `R-93`
guards (`stand-copy-unattested`, `stand-copy-other-target`), which keep refusing first in the states they know.

**Every refusal is a case, and every case is shown able to fail.** For each way a receipt can be wrong the
script ends `REFUSED: [stand_copy_fresh]` with exit 3 before any `build` and before any `up`; the same
invocation against a copy of the script with the `stand-copy-fresh` block deleted no longer produces that word
and goes on to build. The two conditions the `R-93` guards already refuse (unattested; attested for another
commit) are shown on a copy with **those two guards and not this one** deleted, so this guard is not vacuous
there either. The control cases are the other half: no marker, no pending migration, and a good receipt all
deploy -- a guard that refused everything would pass every refusal case.

**The harness is `test_deploy_script_refusals.py`'s**, loaded from that file rather than copied (the stub
`docker`, the staged clone, the served `401`); the one addition is a branch for ``compose exec ... psql``, which
answers ``alembic_version`` from the environment. Time is real: ``quiesced_at`` is written relative to now.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "deploy_refusals_harness", ROOT / "tests/integration/composition/test_deploy_script_refusals.py"
)
assert _spec is not None and _spec.loader is not None
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

serving = harness.serving  # the fixtures, by the names pytest finds them under
free_port = harness.free_port
REFUSED = harness.REFUSED
DEPLOY = harness.DEPLOY

#: `compose exec -T postgres psql ... alembic_version`: the database's migration state, from the environment.
EXEC_BRANCH = '''    if sub == "exec":
        if "alembic_version" in " ".join(rest):
            sys.stdout.write(setting("STUB_ALEMBIC", ""))
            sys.exit(int(setting("STUB_ALEMBIC_STATUS", "0")))
        sys.exit(0)
'''
ANCHOR = '    if sub == "ps":'


@pytest.fixture(autouse=True)
def _docker_that_answers_the_migration_state(monkeypatch: pytest.MonkeyPatch) -> None:
    assert harness.DOCKER_STUB.count(ANCHOR) == 1, "the harness's docker stub changed shape; move the branch"
    monkeypatch.setattr(harness, "DOCKER_STUB", harness.DOCKER_STUB.replace(ANCHOR, EXEC_BRANCH + ANCHOR, 1))


OLD, HEAD_REVISION = "0001_first", "0002_second"
DUMP_SHA = "d" * 64
OTHER_SHA = "e" * 64
NOW = datetime.now(UTC)


def _ago(**delta: float) -> str:
    return (datetime.now(UTC) - timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(
    head: str | None,
    *,
    state: str = "open",
    purpose: str = "publish",
    target: str | None | bool = True,
    dump: dict | None | bool = True,
    attestation: dict | None | bool = True,
    quiesced_at: str | None | bool = None,
) -> str:
    """A copy record in the layout `copy-serve.sh` writes (one top-level key per line), with a good receipt by
    default. `True` means "the good value", `None` means null."""
    good_dump = {"file": "db.dump", "size_bytes": 1234, "sha256": DUMP_SHA}
    good_attestation = {"dump_sha256": DUMP_SHA, "restore_report_sha256": "c" * 64, "attested_at": _ago(hours=1)}
    fields = {
        "kind": "copy",
        "stamp": "20261026T100000Z",
        "state": state,
        "purpose": purpose,
        "target_sha": head if target is True else target,
        "instance": "an-instance",
        "opened_at": _ago(hours=3),
        "quiesced_at": None if quiesced_at is False else (quiesced_at if quiesced_at is not None else _ago(hours=2)),
        "dump": good_dump if dump is True else dump,
        "attestation": good_attestation if attestation is True else attestation,
        "waiver": None,
        "real_data_marker": True,
        "closed_at": None,
    }
    lines = ['  "record_version": 1'] + [f'  "{key}": {json.dumps(value)}' for key, value in fields.items()]
    return "{\n" + ",\n".join(lines) + "\n}\n"


def _migrations(repo: Path, revisions: tuple[tuple[str, str | None], ...] = ((OLD, None), (HEAD_REVISION, OLD))) -> None:
    for revision, down in revisions:
        harness._write(
            repo / f"db/migrations/versions/{revision}.py",
            f'revision: str = "{revision}"\ndown_revision: str | None = {json.dumps(down) if down else "None"}\n',
        )


def _stand(
    tmp_path: Path,
    port: int,
    *,
    marker: bool = True,
    record=None,  # callable(head) -> str | None
    migrations: bool = True,
    script: Path | None = None,
) -> tuple[Path, Path, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    script_path, env_file = harness._ready(tmp_path, port, script=script)
    repo = script_path.parents[2]
    if migrations:
        _migrations(repo)
    head = harness._commit(repo)
    if marker:
        harness._write(tmp_path / "stand-copy" / "real_data", "stamp=20261026T100000Z\n")
    if record is not None:
        harness._write(tmp_path / "stand-copy" / "record.json", record(head))
    return script_path, env_file, head


def _calls(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _built(log: Path) -> bool:
    return any(line.split()[5:6] in (["build"], ["up"]) for line in _calls(log))


def _mutants(tmp_path: Path, *guards: str) -> Path:
    """A copy of deploy.sh with exactly the named guard blocks deleted."""
    text = DEPLOY.read_text(encoding="utf-8")
    for guard in guards:
        block = re.compile(
            rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n", re.DOTALL | re.MULTILINE
        )
        text, count = block.subn("", text)
        assert count == 1, f"the guard markers for {guard!r} are not a single block"
    tmp_path.mkdir(parents=True, exist_ok=True)
    cut = tmp_path / "mutant.sh"
    cut.write_text(text, encoding="utf-8")
    return cut


def _deploy(script: Path, env_file: Path, tmp_path: Path, **stub: str):
    return harness._run(script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_ALEMBIC": f"{OLD}\n", **stub})


WORD = "deploy.sh: REFUSED: [stand_copy_fresh]"


class TestTheControls:
    """Without these, a guard that refused every deploy on a stand with real data would pass every case below."""

    def test_no_marker_means_nothing_changes_even_with_a_pending_migration_and_no_record(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], marker=False)
        completed, log = _deploy(script, env_file, tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "stand_copy_fresh" not in completed.stderr
        assert not any("alembic_version" in line for line in _calls(log)), "the database was asked about a stand with no marker"

    def test_no_pending_migration_needs_no_receipt_at_all(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0])
        completed, log = _deploy(script, env_file, tmp_path, STUB_ALEMBIC=f"{HEAD_REVISION}\n")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert any("alembic_version" in line for line in _calls(log)), "the database was never asked"

    def test_a_good_receipt_lets_the_migrating_deploy_through_and_says_which(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        script, env_file, head = _stand(tmp_path, serving[0], record=lambda head: _record(head))
        completed, _ = _deploy(script, env_file, tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert f"migrating {OLD} -> {HEAD_REVISION} under the copy 20261026T100000Z" in completed.stdout, completed.stdout

    def test_the_boundary_is_24_hours(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=lambda head: _record(head, quiesced_at=_ago(hours=23, minutes=55)))
        completed, _ = _deploy(script, env_file, tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)


#: Each way a receipt is wrong: (id, record builder, a phrase the refusal must say).
WRONG_RECEIPTS = [
    pytest.param(None, "there is no copy record", id="no-record"),
    pytest.param(lambda head: _record(head, state="closed"), "is not open", id="closed-record"),
    pytest.param(lambda head: _record(head, dump=None), "has no dump", id="no-dump"),
    pytest.param(lambda head: _record(head, dump={"file": "db.dump", "size_bytes": 1}), "has no dump", id="dump-without-digest"),
    pytest.param(lambda head: _record(head, quiesced_at=_ago(hours=24, minutes=5)), "more than 24 hours", id="older-than-24-hours"),
    pytest.param(lambda head: _record(head, quiesced_at=_ago(days=9)), "more than 24 hours", id="nine-days-old"),
    pytest.param(lambda head: _record(head, quiesced_at=(datetime.now(UTC) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")), "in the future", id="from-the-future"),
    pytest.param(lambda head: _record(head, quiesced_at=False), "no quiesced_at", id="never-quiesced"),
    pytest.param(lambda head: _record(head, quiesced_at="yesterday-ish"), "is not a time", id="quiesced-at-not-a-time"),
    pytest.param(lambda head: _record(head, attestation={"dump_sha256": OTHER_SHA, "attested_at": _ago(hours=1)}), "does not bind this dump", id="attests-another-dump"),
]


class TestEveryWayAReceiptCanBeWrong:
    @pytest.mark.parametrize(("record", "says"), WRONG_RECEIPTS)
    def test_it_refuses_before_any_build(self, record, says: str, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=record)
        completed, log = _deploy(script, env_file, tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert WORD in completed.stderr, completed.stderr
        assert says in completed.stderr, completed.stderr
        assert not _built(log), f"the deploy built or brought up before it refused: {_calls(log)}"
        assert "R-146t" in completed.stderr and "24 hours" in completed.stderr, completed.stderr

    @pytest.mark.parametrize(("record", "says"), WRONG_RECEIPTS)
    def test_deleting_the_guard_removes_the_refusal_and_the_deploy_goes_on(
        self, record, says: str, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=record, script=_mutants(tmp_path, "stand-copy-fresh"))
        completed, log = _deploy(script, env_file, tmp_path)
        assert "stand_copy_fresh" not in completed.stderr, completed.stderr
        assert _built(log), "the mutant did not reach the build, so this case was not testing that guard"

    def test_the_message_names_what_the_deploy_would_migrate(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=None)
        completed, _ = _deploy(script, env_file, tmp_path)
        assert f"checkout {HEAD_REVISION}, database {OLD}" in completed.stderr, completed.stderr

    def test_every_problem_is_listed_not_only_the_first(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(
            tmp_path, serving[0], record=lambda head: _record(head, dump=None, quiesced_at=_ago(days=3))
        )
        completed, _ = _deploy(script, env_file, tmp_path)
        assert "has no dump" in completed.stderr and "more than 24 hours" in completed.stderr, completed.stderr


class TestTheGuardSitsOnTopOfTheR93Guards:
    """An open record that is unattested, or attested for another commit, is refused first by the `R-93` guards
    in the words they already have. This guard repeats both conditions, and these cases show it is not vacuous:
    with the two earlier guards (and not this one) deleted, it still refuses."""

    @pytest.mark.parametrize(
        ("record", "earlier", "says"),
        [
            pytest.param(lambda head: _record(head, attestation=None, purpose="none", target=None), "stand_copy_unattested", "is not attested", id="unattested"),
            pytest.param(lambda head: _record(head, target="a" * 40), "stand_copy_other_target", "not this checkout", id="attested-for-another-commit"),
        ],
    )
    def test_the_r93_guard_speaks_first_and_this_one_agrees_without_it(
        self, record, earlier: str, says: str, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        script, env_file, _ = _stand(tmp_path / "first", serving[0], record=record)
        completed, log = _deploy(script, env_file, tmp_path / "first")
        assert f"deploy.sh: REFUSED: [{earlier}]" in completed.stderr, completed.stderr
        assert not log.exists() or not _built(log)

        cut = _mutants(tmp_path / "cut", "stand-copy-unattested", "stand-copy-other-target")
        script, env_file, _ = _stand(tmp_path / "second", serving[0], record=record, script=cut)
        completed, log = _deploy(script, env_file, tmp_path / "second")
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert WORD in completed.stderr and says in completed.stderr, completed.stderr
        assert not _built(log)

        all_three = _mutants(tmp_path / "all", "stand-copy-unattested", "stand-copy-other-target", "stand-copy-fresh")
        script, env_file, _ = _stand(tmp_path / "third", serving[0], record=record, script=all_three)
        completed, log = _deploy(script, env_file, tmp_path / "third")
        assert "stand_copy" not in completed.stderr, completed.stderr
        assert _built(log)


class TestAnUnverifiableReceiptIsNotAVerifiedOne:
    def test_a_database_that_cannot_be_read_is_a_refusal_with_the_way_out(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=lambda head: _record(head))
        completed, log = _deploy(script, env_file, tmp_path, STUB_ALEMBIC="", STUB_ALEMBIC_STATUS="1")
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"{WORD} the real_data marker exists and the database's migration state could not be read" in completed.stderr
        assert "up -d postgres" in completed.stderr, "the refusal must name the way out"
        assert not _built(log)

    def test_an_answer_that_is_not_a_revision_is_not_read_as_one(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=lambda head: _record(head))
        completed, _ = _deploy(script, env_file, tmp_path, STUB_ALEMBIC="ERROR: relation does not exist\n")
        assert completed.returncode == REFUSED and "could not be read" in completed.stderr, completed.stderr

    def test_a_checkout_whose_head_cannot_be_read_is_a_refusal(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(tmp_path, serving[0], record=lambda head: _record(head), migrations=False)
        completed, log = _deploy(script, env_file, tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "migration head could not be read" in completed.stderr
        assert not _built(log)

    def test_unreadable_database_refusals_are_shown_able_to_fail(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file, _ = _stand(
            tmp_path, serving[0], record=lambda head: _record(head), script=_mutants(tmp_path, "stand-copy-fresh")
        )
        completed, log = _deploy(script, env_file, tmp_path, STUB_ALEMBIC="", STUB_ALEMBIC_STATUS="1")
        assert "stand_copy_fresh" not in completed.stderr
        assert _built(log)


class TestWhatCountsAsPending:
    def test_a_database_ahead_of_the_checkout_also_differs_and_needs_the_receipt(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """ADR-0021: "the checkout's highest revision differs from `alembic_version`". Not "is lower than"."""
        script, env_file, _ = _stand(tmp_path, serving[0], record=None)
        completed, _ = _deploy(script, env_file, tmp_path, STUB_ALEMBIC="0099_from_the_future\n")
        assert completed.returncode == REFUSED and WORD in completed.stderr, completed.stderr

    def test_two_branches_in_the_checkout_are_two_heads(self, tmp_path: Path, serving: tuple[int, type]) -> None:
        script, env_file = harness._ready(tmp_path, serving[0])
        repo = script.parents[2]
        _migrations(repo, ((OLD, None), ("0002_left", OLD), ("0002_right", OLD)))
        head = harness._commit(repo)
        harness._write(tmp_path / "stand-copy" / "real_data", "stamp=x\n")
        harness._write(tmp_path / "stand-copy" / "record.json", _record(head))
        # The database holds one of the two heads: the other is pending.
        completed, _ = _deploy(script, env_file, tmp_path, STUB_ALEMBIC="0002_left\n")
        assert "migrating 0002_left -> 0002_left,0002_right" in completed.stdout, (completed.stdout, completed.stderr)

    def test_the_head_is_read_from_the_real_migrations_of_this_tree(self) -> None:
        """The function that reads the head must agree with the tree it ships in: one head, and the one
        `alembic` would name. A parse that found two here would refuse every migrating deploy of the stand."""
        script = DEPLOY.read_text(encoding="utf-8")
        function = re.search(r"^checkout_heads\(\) \{\n.*?^\}\n", script, re.DOTALL | re.MULTILINE)
        assert function is not None
        completed = subprocess.run(
            ["bash", "-c", f'REPO="{ROOT}"\n{function.group(0)}\ncheckout_heads'],
            capture_output=True, text=True, timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
        heads = completed.stdout.split()
        revisions = sorted(
            re.search(r'^revision(?:: str)? = "([^"]+)"', path.read_text(encoding="utf-8"), re.M).group(1)  # type: ignore[union-attr]
            for path in (ROOT / "db/migrations/versions").glob("*.py")
        )
        assert len(heads) == 1 and heads[0] == revisions[-1], (heads, revisions[-3:])
