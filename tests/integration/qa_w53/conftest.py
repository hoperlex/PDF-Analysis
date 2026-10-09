"""Use the existing real PostgreSQL/S3 run fixture in this independent QA lane."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
_NAME = "w53_qa_run_harness"
_SPEC = importlib.util.spec_from_file_location(_NAME, _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_HARNESS: ModuleType = importlib.util.module_from_spec(_SPEC)
sys.modules[_NAME] = _HARNESS
_SPEC.loader.exec_module(_HARNESS)

_no_network = _HARNESS._no_network
engine = _HARNESS.engine
blob_store = _HARNESS.blob_store
session = _HARNESS.session


@pytest.fixture(scope="session")
def helpers() -> ModuleType:
    return _HARNESS
