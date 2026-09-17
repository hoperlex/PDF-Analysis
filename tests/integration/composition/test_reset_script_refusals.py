"""`T-5` -- every refusal `infra/deploy/reset.sh` makes, and every one shown able to fail.

`R-4`: the owner ruled on 2026-09-17 that **real client documents may be uploaded and must
be wiped at the end of the pilot.** So this script exists to destroy real data, and a guard
on it that has never been shown to fail is the most expensive kind of green this programme
has a name for -- `ALPHA_ROADMAP.md` section 3 `T-5` calls it "the rule this programme has
paid for four times".

**The shape of each case, and why it is this shape.** For every guard:

1. an invocation that should trip it exits 3, names the reason, and -- for the guards that
   run before any connection is opened -- makes **no `docker` call at all**. That last part
   is what distinguishes "refused" from "refused after starting";
2. the same invocation against a **mutant copy with exactly that guard block deleted** no
   longer produces that refusal. That is the "shown able to fail" half, and it is done by
   deleting the guard rather than by asserting a message, because a message can be produced
   by a guard that happens to be unreachable.

**Nothing here can destroy anything**, and not by hoping. `docker` is replaced on `PATH`
with a stub that records its arguments and exits 0, so even a mutant that runs to the end
reaches no database and no bucket. The stub is also the instrument: an empty log is the
evidence that a refusal happened first.

This suite needs no running stack, which is the point -- it is the part of `T-5` that a
gate can hold, and the dump/restore cycle against a live stack is driven by hand and
recorded in `docs/program/reviews/W14-PKG.md`.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RESET = ROOT / "infra/deploy/reset.sh"

#: Literals. The configured instance the cases are written against, spelled out rather than
#: read from `infra/deploy/env/alpha.env.example` -- `OPERATING_CONSTRAINTS.md` section 12.
INSTANCE = "an-instance"
DATABASE = "the_configured_database"
BUCKET = "the-configured-bucket"
USER = "the_configured_user"

#: `refuse()`'s exit status. One code for every refusal; the *reason* is asserted on the
#: message, because two guards sharing an exit code must still be told apart.
REFUSED = 3

ENV_FILE = f"""\
ALPHA_INSTANCE={INSTANCE}
POSTGRES_DB={DATABASE}
POSTGRES_USER={USER}
S3_BUCKET={BUCKET}
"""

#: One case per guard: the marker name, the arguments, and the words the refusal must say.
#: ``needs_compose`` marks the cases that run from a directory with a compose file beside
#: the script, because the guard under test sits after `compose-file-present`.
CASES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "known-options",
        ("--database", DATABASE, "--bucket", BUCKET, "--dry-run", "--dryrun"),
        "unrecognised option: --dryrun",
    ),
    (
        "destructive-flag",
        ("--database", DATABASE, "--bucket", BUCKET),
        "no --yes-destroy-everything and no --dry-run",
    ),
    (
        "one-mode",
        ("--database", DATABASE, "--bucket", BUCKET, "--dry-run", "--yes-destroy-everything"),
        "were both given",
    ),
    (
        "names-required",
        ("--dry-run",),
        "--database and --bucket are both required",
    ),
    (
        "database-matches",
        ("--database", "some_other_database", "--bucket", BUCKET, "--dry-run"),
        "not the configured alpha database",
    ),
    (
        "bucket-matches",
        ("--database", DATABASE, "--bucket", "some-other-bucket", "--dry-run"),
        "not the configured alpha bucket",
    ),
)


def _stub_path(tmp_path: Path) -> tuple[Path, Path]:
    """A `docker` on PATH that records and does nothing. Returns (bin dir, log file)."""
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    log = tmp_path / "docker-calls.log"
    stub = binary / "docker"
    stub.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> " + str(log) + "\nexit 0\n", encoding="utf-8"
    )
    stub.chmod(0o755)
    return binary, log


def _run(
    script: Path,
    args: tuple[str, ...],
    *,
    tmp_path: Path,
    env_file: Path,
    dump_root: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    binary, log = _stub_path(tmp_path)
    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["ALPHA_ENV_FILE"] = str(env_file)
    environment["ALPHA_DUMP_ROOT"] = str(dump_root or (tmp_path / "dumps"))
    completed = subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    return completed, log


def _mutant(directory: Path, guard: str, *, with_compose: bool = True) -> Path:
    """A copy of reset.sh with exactly one guard block deleted."""
    source = RESET.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n",
        re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", source)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    assert mutated != source
    directory.mkdir(parents=True, exist_ok=True)
    if with_compose:
        # Only its presence is checked, and `docker` is a stub, so its contents never run.
        (directory / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
    target = directory / "reset.sh"
    target.write_text(mutated, encoding="utf-8")
    return target


@pytest.fixture()
def env_file(tmp_path: Path) -> Path:
    path = tmp_path / "alpha.env"
    path.write_text(ENV_FILE, encoding="utf-8")
    return path


class TestEveryRefusalRefuses:
    @pytest.mark.parametrize(("guard", "args", "says"), CASES, ids=[c[0] for c in CASES])
    def test_it_refuses_and_says_why(
        self, guard: str, args: tuple[str, ...], says: str, tmp_path: Path, env_file: Path
    ) -> None:
        completed, log = _run(RESET, args, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert says in completed.stderr, completed.stderr
        assert not log.exists(), (
            f"{guard} refused, but only after running docker: {log.read_text()}"
        )


class TestEveryRefusalIsShownAbleToFail:
    """Delete the guard, and the refusal is gone. Nothing else in the file changes."""

    @pytest.mark.parametrize(("guard", "args", "says"), CASES, ids=[c[0] for c in CASES])
    def test_deleting_the_guard_removes_the_refusal(
        self, guard: str, args: tuple[str, ...], says: str, tmp_path: Path, env_file: Path
    ) -> None:
        mutant = _mutant(tmp_path / "mutant", guard)
        completed, _ = _run(mutant, args, tmp_path=tmp_path, env_file=env_file)
        assert says not in completed.stderr, (
            f"the {guard} guard was deleted and the refusal happened anyway, so this case "
            "was never testing that guard"
        )


class TestTheTwoGuardsThatNeedTheirOwnStaging:
    """Two guards cannot be reached with the arguments above, so they get their own case."""

    def test_a_missing_environment_file_is_refused(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        missing = tmp_path / "not-there.env"
        completed, log = _run(
            RESET,
            ("--database", DATABASE, "--bucket", BUCKET, "--dry-run", "--env-file", str(missing)),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert completed.returncode == REFUSED
        assert "missing or unreadable" in completed.stderr, completed.stderr
        assert not log.exists()

    def test_a_missing_environment_file_guard_is_shown_able_to_fail(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        mutant = _mutant(tmp_path / "mutant", "env-file-present")
        missing = tmp_path / "not-there.env"
        completed, _ = _run(
            mutant,
            ("--database", DATABASE, "--bucket", BUCKET, "--dry-run", "--env-file", str(missing)),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert "missing or unreadable" not in completed.stderr

    def test_a_half_configured_instance_is_refused(self, tmp_path: Path) -> None:
        """An environment naming a database but no instance is not the alpha instance."""
        half = tmp_path / "half.env"
        half.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
        completed, log = _run(
            RESET,
            ("--database", DATABASE, "--bucket", BUCKET, "--dry-run"),
            tmp_path=tmp_path,
            env_file=half,
        )
        assert completed.returncode == REFUSED
        assert "names no ALPHA_INSTANCE" in completed.stderr, completed.stderr
        assert not log.exists()

    def test_a_half_configured_instance_guard_is_shown_able_to_fail(
        self, tmp_path: Path
    ) -> None:
        half = tmp_path / "half.env"
        half.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
        mutant = _mutant(tmp_path / "mutant", "instance-configured")
        completed, _ = _run(
            mutant,
            ("--database", DATABASE, "--bucket", BUCKET, "--dry-run"),
            tmp_path=tmp_path,
            env_file=half,
        )
        assert "names no ALPHA_INSTANCE" not in completed.stderr

    def test_a_missing_compose_file_is_refused(self, tmp_path: Path, env_file: Path) -> None:
        """Every destructive step runs through the compose file; without it there is no
        target this script is allowed to reach."""
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        copy = elsewhere / "reset.sh"
        copy.write_text(RESET.read_text(encoding="utf-8"), encoding="utf-8")
        completed, log = _run(
            copy,
            ("--database", DATABASE, "--bucket", BUCKET, "--dry-run"),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert completed.returncode == REFUSED
        assert "compose.server.yml is missing" in completed.stderr, completed.stderr
        assert not log.exists()

    def test_a_missing_compose_file_guard_is_shown_able_to_fail(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        mutant = _mutant(tmp_path / "mutant", "compose-file-present", with_compose=False)
        completed, _ = _run(
            mutant,
            ("--database", DATABASE, "--bucket", BUCKET, "--dry-run"),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert "compose.server.yml is missing" not in completed.stderr


class TestItDumpsBeforeItDrops:
    """The order `T-5` asks for, asserted on the one thing a stub can prove: an unusable
    dump stops the run, and it stops it before any `DROP`."""

    def _destroy(self, script: Path, tmp_path: Path, env_file: Path):
        return _run(
            script,
            ("--database", DATABASE, "--bucket", BUCKET, "--yes-destroy-everything"),
            tmp_path=tmp_path,
            env_file=env_file,
        )

    def test_an_unreadable_dump_stops_the_wipe(self, tmp_path: Path, env_file: Path) -> None:
        staged = tmp_path / "staged"
        staged.mkdir(parents=True, exist_ok=True)
        (staged / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
        script = staged / "reset.sh"
        script.write_text(RESET.read_text(encoding="utf-8"), encoding="utf-8")

        completed, log = self._destroy(script, tmp_path, env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "is empty" in completed.stderr, completed.stderr
        # The stub answered every `docker` call, so the only reason nothing was dropped is
        # the guard. Prove it: no DROP SCHEMA was ever attempted.
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        assert "pg_dump" in calls, "it refused before even trying to dump"
        assert "DROP SCHEMA" not in calls, calls

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, env_file: Path) -> None:
        """Delete it and the same empty dump is followed by a DROP. This is the case the
        whole script is arranged to prevent."""
        mutant = _mutant(tmp_path / "mutant", "dump-verified")
        completed, log = self._destroy(mutant, tmp_path, env_file)
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        assert "is empty" not in completed.stderr
        assert "DROP SCHEMA" in calls, (
            "the mutant did not reach the drop, so the guard was not what stopped it"
        )


def test_every_guard_in_the_script_has_a_case_here() -> None:
    """A guard added without a test is caught here rather than in a wipe.

    The count is a literal for the same reason every other figure in this file is.
    """
    markers = re.findall(r"^# >>> guard: ([a-z-]+)$", RESET.read_text(encoding="utf-8"), re.M)
    assert len(markers) == len(set(markers)), markers
    assert len(markers) == 10, markers
    covered = {guard for guard, _, _ in CASES} | {
        "env-file-present",
        "instance-configured",
        "compose-file-present",
        "dump-verified",
    }
    assert set(markers) == covered, set(markers) ^ covered
