"""Fixtures for the run-executor suite. The definitions live in ``harness.py`` beside this file.

They are in a separate module because ``tests/integration/exports`` drives the same
chain and seeds the same rows; two copies of that would be two things to keep in step.

The harness is loaded **by explicit path** with ``importlib.util.spec_from_file_location``,
which is the mechanism ``tests/contract/api_v1`` and ``tests/contract/test_cp00_final_state``
already use for a helper module beside a suite. The root ``pyproject.toml`` says a lane
that adds ``sys.path`` juggling to a conftest is working around the import contract
rather than extending it, and ``--import-mode=importlib`` means a bare
``from harness import ...`` would not resolve anyway. Loading by path adds nothing to
``sys.path`` and cannot collide with another lane's module of the same name.

Test modules reach the non-fixture helpers through the ``helpers`` fixture rather than
importing them, for the same reason.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parent / "harness.py"
_spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
assert _spec is not None and _spec.loader is not None
harness: ModuleType = importlib.util.module_from_spec(_spec)
# Registered before execution because ``@dataclass`` resolves annotations through
# ``sys.modules[cls.__module__]``; a module executed outside it raises. This is the
# module object itself, not a ``sys.path`` entry.
sys.modules[_HARNESS_NAME] = harness
_spec.loader.exec_module(harness)

# Bind the harness's fixture functions into this conftest's namespace so pytest
# registers them for this directory.
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
