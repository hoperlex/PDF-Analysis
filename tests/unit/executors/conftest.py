"""Fixtures for the executor unit tests: the fake gateway, loaded by explicit path."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest

_NAME = "am_exec_fake_gateway"
_PATH = Path(__file__).resolve().parent / "fake_gateway.py"
if _NAME in sys.modules:
    fake_gateway_module: ModuleType = sys.modules[_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_NAME, _PATH)
    assert _spec is not None and _spec.loader is not None
    fake_gateway_module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = fake_gateway_module
    _spec.loader.exec_module(fake_gateway_module)


@pytest.fixture
def gateway_factory() -> Iterator[Callable[..., object]]:
    started: list[object] = []

    def make(**options: object) -> object:
        gateway = fake_gateway_module.FakeGateway(**options).start()
        started.append(gateway)
        return gateway

    yield make
    for gateway in started:
        gateway.stop()  # type: ignore[attr-defined]


@pytest.fixture
def fake_gateway_module_fixture() -> ModuleType:
    return fake_gateway_module
