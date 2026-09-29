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

Two guards -- `dump-verified` and `rehearsal-counted` -- sit **after** a connection is
attempted, so for those an empty log would be the wrong evidence. Their cases read the log
for what is *not* in it instead: no `DROP SCHEMA`, and for the rehearsal no `pg_dump` either.

This suite needs no running stack, which is the point -- it is the part of `T-5` that a
gate can hold, and the dump/restore cycle against a live stack is driven by hand and
recorded in `docs/program/reviews/W14-PKG.md`.

**What is NOT here, and where it is.** The rehearsal's arithmetic -- `D-24`'s exact counts
and `D-39`'s total -- cannot be settled by a stub that answers every read with silence, and
an assertion about the characters of a SQL statement would pass the moment somebody wrote a
different wrong one. It is driven against a real PostgreSQL in
`test_reset_rehearsal_counts_base_tables.py` beside this file.
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
    cwd: Path | None = None,
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
        cwd=str(cwd) if cwd is not None else None,
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

    def test_a_dump_directory_that_is_not_one_of_ours_is_refused(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """A restore is three files or it is nothing.

        Bytes without their `content-sha256` restore into an instance that lists a document
        and refuses to serve it, which is worse than an empty one because it looks
        recovered. Measured against the running stack before this guard was written.
        """
        staged = tmp_path / "staged"
        staged.mkdir()
        (staged / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
        script = staged / "reset.sh"
        script.write_text(RESET.read_text(encoding="utf-8"), encoding="utf-8")
        half = tmp_path / "half-a-dump"
        half.mkdir()
        (half / "database.dump").write_bytes(b"PGDMP")  # the objects half is absent

        completed, log = _run(
            script,
            ("--database", DATABASE, "--bucket", BUCKET, "--restore", str(half)),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert completed.returncode == REFUSED
        assert "is not one of this script's dumps" in completed.stderr, completed.stderr
        assert not log.exists(), "it refused, but only after running docker"

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, env_file: Path) -> None:
        mutant = _mutant(tmp_path / "mutant", "restore-complete")
        half = tmp_path / "half-a-dump"
        half.mkdir()
        (half / "database.dump").write_bytes(b"PGDMP")
        completed, _ = _run(
            mutant,
            ("--database", DATABASE, "--bucket", BUCKET, "--restore", str(half)),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert "is not one of this script's dumps" not in completed.stderr

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


class TestTheRehearsalRefusesRatherThanShowingNoNumbers:
    """`D-24`, the half of it that is not about arithmetic.

    The rehearsal is the screen an operator reads **before** agreeing to destroy real
    client documents (`R-4`). At `313e753` a `--dry-run` that could not reach the database
    printed ``(could not read the schema; is the stack up?)``, went on to print an exact
    bucket listing and a calm closing sentence, and **exited 0**. Measured on a live stack
    with its postgres container stopped, before this guard existed.

    A table list with no numbers beside it, wrapped in a screen that otherwise looks
    complete, is the same untruth as ``(0 rows)`` in a different costume. So it refuses.

    The plain stub is exactly the instrument for this: it answers `docker` with silence and
    exit 0, which is precisely "the count did not come back". Here, unlike the guards above,
    an empty call log would be the *wrong* evidence -- this guard sits after a connection is
    attempted, so the log must exist and must contain nothing destructive.
    """

    ARGS = ("--database", DATABASE, "--bucket", BUCKET, "--dry-run")

    def test_a_rehearsal_that_cannot_count_is_refused(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        completed, log = _run(_staged(tmp_path), self.ARGS, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "could not count what is in" in completed.stderr, completed.stderr
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        # It tried -- so the refusal is this guard and not an earlier one -- and a rehearsal
        # still touches nothing.
        assert "psql" in calls, "it refused before even trying to read the database"
        assert "DROP SCHEMA" not in calls, calls
        assert "pg_dump" not in calls, calls

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, env_file: Path) -> None:
        """Delete it and the rehearsal prints a table list with no numbers, and exits 0 --
        which is what it did at `313e753` and what this row is about."""
        mutant = _mutant(tmp_path / "mutant", "rehearsal-counted")
        completed, _ = _run(mutant, self.ARGS, tmp_path=tmp_path, env_file=env_file)
        assert "could not count what is in" not in completed.stderr
        assert completed.returncode == 0, (completed.returncode, completed.stderr)

    def test_the_count_is_a_count_and_not_the_statistics_estimate(self) -> None:
        """The arithmetic half, pinned on the one thing a test with no server can read.

        ``pg_stat_user_tables.n_live_tup`` is an asynchronous estimate. Measured on a live
        stack at `313e753`: in one session straight after a committed INSERT it said 4 where
        ``count(*)`` said 5, and with the statistics not yet collected -- a freshly written
        database, or any server after ``pg_stat_reset()`` -- every table printed
        ``(0 rows)`` while five projects, a document, a version, a manifest entry and a blob
        all existed.

        So the rehearsal may not consult that view at all, and must count.
        """
        #: The COMMENTS name the estimate on purpose -- they are what records why it is not
        #: used -- so this reads the executable lines only. A guard that reddened on its own
        #: explanation would teach the next session to delete the explanation.
        code = "\n".join(
            line
            for line in RESET.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        assert "n_live_tup" not in code, (
            "the rehearsal is reading the statistics estimate again (D-24)"
        )
        assert "count(*)" in code, "the rehearsal no longer counts anything"


class TestTheRestorePutsBothHalvesBack:
    """`W22-OPS`, and it was found by running the command this script prints.

    A wipe ends by telling the operator how to put the dump back, and the path it prints is
    relative -- `infra/deploy/dumps/<stamp>` -- as is README.md's. Driven on a live lane,
    that invocation restored the DATABASE and then died, because the object half mounts the
    dump with `docker run -v "$RESTORE:/dump:ro"` and a relative path there is a volume
    NAME to docker, not a directory. What was left was one project, one document and one
    blob in the database and **zero objects in the bucket** -- precisely the instance
    `restore-complete`'s own comment calls worse than an empty one, because it looks
    recovered.

    Two things came out of that, and both are pinned here: the path is made absolute before
    anything is touched, and the BYTES go back before the ROWS, so that a restore which
    fails half way leaves the half that does not mislead anybody.
    """

    def _a_dump(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "database.dump").write_bytes(b"PGDMP")
        (directory / "objects.attrs").write_text(_sidecar(1), encoding="utf-8")
        (directory / "objects").mkdir(exist_ok=True)
        return directory

    def test_a_relative_dump_directory_is_mounted_as_an_absolute_path(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        script = _staged(tmp_path)
        self._a_dump(tmp_path / "dumps" / "an-instance-20260919T000000Z")
        completed, log = _run(
            script,
            ("--database", DATABASE, "--bucket", BUCKET,
             "--restore", "dumps/an-instance-20260919T000000Z"),
            tmp_path=tmp_path,
            env_file=env_file,
            cwd=tmp_path,
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        calls = log.read_text(encoding="utf-8")
        mounts = [
            word
            for line in calls.splitlines()
            for word in line.split()
            if word.endswith(":/dump:ro")
        ]
        assert mounts, f"nothing was mounted at /dump: {calls}"
        for mount in mounts:
            assert mount.startswith("/"), (
                f"docker was handed {mount!r}; a relative path there is a volume name and "
                "is refused, after the database half has already run"
            )

    def test_the_bytes_go_back_before_the_rows(self, tmp_path: Path, env_file: Path) -> None:
        """Either half can fail. Rows without bytes looks recovered and is not; bytes
        without rows looks exactly as empty as it is. So the misleading half goes last."""
        script = _staged(tmp_path)
        dump = self._a_dump(tmp_path / "dump")
        completed, log = _run(
            script,
            ("--database", DATABASE, "--bucket", BUCKET, "--restore", str(dump)),
            tmp_path=tmp_path,
            env_file=env_file,
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        lines = log.read_text(encoding="utf-8").splitlines()
        objects = next(i for i, line in enumerate(lines) if ":/dump:ro" in line)
        rows = next(i for i, line in enumerate(lines) if "pg_restore" in line)
        assert objects < rows, (
            "the database was restored before the objects, so a restore that fails half "
            "way leaves an instance that lists a document and cannot serve it"
        )


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
    assert len(markers) == 13, markers
    covered = {guard for guard, _, _ in CASES} | {
        "env-file-present",
        "instance-configured",
        "compose-file-present",
        "dump-verified",
        "restore-complete",
        # `W22-OPS`, `D-24`: a rehearsal that could not count does not exit 0.
        "rehearsal-counted",
        # `Y8`/`R-52`: a wipe that could not clear the session register refuses before it
        # drops anything, rather than ending the pilot for the data only.
        "sessions-cleared",
    }
    assert set(markers) == covered, set(markers) ^ covered


# --- the sidecar guard (`D-17`) ----------------------------------------------------
#
# `dump-verified` refuses an empty dump, an unreadable one and a short mirror, and the
# cases above reach all three with the plain stub because the run stops at the FIRST of
# them: the stub answers `pg_dump` with nothing, so `database.dump` is empty.
#
# The sidecar check sits after those, and reaching it needs a `docker` that plays the dump
# through rather than one that only records. This stub is still incapable of destroying
# anything -- it opens no connection and runs no container -- but it writes the artefacts
# the guard reads, from content the test chooses. That is what lets a sidecar with a
# missing `blob-role` be put in front of the guard on purpose.

STAGING_STUB = '''#!/usr/bin/env python3
"""A `docker` that records, plays the dump through, and reaches nothing."""
import os, pathlib, sys

argv = sys.argv[1:]
line = " ".join(argv)
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(line + "\\n")


def mount(suffix):
    for index, arg in enumerate(argv):
        if arg == "-v" and index + 1 < len(argv) and argv[index + 1].endswith(suffix):
            return pathlib.Path(argv[index + 1][: -len(suffix)])
    return None


if "object_attrs.py" in line:
    dump = mount(":/dump")
    if dump is not None:
        (dump / "objects.attrs").write_text(os.environ["STUB_ATTRS"], encoding="utf-8")
elif ":/out" in line:
    out = mount(":/out")
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        for n in range(int(os.environ["STUB_OBJECTS"])):
            (out / ("object-%d" % n)).write_bytes(b"bytes")
elif "pg_dump" in line:
    sys.stdout.buffer.write(b"PGDMP-not-a-real-dump")
elif "ls --recursive" in line and "wc -l" in line:
    sys.stdout.write(os.environ["STUB_OBJECTS"] + "\\n")
elif "json stat --recursive" in line:
    # `Y-D`. THIS IS WHAT `mc` REALLY DOES on a bucket with no objects: it writes an error
    # payload to STDOUT -- which `reset.sh` redirects into the sidecar -- and exits 1.
    # Reproduced here rather than described, because the defect was the exit status and a
    # stub that always exited 0 could never have shown it.
    if os.environ["STUB_OBJECTS"] == "0":
        sys.stdout.write(
            '{"status":"error","error":{"message":"Unable to stat `local/b`.",'
            '"cause":{"message":"Object does not exist"}}}\\n'
        )
        sys.exit(1)
elif "auditmanager.access.revoke" in line:
    sys.stdout.write("access-revoke REVOKED login=admin\\n")
    sys.exit(int(os.environ.get("STUB_REVOKE_STATUS", "0")))
elif "auditmanager.access.check" in line:
    status = int(os.environ.get("STUB_CHECK_STATUS", "0"))
    if status == 1:
        sys.stdout.write("access-check DEFAULT CREDENTIAL: login=admin user_uid=usr_x\\n")
    elif status == 0:
        sys.stdout.write("access-check OK no default credentials\\n")
    sys.exit(status)
elif "register.json" in line:
    sys.exit(int(os.environ.get("STUB_SESSIONS_STATUS", "0")))
sys.exit(0)
'''

#: A complete row: key + the four `_metadata_for` keys + Content-Type.
GOOD_ROW = "blobs/aa/bb/{key}\tblob_ID{key}\tsource_document\t{sha}\t5\tapplication/pdf"
SHA = "a" * 64


def _sidecar(rows: int, *, role: str = "source_document") -> str:
    return "".join(
        GOOD_ROW.format(key=f"K{n}", sha=SHA).replace("\tsource_document\t", f"\t{role}\t")
        + "\n"
        for n in range(rows)
    )


def _run_through_the_dump(
    script: Path,
    *,
    tmp_path: Path,
    env_file: Path,
    attrs: str,
    objects: int = 2,
    statuses: dict[str, str] | None = None,
    mode: tuple[str, ...] | None = None,
) -> tuple[subprocess.CompletedProcess[str], str]:
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    log = tmp_path / "docker-calls.log"
    stub = binary / "docker"
    stub.write_text(STAGING_STUB, encoding="utf-8")
    stub.chmod(0o755)
    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["ALPHA_ENV_FILE"] = str(env_file)
    environment["ALPHA_DUMP_ROOT"] = str(tmp_path / "dumps")
    environment["STUB_LOG"] = str(log)
    environment["STUB_ATTRS"] = attrs
    environment["STUB_OBJECTS"] = str(objects)
    environment.update(statuses or {})
    completed = subprocess.run(
        ["bash", str(script), "--database", DATABASE, "--bucket", BUCKET,
         *(mode or ("--yes-destroy-everything",))],
        capture_output=True, text=True, env=environment, timeout=120,
    )
    return completed, (log.read_text(encoding="utf-8") if log.exists() else "")


def _staged(tmp_path: Path) -> Path:
    staged = tmp_path / "staged"
    staged.mkdir(parents=True, exist_ok=True)
    (staged / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
    script = staged / "reset.sh"
    script.write_text(RESET.read_text(encoding="utf-8"), encoding="utf-8")
    return script


class TestTheSidecarCarriesEveryPublishedAttribute:
    """`D-17`. `publish()` writes `blob-id`, `blob-role`, `content-sha256`, `content-size`
    and `Content-Type`. A dump that records some of them restores an object that READS
    correctly and answers `409` to the next upload of its own bytes, because `blob-role` is
    consulted only on the write path. So the guard refuses a row short of any field."""

    def test_a_complete_sidecar_lets_the_wipe_proceed(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """The control. Without it, a guard that refused everything would look correct."""
        completed, calls = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs=_sidecar(2)
        )
        assert "REFUSED" not in completed.stderr, completed.stderr
        assert "DROP SCHEMA" in calls, calls

    @pytest.mark.parametrize(
        ("name", "attrs"),
        (
            # The `D-17` shape exactly: every other attribute present, role empty.
            ("blob-role missing", _sidecar(2, role="")),
            # What this file emitted before wave 18: key, sha, content-type.
            ("the old three-column sidecar", f"blobs/aa/bb/K0\t{SHA}\tapplication/pdf\n" * 2),
            # A row that simply stops early.
            ("a truncated row", f"blobs/aa/bb/K0\tblob_ID\tsource_document\t{SHA}\t5\n" * 2),
            # The empty DIGEST. This guard was written to refuse exactly this and, under
            # GNU grep, never did: `grep -q '^[^\t]*\t\t'` reads `\t` as the letter `t`,
            # so the pattern looked for `tt` and matched no sidecar ever produced. It
            # looked correct on a host whose `grep` is ugrep, which does read `\t`.
            (
                "an empty content-sha256",
                "blobs/aa/bb/K0\tblob_ID\tsource_document\t\t5\tapplication/pdf\n" * 2,
            ),
        ),
        ids=("role", "three-column", "truncated", "empty-digest"),
    )
    def test_an_incomplete_sidecar_stops_the_wipe(
        self, name: str, attrs: str, tmp_path: Path, env_file: Path
    ) -> None:
        completed, calls = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs=attrs
        )
        assert completed.returncode == REFUSED, (name, completed.stdout, completed.stderr)
        assert "missing an attribute" in completed.stderr, completed.stderr
        # It got as far as dumping -- so the refusal is the sidecar check, not an earlier
        # guard -- and no further.
        assert "pg_dump" in calls, "it refused before even trying to dump"
        assert "DROP SCHEMA" not in calls, calls

    def test_that_refusal_is_shown_able_to_fail(self, tmp_path: Path, env_file: Path) -> None:
        """Delete `dump-verified` and the same sidecar is followed by a DROP."""
        mutant = _mutant(tmp_path / "mutant", "dump-verified")
        completed, calls = _run_through_the_dump(
            mutant, tmp_path=tmp_path, env_file=env_file, attrs=_sidecar(2, role="")
        )
        assert "missing an attribute" not in completed.stderr
        assert "DROP SCHEMA" in calls, (
            "the mutant did not reach the drop, so this case was not testing that guard"
        )

    def test_a_short_sidecar_is_still_refused_by_its_own_message(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """Complete rows, one too few of them. The count check and the field check are two
        refusals with two messages, because an operator shown one must not read the other."""
        completed, calls = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs=_sidecar(1),
            objects=2,
        )
        assert completed.returncode == REFUSED, completed.stderr
        assert "sidecar is short" in completed.stderr, completed.stderr
        assert "DROP SCHEMA" not in calls, calls


def test_the_restore_reattaches_every_attribute_the_adapter_publishes() -> None:
    """The dump and the restore are two halves of one format, and they are written in two
    different files. This pins them to each other and to `s3.py`, so that a fifth key added
    to `_metadata_for` reddens here rather than in a wipe.

    `blob-id`, `blob-role`, `content-sha256` and `content-size` are user metadata;
    `media_type` travels as the `Content-Type` header and `publish` compares it too.
    """
    adapter = (ROOT / "src/auditmanager/storage/s3.py").read_text(encoding="utf-8")
    published = set(re.findall(r'^_META_[A-Z0-9_]+: Final\[str\] = "([a-z0-9-]+)"$', adapter, re.M))
    assert published == {"blob-id", "blob-role", "content-sha256", "content-size"}, published

    written = (ROOT / "infra/deploy/object_attrs.py").read_text(encoding="utf-8")
    recorded = re.search(r"^USER_META_KEYS = \(([^)]*)\)", written, re.M)
    assert recorded is not None, "object_attrs.py no longer declares USER_META_KEYS"
    assert set(re.findall(r'"([a-z0-9-]+)"', recorded.group(1))) == published

    script = RESET.read_text(encoding="utf-8")
    attr = re.search(r'mc --quiet cp --attr "([^"]+)"', script)
    assert attr is not None, "reset.sh no longer reattaches attributes on restore"
    reattached = {pair.split("=", 1)[0] for pair in attr.group(1).split(";")}
    assert reattached == published | {"Content-Type"}, reattached


class TestARestoreTakesBackTheCredentialsItPutsBack:
    """`R-52`, ruled 2026-09-29 after `W47-JUDGE-X` found it in cross-examination.

    `pg_dump` here is the whole database with no ``--exclude-table`` and the restore is
    ``pg_restore --clean --if-exists``, so ``app_user`` comes back entire -- ``password_hash``,
    ``token_epoch`` and ``is_default_credential`` with it. Driven end to end by the judge
    against a built API: default -> dump -> forced change -> restore ->
    ``is_default_credential = true``, and the shipped ``admin``/``password`` pair answers 200.

    Two of the three consequences are bounded by ``TOKEN_LIFETIME_SECONDS``; **the third is
    bounded by nothing, because a password is not a token.**

    **It reports; it does not refuse**, and that is the owner's explicit choice taken with
    `D-72` in hand, where a correct fail-closed repair took the stand down for a day. A
    restore that refuses blocks the legitimate one at the moment it is needed most, which is
    after a failure. So the two cases below that put a failure in front of it assert **exit
    0** -- the restore happened -- and assert on the report instead.
    """

    def _a_dump(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "database.dump").write_bytes(b"PGDMP")
        (directory / "objects.attrs").write_text(_sidecar(1), encoding="utf-8")
        (directory / "objects").mkdir(exist_ok=True)
        return directory

    def _restore(
        self, tmp_path: Path, env_file: Path, statuses: dict[str, str] | None = None
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        dump = self._a_dump(tmp_path / "dump")
        return _run_through_the_dump(
            _staged(tmp_path),
            tmp_path=tmp_path,
            env_file=env_file,
            attrs=_sidecar(1),
            statuses=statuses,
            mode=("--restore", str(dump)),
        )

    def test_every_restored_credential_is_dead_by_the_time_the_restore_returns(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """The epoch is raised on **every** row, after the rows are back and not before.

        Before the rows are back there is nothing to raise it on: `pg_restore --clean`
        replaces them. Ordering is therefore the whole of the assertion.
        """
        completed, calls = self._restore(tmp_path, env_file)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        lines = calls.splitlines()
        restored = next(i for i, line in enumerate(lines) if "pg_restore" in line)
        revoked = next(
            i for i, line in enumerate(lines) if "auditmanager.access.revoke" in line
        )
        assert "--everyone" in lines[revoked], lines[revoked]
        assert restored < revoked, (
            "the epoch was raised before the dumped rows were put back, so it raised it on "
            "the rows the restore was about to replace"
        )

    def test_it_runs_inside_the_api_image_and_not_on_the_host(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """`Y-C`. The deploy host is promised bash/docker/curl/sed/git and explicitly **no**
        ``.venv``, so a bare ``PYTHONPATH=src python -m auditmanager.access.revoke`` dies on
        ``ModuleNotFoundError: sqlalchemy``. ``readiness.sh`` already uses the working idiom
        and this uses the same one."""
        _, calls = self._restore(tmp_path, env_file)
        for module in ("auditmanager.access.revoke", "auditmanager.access.check"):
            line = next(one for one in calls.splitlines() if module in one)
            assert "--entrypoint python api" in line, line
            assert "PYTHONPATH" not in line, line

    def test_it_names_by_login_any_account_back_on_its_default_password(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """`access-check` prints one ``DEFAULT CREDENTIAL`` line per account, with the
        login on it, and exits 1. That exit status is the report, not a refusal."""
        completed, calls = self._restore(
            tmp_path, env_file, statuses={"STUB_CHECK_STATUS": "1"}
        )
        assert completed.returncode == 0, (
            "a default credential coming back turned the restore into a failure; R-52 says "
            "it reports and does not refuse"
        )
        assert "auditmanager.access.check" in calls
        assert "DEFAULT CREDENTIAL" in completed.stdout, completed.stdout
        assert "CAME BACK ON ITS SHIPPED DEFAULT PASSWORD" in completed.stdout
        # And it says what to do, which is the other half of the ruling.
        assert "change the password" in completed.stdout, completed.stdout

    def test_a_revocation_that_could_not_run_is_reported_and_does_not_refuse(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """Status 2 is "could not reach the database". The restore has already happened, so
        there is nothing left to refuse; what the operator needs is the command to type."""
        completed, _ = self._restore(
            tmp_path, env_file, statuses={"STUB_REVOKE_STATUS": "2"}
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "THE RESTORED CREDENTIALS WERE NOT REVOKED" in completed.stdout
        assert "auditmanager.access.revoke --everyone" in completed.stdout

    def test_a_dump_with_no_accounts_in_it_is_not_reported_as_a_failure(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """`revoke` exits **1** when it was well-formed and matched nothing. That is a
        successful reading of an empty table, not a fault, and the control that stops the
        two cases above from passing on any non-zero status at all."""
        completed, _ = self._restore(
            tmp_path, env_file, statuses={"STUB_REVOKE_STATUS": "1"}
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "WERE NOT REVOKED" not in completed.stdout, completed.stdout

    def test_a_clean_restore_says_so_and_raises_no_alarm(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """The control. Without it a report that fired on every restore would look right."""
        completed, _ = self._restore(tmp_path, env_file)
        assert completed.returncode == 0
        assert "CAME BACK ON ITS SHIPPED DEFAULT PASSWORD" not in completed.stdout
        assert "restored. Verify with a read" in completed.stdout


class TestTheWipeClearsTheSessionRegister:
    """`Y8`, folded into `R-52` by the owner's choice.

    `R-51` put the web tier's open sessions on a third named volume as ``register.json``,
    mode 0600. Driven by `W47-JUDGE-Y` §6 on a deployed stack: the file was **byte-identical
    across the wipe**, ``md5sum`` unchanged, with three complete 199-character reviewer
    credentials in it. §7 of the runbook promises the documents and the access in one
    landing; without this the wipe ended the pilot for the data only.

    The credentials were inert **only because the account row was gone** -- and ``--restore``
    is the mode that brings that row back, which is why the two findings are one change.
    """

    def test_the_register_is_cleared_and_before_anything_is_destroyed(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        completed, calls = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs=_sidecar(2)
        )
        assert "REFUSED" not in completed.stderr, completed.stderr
        lines = calls.splitlines()
        cleared = next(
            i
            for i, line in enumerate(lines)
            if "register.json" in line and "rm -f" in line
        )
        dropped = next(i for i, line in enumerate(lines) if "DROP SCHEMA" in line)
        assert cleared < dropped, (
            "the schema was dropped before the register was cleared, so a wipe that could "
            "not clear it would already have destroyed the documents"
        )
        # The process's copy goes with the file: `persist()` writes the whole in-memory map
        # out after every change, so a live container can write those credentials straight
        # back on the next sweep.
        stopped = next(i for i, line in enumerate(lines) if "stop web" in line)
        started = next(
            i for i, line in enumerate(lines) if "up -d --no-deps web" in line
        )
        assert stopped < cleared < started, lines[stopped : started + 1]

    def test_a_register_that_cannot_be_cleared_refuses_and_destroys_nothing(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        completed, calls = _run_through_the_dump(
            _staged(tmp_path),
            tmp_path=tmp_path,
            env_file=env_file,
            attrs=_sidecar(2),
            statuses={"STUB_SESSIONS_STATUS": "1"},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "session register could not be cleared" in completed.stderr, completed.stderr
        # It got as far as dumping -- so this is the refusal under test and not an earlier
        # guard -- and no further.
        assert "pg_dump" in calls, "it refused before even trying to dump"
        assert "DROP SCHEMA" not in calls, calls
        assert "rm --recursive --force" not in calls, calls

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, env_file: Path) -> None:
        """Delete the guard block and the same failure is followed by a DROP -- the wipe
        this repair exists to stop, which ends the pilot for the data and leaves the
        credentials on the disk."""
        mutant = _mutant(tmp_path / "mutant", "sessions-cleared")
        completed, calls = _run_through_the_dump(
            mutant,
            tmp_path=tmp_path,
            env_file=env_file,
            attrs=_sidecar(2),
            statuses={"STUB_SESSIONS_STATUS": "1"},
        )
        assert "session register could not be cleared" not in completed.stderr
        assert "DROP SCHEMA" in calls, (
            "the mutant did not reach the drop, so this case was not testing that guard"
        )


class TestAnEmptyBucketIsAStateAndNotAFailure:
    """`Y-D`. Found by `W47-JUDGE-Y` running §7's own sequence on a fresh instance.

    ``mc --json stat --recursive`` exits **1** on a bucket with no objects, writing its error
    payload to stdout -- which ``reset.sh`` redirects into ``objects.stat.json``. Under
    ``set -euo pipefail`` the whole wipe died with **exit 1**, a status ``usage()`` does not
    list and the script issues nowhere else, after a complete 100 KB database dump had
    already been written and with not one word about why. ``--dry-run``, which is what §7
    tells the operator to run first, handled the same bucket correctly and said nothing was
    wrong.

    The stub reproduces ``mc``'s real behaviour rather than describing it: on
    ``STUB_OBJECTS=0`` it writes that payload and exits 1.
    """

    def test_a_wipe_on_an_empty_bucket_runs_to_the_end(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        completed, calls = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs="", objects=0
        )
        assert completed.returncode == 0, (
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
        assert "REFUSED" not in completed.stderr, completed.stderr
        assert "DROP SCHEMA" in calls, calls
        assert "the bucket holds no objects" in completed.stdout, completed.stdout

    def test_the_command_that_exits_one_on_empty_is_not_run_on_an_empty_bucket(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """And **is** run otherwise. Without the second half this would pass just as well
        for a script that had stopped taking object metadata at all."""
        _, empty = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs="", objects=0
        )
        assert "json stat --recursive" not in empty, empty
        _, full = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs=_sidecar(2)
        )
        assert "json stat --recursive" in full, full

    def test_an_empty_sidecar_is_the_right_length_and_not_a_short_one(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """`Y-D` one layer on, uncovered by repairing the first layer. ``grep -c`` PRINTS
        the count and EXITS 1 when it is zero, so ``$(grep -c . … || echo 0)`` captured the
        two-line string ``0\\n0`` -- and ``0\\n0`` is not ``0``, so ``dump-verified`` refused a
        wipe whose dump was exactly right, saying the sidecar was *short* when it was the
        correct length."""
        completed, _ = _run_through_the_dump(
            _staged(tmp_path), tmp_path=tmp_path, env_file=env_file, attrs="", objects=0
        )
        assert "sidecar is short" not in completed.stderr, completed.stderr

    def test_an_absent_sidecar_is_still_refused_on_an_empty_bucket(
        self, tmp_path: Path, env_file: Path
    ) -> None:
        """The control on the line above, and the reason it is not ``|| echo 0``. An absent
        sidecar means ``object_attrs.py`` did not finish and **nothing** is known about the
        objects; a zero there would let that pass on exactly the bucket that produced it."""
        staged = _staged(tmp_path)
        # A docker that plays everything through EXCEPT writing the sidecar.
        binary = tmp_path / "bin"
        binary.mkdir(exist_ok=True)
        log = tmp_path / "docker-calls.log"
        stub = binary / "docker"
        stub.write_text(
            STAGING_STUB.replace('if "object_attrs.py" in line:', 'if False:'),
            encoding="utf-8",
        )
        stub.chmod(0o755)
        environment = dict(os.environ)
        environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
        environment["ALPHA_ENV_FILE"] = str(env_file)
        environment["ALPHA_DUMP_ROOT"] = str(tmp_path / "dumps")
        environment["STUB_LOG"] = str(log)
        environment["STUB_ATTRS"] = ""
        environment["STUB_OBJECTS"] = "0"
        completed = subprocess.run(
            ["bash", str(staged), "--database", DATABASE, "--bucket", BUCKET,
             "--yes-destroy-everything"],
            capture_output=True, text=True, env=environment, timeout=120,
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "sidecar is short" in completed.stderr, completed.stderr
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        assert "DROP SCHEMA" not in calls, calls
