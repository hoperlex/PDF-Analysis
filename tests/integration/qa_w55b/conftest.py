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


@pytest.fixture(scope="session")
def api_control() -> Iterator[object]:
    control = support.ApiControl()
    try:
        yield control
    finally:
        control.stop()
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
