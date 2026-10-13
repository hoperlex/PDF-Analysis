"""`W55B-SEAL-01`: pypdfium2 and Pillow are direct dependencies, pinned in all three places.

They were transitive (pdfplumber pulls both), and the portal-bundle envelope and the crop
renderer now import them. A dependency a module imports but nobody declared moves whenever
its parent does, so the three records that name a pin -- ``pyproject.toml``, ``uv.lock`` and
``docs/program/P02_LOCK.json`` -- must agree, and must agree with the version actually
locked. Container-free: it reads three files.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: ``pyproject`` spelling, ``uv.lock`` normalised name, ``P02_LOCK.json`` key.
DIRECT = (
    ("pypdfium2", "pypdfium2", "pypdfium2"),
    ("Pillow", "pillow", "Pillow"),
)


def _declared() -> dict[str, str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    found = {}
    for requirement in project["project"]["dependencies"]:
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([0-9][^\s;]*)", requirement)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def _lock() -> dict:
    return tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("declared", "locked", "record"), DIRECT)
def test_the_three_records_name_one_version(declared: str, locked: str, record: str) -> None:
    pin = _declared()[declared]
    lock = _lock()
    packages = {p["name"]: p["version"] for p in lock["package"]}
    root = next(p for p in lock["package"] if p["name"] == "auditmanager-foundation")
    lock_pins = json.loads((ROOT / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))["pins"]

    assert packages[locked] == pin, "uv.lock resolves a different version than pyproject pins"
    assert {"name": locked} in root["dependencies"], "uv.lock's root package does not depend on it"
    specifier = next(r for r in root["metadata"]["requires-dist"] if r["name"] == locked)
    assert specifier["specifier"] == f"=={pin}"
    assert lock_pins[record]["version"] == pin, "P02_LOCK.json records a different version"
    assert lock_pins[record]["licence"] and lock_pins[record]["purpose"]


def test_the_guard_can_fail() -> None:
    """The parametrised case above is not vacuous: a drifted record is a different string."""
    assert _declared()["pypdfium2"] != "0.0.0"
    assert not re.fullmatch(r"([A-Za-z0-9_.-]+)==([0-9][^\s;]*)", "pypdfium2>=5")
