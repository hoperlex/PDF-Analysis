"""Fixtures for the PC-01 acceptance suite, session ``C2``.

The driver beside this file is loaded by explicit path -- the mechanism
``tests/integration/runs`` and ``tests/contract/api_v1`` already use for a helper beside a
suite. It adds nothing to ``sys.path``, and under ``--import-mode=importlib`` a bare
``from driver import ...`` would not resolve anyway.

**Provider configuration is set here, explicitly and visibly.** The root
``tests/conftest.py`` strips every provider-selecting variable for the whole session
precisely so that a suite which wants a mode has to say so out loud. This one wants
``recorded`` for everything except the single test that names a live call in its own body.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

_DRIVER_NAME = "c2_pc01_driver"


def _load_driver() -> Any:
    existing = sys.modules.get(_DRIVER_NAME)
    if existing is not None:
        return existing
    path = Path(__file__).resolve().with_name("driver.py")
    spec = importlib.util.spec_from_file_location(_DRIVER_NAME, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[_DRIVER_NAME] = module
    spec.loader.exec_module(module)
    return module


driver = _load_driver()


@pytest.fixture(scope="session", autouse=True)
def recorded_provider_mode() -> Iterator[None]:
    """Name the provider mode out loud, because the root conftest removed it.

    Asserted rather than assumed. If that strip were ever reordered after this fixture,
    the suite would silently inherit whatever a developer had exported -- and a shell
    carrying the operated proxy's credentials would turn every test below into a paid
    call. That is the accident the root conftest exists to prevent, so this checks it held.
    """
    driver.load_env_file()
    os.environ["AUDITMANAGER_PROVIDER_MODE"] = "recorded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, (
            f"{leaked} reached this suite; the recorded journey must not be able to spend"
        )
    yield


@pytest.fixture(scope="session")
def manifest() -> Mapping[str, Any]:
    """The corpus's declaration of what it seeds and where."""
    import json

    return json.loads(driver.EXPECTED_ISSUES.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def page_texts(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    """The eight page texts of the baseline PDF, read back from the file bytes.

    Pinned against the manifest's ``page_text_sha256`` *before* any quotation is checked
    against them. Without that pin, a quotation check would be asserting a property of
    whatever this extractor happened to produce rather than of the corpus -- which is the
    exact shape of the vacuous test this programme keeps finding.
    """
    extractor = driver.load_pdfextract()
    pages = tuple(extractor.extract_pages(driver.BASELINE_PDF.read_bytes()))
    declared = tuple(manifest["baseline"]["page_text_sha256"])
    observed = tuple(hashlib.sha256(text.encode("utf-8")).hexdigest() for text in pages)
    assert observed == declared, (
        "the corpus extractor no longer reproduces the page texts the manifest declares, "
        "so every quotation check would be measuring the extractor and not the corpus"
    )
    return pages


@pytest.fixture(scope="session")
def client(recorded_provider_mode: None) -> Any:
    """The application under test, composed once from the environment."""
    return driver.build_client(AUDITMANAGER_PROVIDER_MODE="recorded")
