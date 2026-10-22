"""`W55B-QA-01` fixtures: one served API child, the lane's database, and accounts.

The helpers live in ``qa_support.py`` beside this file and are loaded **by path** under a
session-unique module name (the mechanism ``tests/conftest.py`` uses for the accounts
helper), because ``--import-mode=importlib`` resolves no bare sibling import. Test modules
say ``from w55b_qa_support import ...``. See ``qa_support.py`` for what the harness does
and why it never signals a process it did not start.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine

_NAME = "w55b_qa_support"
_PATH = Path(__file__).resolve().parent / "qa_support.py"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, _PATH)
    assert _spec is not None and _spec.loader is not None
    _module: ModuleType = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
support: ModuleType = sys.modules[_NAME]


_DIRECTORY = Path(__file__).resolve().parent
_CONTROLS: list[object] = []


def _close_controls() -> None:
    for control in _CONTROLS:
        control.close()  # type: ignore[attr-defined]


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    """Stop the served child when the last test of **this directory** ends (`GATE-REPAIR-02`).

    ``api_control`` is session scoped so the child, which is expensive to start, is shared by
    every module here. A session scope also means it lived to the end of the pytest *session*:
    in the complete battery that is through ``recovery``, ``runs``, ``shared_kernel`` and
    ``workers``, and the child is the in-process claimant of ``EXECUTION_ROLE=all``, so it
    claimed the queued runs of those suites and failed them (``analysis_failed``, "the run's
    pinned analysis profile is not registered in this deployment"; three
    ``workers/test_worker_service.py`` tests in the complete gate on `7cb317b0`). This hook sees
    only the items of this directory; the next one tells where the run goes after it.
    """
    if nextitem is not None and _DIRECTORY in Path(str(nextitem.path)).resolve().parents:
        return
    _close_controls()


@pytest.fixture(scope="session")
def api_control(engine: Engine) -> Iterator[object]:
    control = support.ApiControl()
    _CONTROLS.append(control)
    control.park_foreign_queue(engine)
    try:
        yield control
    finally:
        control.close()
        _CONTROLS.remove(control)
        for ceiling, peak in control.peaks:
            sys.stderr.write(
                f"\nw55b-qa: API child (ceiling {ceiling or 'default'}) VmHWM {peak} KiB\n"
            )
        # The children's logs: a start that failed has already quoted its tail in the failure.
        shutil.rmtree(control.log_directory, ignore_errors=True)


@pytest.fixture
def api(api_control: object) -> object:
    """The served application at the default configuration (no ceiling set: $1.00)."""
    return api_control.ensure(None)  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    created = support.make_engine()
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture(scope="session")
def accounts(engine: Engine) -> object:
    return support.Accounts(engine)


@pytest.fixture(scope="session")
def expert(accounts: object) -> str:
    """One complete ``expert`` account's credential: the uploader and the runner."""
    return accounts.credential("expert")  # type: ignore[attr-defined]
