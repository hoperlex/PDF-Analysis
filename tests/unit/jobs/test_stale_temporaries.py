"""A killed process's temporary PDFs are reclaimed by the next one (`RUN-ROBUSTNESS-01`, D-170).

`W55B-REHEARSAL-01` §4.2.9: each of the three memory kills left a 45 MB ``am-source-*.pdf`` in
the worker's ``/tmp`` -- a stage's temporary file is removed by a context manager, which a
SIGKILL never reaches -- and on the stand that is up to 250 MiB a kill. The sweep removes what
a killed process left; the tests below show that it **does remove those**, and, one case each,
that it **removes nothing else**: nothing young, nothing of another name, nothing that is a
link, nothing whose directory holds something young. No database, no container.

A file's change time cannot be set backwards, so a test makes a file "old" by sweeping with a
clock in the future (``now=``), and "young" by sweeping with the real one.
"""

from __future__ import annotations

import importlib
import inspect
import os
import tempfile
import time
from pathlib import Path

import pytest

from auditmanager.analysis.stages import source_preparation
from auditmanager.ingest import bundle_archive
from auditmanager.jobs import temporaries
from auditmanager.jobs.lease import ATTEMPT_WATCHDOG_SECONDS
from auditmanager.jobs.temporaries import (
    DIRECTORY_NAME,
    FILE_NAME,
    STALE_AFTER_SECONDS,
    sweep_stale_temporaries,
)

source_file = importlib.import_module("auditmanager.analysis.geometry.source_file")

SOURCE = "am-source-a1b2c3d4.pdf"
GEOMETRY = "am-geometry-e5f6g7h8.pdf"
BUNDLE = "auditmanager-bundle-i9j0k1l2"


def long_after() -> float:
    """A clock far enough ahead that everything made now is older than the watchdog."""
    return time.time() + STALE_AFTER_SECONDS + 600


def make_file(directory: Path, name: str, size: int = 1000) -> Path:
    path = directory / name
    path.write_bytes(b"%PDF-1.7\n" + b"x" * size)
    return path


def make_bundle(directory: Path, name: str = BUNDLE) -> Path:
    bundle = directory / name
    bundle.mkdir()
    (bundle / "member.pdf").write_bytes(b"%PDF-1.7\n" + b"y" * 500)
    (bundle / "member_blocks.json").write_bytes(b"{}")
    return bundle


# ---------------------------------------------------------------------------------------
# What a killed process left, and is reclaimed
# ---------------------------------------------------------------------------------------


def test_the_threshold_is_the_attempt_watchdog_and_a_minute() -> None:
    assert ATTEMPT_WATCHDOG_SECONDS == 900
    assert STALE_AFTER_SECONDS == 960.0


def test_a_stale_stage_pdf_and_bundle_directory_are_removed(tmp_path: Path) -> None:
    make_file(tmp_path, SOURCE, 45_000)
    make_file(tmp_path, GEOMETRY, 1_000)
    make_bundle(tmp_path)

    report = sweep_stale_temporaries(directory=tmp_path, now=long_after())

    assert report.removed == tuple(sorted([SOURCE, GEOMETRY, BUNDLE]))
    assert report.failed == ()
    assert report.bytes_freed >= 45_000 + 1_000 + 500
    assert list(tmp_path.iterdir()) == []


def test_the_names_are_the_ones_the_producers_write() -> None:
    """Written by the real functions, not by this file: a producer that renamed its temporary
    would make the sweep a no-op, and this is what would say so."""
    for prefix in ("am-source-", source_file.TEMPORARY_PREFIX):
        descriptor, name = tempfile.mkstemp(prefix=prefix, suffix=".pdf")
        os.close(descriptor)
        try:
            assert FILE_NAME.match(Path(name).name), name
        finally:
            os.unlink(name)
    with tempfile.TemporaryDirectory(prefix="auditmanager-bundle-") as directory:
        assert DIRECTORY_NAME.match(Path(directory).name), directory
    # And the producers still spell the prefixes the sweep matches.
    assert 'prefix="am-source-"' in inspect.getsource(source_preparation)
    assert source_file.TEMPORARY_PREFIX == "am-geometry-"
    assert 'prefix="auditmanager-bundle-"' in inspect.getsource(bundle_archive)


# ---------------------------------------------------------------------------------------
# What it leaves alone
# ---------------------------------------------------------------------------------------


def test_nothing_younger_than_the_watchdog_is_removed(tmp_path: Path) -> None:
    """A live attempt's file is young: it is made after the claim and the watchdog fences the
    attempt 900 s after it."""
    make_file(tmp_path, SOURCE)
    make_bundle(tmp_path)

    now = time.time()
    assert sweep_stale_temporaries(directory=tmp_path, now=now).removed == ()
    assert sweep_stale_temporaries(directory=tmp_path, now=now + STALE_AFTER_SECONDS - 5).removed == ()
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted([SOURCE, BUNDLE])


def test_the_threshold_is_strict_and_a_second_past_it_removes(tmp_path: Path) -> None:
    path = make_file(tmp_path, SOURCE)
    written = max(path.stat().st_mtime, path.stat().st_ctime)
    assert sweep_stale_temporaries(directory=tmp_path, now=written + STALE_AFTER_SECONDS).removed == ()
    assert sweep_stale_temporaries(directory=tmp_path, now=written + STALE_AFTER_SECONDS + 1).removed == (SOURCE,)


def test_a_file_changed_recently_is_young_whatever_its_modification_time(tmp_path: Path) -> None:
    """The change time counts too: a file whose mtime was set an hour back, just now, is young."""
    path = make_file(tmp_path, SOURCE)
    hour_ago = time.time() - 3600
    os.utime(path, (hour_ago, hour_ago))  # sets mtime back; the change time is now
    assert sweep_stale_temporaries(directory=tmp_path).removed == ()
    assert path.exists()


