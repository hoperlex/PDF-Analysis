"""Fixtures for the CSV-export suite.

The export is a read over what a *real run* produced, so this suite drives the same
chain the run suite does and reuses its harness rather than seeding rows by hand: a
CSV asserted against hand-written fixture rows would prove the serializer correct and
say nothing about whether the columns resolve to what the chain actually wrote.

``harness.py`` lives beside ``tests/integration/runs`` and is loaded here **by explicit
path**, the mechanism ``tests/contract/api_v1`` already uses for a helper module. The
root ``pyproject.toml`` says a lane that adds ``sys.path`` juggling to a conftest is
working around the import contract rather than extending it, and
``--import-mode=importlib`` would not resolve a bare import anyway. Both directories
belong to this session.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"

if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    # Registered before execution because ``@dataclass`` resolves annotations through
    # ``sys.modules[cls.__module__]``. This is the module object, not a path entry.
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

_no_network = harness._no_network
engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter
variant_adapter = harness.variant_adapter
seeded = harness.seeded
new_key = harness.new_key


@pytest.fixture(scope="session")
def helpers() -> ModuleType:
    """The harness module itself, for the plain helpers a test wants to call."""
    return harness
