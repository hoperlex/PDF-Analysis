"""`CMP-SEAL-C0` (ADR-0025 decision 23): the comparison module set and its carrier.

``AUDITMANAGER_COMPARISON_MODULES`` is ``none`` (the default), ``versions`` or ``versions,stages``.
Container-free: it reads the parser, the contract and the adapter that builds the product version.
Each rule is shown failing: a value outside the three is refused rather than read as ``none``, and the
parser's set is held equal to the contract's enum so that one cannot move without the other.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import ReleasesAdapter, _version_view
from auditmanager.comparison import public as comparison

ROOT = Path(__file__).resolve().parents[3]


def _contract_enum(name: str) -> list[str]:
    document = json.loads((ROOT / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    return document["components"]["schemas"][name]["enum"]


def test_the_environment_variable_has_the_name_the_adr_gives() -> None:
    assert comparison.COMPARISON_MODULES_ENV == "AUDITMANAGER_COMPARISON_MODULES"


@pytest.mark.parametrize("value", [None, "", "   ", "none"])
def test_an_absent_or_empty_value_is_none(value: str | None) -> None:
    assert comparison.parse_modules(value) == "none"


@pytest.mark.parametrize("value", ["versions", "versions,stages", " versions,stages "])
def test_the_two_module_sets_are_accepted(value: str) -> None:
    assert comparison.parse_modules(value) == value.strip()


@pytest.mark.parametrize(
    "value", ["stages", "versions, stages", "Versions", "all", "versions,stages,extra", "1", "none,versions"],
)
def test_any_other_value_is_refused_and_never_read_as_none(value: str) -> None:
    with pytest.raises(ValueError) as caught:
        comparison.parse_modules(value)
    message = str(caught.value)
    assert comparison.COMPARISON_MODULES_ENV in message
    assert "none, versions, versions,stages" in message


def test_the_set_of_values_is_the_contracts_enum() -> None:
    assert list(comparison.MODULE_SETS) == _contract_enum("ComparisonModules")
    assert [member.value for member in models.ComparisonModules] == list(comparison.MODULE_SETS)


def test_the_enabled_modules_of_each_set() -> None:
    assert comparison.enabled_modules("none") == frozenset()
    assert comparison.enabled_modules("versions") == frozenset({comparison.MODULE_VERSIONS})
    assert comparison.enabled_modules("versions,stages") == frozenset(
        {comparison.MODULE_VERSIONS, comparison.MODULE_STAGES}
    )
    with pytest.raises(ValueError):
        comparison.enabled_modules("stages")


@pytest.mark.parametrize("value", list(comparison.MODULE_SETS))
def test_the_product_version_carries_the_module_set(value: str) -> None:
    adapter = ReleasesAdapter(SimpleNamespace(), product_version="0.9.0", build_id="b", comparison_modules=value)
    read = adapter.get_product_version()
    assert read.comparison_modules.value == value
    assert read.model_dump(mode="json")["comparison_modules"] == value


def test_the_product_version_defaults_to_none_and_refuses_a_value_outside_the_enum() -> None:
    adapter = ReleasesAdapter(SimpleNamespace(), product_version="0.9.0", build_id="b")
    assert adapter.get_product_version().comparison_modules is models.ComparisonModules.NONE
    with pytest.raises(ValueError):
        ReleasesAdapter(SimpleNamespace(), product_version="0.9.0", build_id="b", comparison_modules="stages")


def test_the_version_view_carries_the_upload_kind_and_the_contract_names_the_two_kinds() -> None:
    assert _contract_enum("VersionUploadKind") == ["portal_bundle", "comparison_pdf"]
    record = SimpleNamespace(
        version_uid="ver_x", document_uid="doc_x", project_uid="prj_x", version_ordinal=1, byte_size=1,
        sha256="a" * 64, page_count=1, published_at=None, media_type="application/pdf", display_title="D",
        section=None, classification=None, manifest=(), upload_kind="comparison_pdf",
    )
    assert _version_view(record).upload_kind == "comparison_pdf"
    default = SimpleNamespace(**{**record.__dict__})
    del default.upload_kind
    with pytest.raises(AttributeError):
        _version_view(default)
