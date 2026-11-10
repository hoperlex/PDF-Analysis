"""`D-669`: ``contracts/analysis/v1/model-catalogue.json`` has one reader, ``analysis.public``; the hosts take their view through it.

Two guards, each of which fails when the old state comes back:

* no module of ``src`` but ``analysis/text/catalogue.py`` holds the file's path as a string constant (the executors used to hold a second
  ``CATALOGUE_RELPATH`` and a second ``json.loads``);
* ``executors.catalogue.load_catalogue`` asks ``analysis.public`` for the document -- a stub planted there is what the hosts' catalogue is
  built from, and the path of a variant is handed on to the one reader.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

import auditmanager
from auditmanager.analysis import public as analysis_public
from auditmanager.executors.catalogue import Catalogue, load_catalogue
from auditmanager.shared.errors import DomainError, ErrorCode

CATALOGUE_PATH = "contracts/analysis/v1/model-catalogue.json"
SRC = Path(auditmanager.__file__).resolve().parent  # the package under test, wherever it is imported from


def _entry(provider: str, model_id: str, **fields: Any) -> analysis_public.CatalogueEntry:
    base: dict[str, Any] = {
        "access": ("api",), "efforts": ("high",), "accepted_reported": (model_id,),
    }
    base.update(fields)
    return analysis_public.CatalogueEntry(provider=provider, model_id=model_id, **base)


def _document(*entries: analysis_public.CatalogueEntry) -> analysis_public.ModelCatalogue:
    return analysis_public.ModelCatalogue(contract_version="0", efforts_vocabulary=("low", "medium", "high"), entries=entries)


def test_only_one_module_of_src_names_the_catalogue_file() -> None:
    holders = sorted(
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and node.value == CATALOGUE_PATH
    )
    # `==` on the whole list, not `in`: a second holder (the executors' old `CATALOGUE_RELPATH`) is a failure.
    assert holders == ["analysis/text/catalogue.py"]


def test_the_hosts_catalogue_is_built_from_what_analysis_public_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    planted = _document(
        _entry("codex", "planted-model", access=("subscription", "api"), efforts=("low", "high"), accepted_reported=("planted-model", "planted-model[x]")),
        _entry("codex", "unpinned-model"),
    )
    monkeypatch.setattr(analysis_public, "model_catalogue", lambda: planted)

    built = load_catalogue(pinned=frozenset({"planted-model"}))

    assert isinstance(built, Catalogue)
    assert [(item.provider, item.model_id, item.accesses, item.efforts, item.accepted_reported) for item in built.entries] == [
        ("codex", "planted-model", ("subscription", "api"), ("low", "high"), ("planted-model", "planted-model[x]"))
    ]


def test_a_variant_path_goes_to_the_one_reader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[Path | None] = []

    def reader(path: Path | None = None) -> analysis_public.ModelCatalogue:
        seen.append(path)
        return _document(_entry("claude_code", "variant-model"))

    monkeypatch.setattr(analysis_public, "load_model_catalogue", reader)
    variant = tmp_path / "variant.json"

    built = load_catalogue(variant, pinned=frozenset({"variant-model"}))

    assert seen == [variant]
    assert [item.model_id for item in built.entries] == ["variant-model"]


def test_an_unreadable_file_stays_dependency_unavailable(tmp_path: Path) -> None:
    with pytest.raises(DomainError) as refused:
        load_catalogue(tmp_path / "absent.json", pinned=frozenset())
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_the_repository_catalogue_keeps_its_hosts_view() -> None:
    """Behaviour of the real file did not move: the hosts' entries are the analysis entries of the lock pins, field for field."""
    pinned = frozenset(pin.model_id for pin in analysis_public.pinned_models())
    expected = [
        (item.provider, item.model_id, item.access, item.efforts, item.accepted_reported)
        for item in analysis_public.model_catalogue().entries
        if item.model_id in pinned
    ]
    built = load_catalogue()
    assert expected
    assert [(item.provider, item.model_id, item.accesses, item.efforts, item.accepted_reported) for item in built.entries] == expected