def test_a_bundle_directory_is_as_young_as_its_youngest_member(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    clock = time.time() + STALE_AFTER_SECONDS + 100
    member = bundle / "member.pdf"
    os.utime(member, (clock - 50, clock - 50))  # modified 50 s before `clock`: young then
    assert sweep_stale_temporaries(directory=tmp_path, now=clock).removed == ()
    assert member.exists()
    assert sweep_stale_temporaries(directory=tmp_path, now=clock + STALE_AFTER_SECONDS).removed == (BUNDLE,)


def test_a_young_file_deep_inside_a_bundle_directory_keeps_it(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    nested = bundle / "inner" / "deeper"
    nested.mkdir(parents=True)
    clock = time.time() + STALE_AFTER_SECONDS + 100
    young = nested / "late.bin"
    young.write_bytes(b"z")
    os.utime(young, (clock - 10, clock - 10))
    assert sweep_stale_temporaries(directory=tmp_path, now=clock).removed == ()
    assert young.exists()


@pytest.mark.parametrize(
    "name",
    [
        "am-source-a1b2c3d4.txt",        # not a PDF
        "am-source-a1b2c3.pdf",          # random part too short
        "am-source-a1b2c3d4e5.pdf",      # random part too long
        "am-source-a1b2-3d4.pdf",        # a character mkstemp never writes
        "am-sources-a1b2c3d4.pdf",       # not the prefix
        "xam-source-a1b2c3d4.pdf",       # not at the start
        "am-geometry-a1b2c3d4.pdf.bak",  # something appended
        "am-source-a1b2c3d4.PDF",        # case
        "tmpa1b2c3d4",                   # a multipart spool: never matched
        "notes.pdf",
        "auditmanager-bundle-a1b2c3d4.zip",
    ],
)
def test_a_file_with_any_other_name_is_never_removed(tmp_path: Path, name: str) -> None:
    path = make_file(tmp_path, name)
    assert sweep_stale_temporaries(directory=tmp_path, now=long_after()).removed == ()
    assert path.exists()


def test_a_directory_with_a_file_name_and_a_file_with_a_directory_name_are_left(tmp_path: Path) -> None:
    (tmp_path / SOURCE).mkdir()
    make_file(tmp_path, BUNDLE)
    assert sweep_stale_temporaries(directory=tmp_path, now=long_after()).removed == ()
    assert (tmp_path / SOURCE).is_dir() and (tmp_path / BUNDLE).is_file()


def test_a_link_is_never_followed_and_never_removed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    precious = make_file(outside, "precious.pdf")
    precious_dir = outside / "precious_directory"
    precious_dir.mkdir()
    (precious_dir / "kept").write_text("kept")
    sweep_root = tmp_path / "tmp"
    sweep_root.mkdir()
    os.symlink(precious, sweep_root / SOURCE)
    os.symlink(precious_dir, sweep_root / BUNDLE)

    assert sweep_stale_temporaries(directory=sweep_root, now=long_after()).removed == ()

    assert (sweep_root / SOURCE).is_symlink() and (sweep_root / BUNDLE).is_symlink()
    assert precious.exists() and (precious_dir / "kept").read_text() == "kept"


def test_a_link_inside_a_stale_bundle_directory_is_unlinked_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    precious = make_file(outside, "precious.pdf")
    sweep_root = tmp_path / "tmp"
    sweep_root.mkdir()
    bundle = make_bundle(sweep_root)
    os.symlink(precious, bundle / "link.pdf")

    assert sweep_stale_temporaries(directory=sweep_root, now=long_after()).removed == (BUNDLE,)

    assert precious.exists(), "removing a directory must not remove what a link inside it names"


def test_a_file_of_another_user_is_left(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path, SOURCE)
    monkeypatch.setattr(temporaries.os, "geteuid", lambda: path.stat().st_uid + 1)
    assert sweep_stale_temporaries(directory=tmp_path, now=long_after()).removed == ()
    assert path.exists()


# ---------------------------------------------------------------------------------------
# It never stops a process from starting
# ---------------------------------------------------------------------------------------


def test_a_directory_that_cannot_be_read_is_an_empty_sweep(tmp_path: Path) -> None:
    report = sweep_stale_temporaries(directory=tmp_path / "there_is_no_such_directory")
    assert (report.removed, report.failed, report.bytes_freed) == ((), (), 0)


def test_a_removal_that_fails_is_reported_and_the_others_still_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_file(tmp_path, SOURCE)
    make_file(tmp_path, GEOMETRY)
    real_unlink = os.unlink

    def refuse_one(path: str | os.PathLike[str], *args: object, **kwargs: object) -> None:
        if str(path).endswith(SOURCE):
            raise PermissionError("not yours")
        real_unlink(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(temporaries.os, "unlink", refuse_one)

    report = sweep_stale_temporaries(directory=tmp_path, now=long_after())

    assert report.failed == (SOURCE,)
    assert report.removed == (GEOMETRY,)
    assert (tmp_path / SOURCE).exists() and not (tmp_path / GEOMETRY).exists()


def test_a_file_another_process_removed_first_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_file(tmp_path, SOURCE)

    def vanished(path: str | os.PathLike[str], *args: object, **kwargs: object) -> None:
        raise FileNotFoundError(path)

    monkeypatch.setattr(temporaries.os, "unlink", vanished)
    report = sweep_stale_temporaries(directory=tmp_path, now=long_after())
    assert (report.removed, report.failed) == ((), ())


def test_the_default_directory_is_the_process_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    make_file(tmp_path, SOURCE)
    assert sweep_stale_temporaries(now=long_after()).removed == (SOURCE,)
