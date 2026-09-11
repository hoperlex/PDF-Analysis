"""Fixtures for the P02 journey-convergence suite.

The definitions live in ``journey.py`` in the sibling `tests/integration/p02_journey` tree this session also owns, loaded **by explicit
path**, the mechanism ``tests/integration/runs`` and ``tests/contract/api_v1`` already
use for a helper module beside a suite. It adds nothing to ``sys.path``, and with
``--import-mode=importlib`` a bare ``from journey import ...`` would not resolve anyway.
The module name is session-unique so it cannot collide with another lane's helper.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_NAME = "b3conv_journey_harness"
_PATH = Path(__file__).resolve().parents[2] / "integration" / "p02_journey" / "journey.py"
_spec = importlib.util.spec_from_file_location(_NAME, _PATH)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules[_NAME] = _module
_spec.loader.exec_module(_module)

_environment = _module._environment
engine = _module.engine
session_factory = _module.session_factory
session = _module.session
blob_store = _module.blob_store
ingest = _module.ingest
recorded_adapter = _module.recorded_adapter
provider_config = _module.provider_config


import pytest


@pytest.fixture()
def journey_harness():
    """The non-fixture helpers, reached through a fixture rather than imported."""
    return _module
