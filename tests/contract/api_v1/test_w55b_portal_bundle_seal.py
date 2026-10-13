"""`W55B-SEAL-01`: what the portal-bundle seal declares, checked without a database.

The database half is ``tests/integration/db/test_portal_bundles_migration.py``. This module
holds the parts that are pure functions of the tree:

* the two portal-block operations: path, tag, roles, response set, the `404` an absent parent
  must be able to answer, the `422` only the listing can answer;
* the seven new schemas are closed, and ``PortalBlock``'s required/optional split is the one
  the wire body function renders (an absent optional member is omitted, never ``null``);
* ``portal_block_id`` is registered as an **external** identifier beside the identities and
  not among them, with a pattern that is not a ULID;
* the new error code, its detail keys, and every constraint value the bundle upload can
  report being registered in the domain catalog's notes (a value nobody registered is a value
  nobody can match on);
* the upload contract: a ZIP, 500 pages, 250 MiB, a bare PDF refused, the D-110 sentence;
* the stage registry names the new roles, and the registry's own roles are the ones the
  seam register's manifest roles come from.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from auditmanager.api.schemas.blocks import (
    PortalBlockIndexView,
    PortalBlockView,
    PortalCropView,
    PortalRecognisedTextView,
    portal_block_body,
    portal_block_page_body,
)
from auditmanager.api.security import OPERATION_ROLES
from auditmanager.shared.errors import ErrorCode

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
ERRORS = json.loads((ROOT / "contracts/domain/v1/error-codes.json").read_text(encoding="utf-8"))
IDENTIFIERS = json.loads((ROOT / "contracts/domain/v1/identifiers.json").read_text(encoding="utf-8"))
REGISTRY = json.loads((ROOT / "contracts/analysis/v1/stage-registry.json").read_text(encoding="utf-8"))

LIST_PATH = "/versions/{version_uid}/portal-blocks"
CROP_PATH = "/versions/{version_uid}/portal-blocks/{portal_block_id}/crop"
NEW_SCHEMAS = (
    "PortalBlockId",
    "PortalBlockType",
    "PortalGeometryState",
    "PortalCrop",
    "PortalRecognisedText",
    "PortalBlock",
    "PortalBlockPage",
)

#: Every `constraint` the portal-bundle upload can report that is new in W55b. Written out
#: here, not read from the catalog, so deleting one from the notes is a red and not a pass.
BUNDLE_CONSTRAINTS = (
    "portal_bundle_required",
    "bundle_unreadable",
    "bundle_entry_count",
    "bundle_directory_entry",
    "bundle_member_name",
    "bundle_symlink",
    "bundle_encrypted_member",
    "bundle_compression_method",
    "bundle_duplicate_member",
    "bundle_stem_mismatch",
    "bundle_member_set",
    "bundle_member_size",
    "bundle_total_size",
    "bundle_compression_ratio",
    "blocks_json_invalid",
    "blocks_page_count",
    "results_blocks_mismatch",
    "stamp_audit_invalid",
)


def _operation(path: str) -> dict[str, Any]:
    return CONTRACT["paths"][path]["get"]


# --- the surface --------------------------------------------------------------------------


def test_both_reads_are_documents_operations_for_any_one_role() -> None:
    for path, operation_id in ((LIST_PATH, "listVersionPortalBlocks"), (CROP_PATH, "streamVersionPortalBlockCrop")):
        operation = _operation(path)
        assert operation["operationId"] == operation_id
        assert operation["tags"] == ["documents"]
        assert OPERATION_ROLES[operation_id] == frozenset({"expert", "admin"}), operation_id


def test_the_listing_pages_and_can_refuse_a_cursor_and_the_crop_declares_no_422() -> None:
    listing, crop = _operation(LIST_PATH), _operation(CROP_PATH)
    assert set(listing["responses"]) == {"200", "401", "403", "404", "422", "500", "503"}
    assert set(crop["responses"]) == {"200", "401", "403", "404", "500", "503"}
    assert {ref["$ref"].rsplit("/", 1)[1] for ref in listing["parameters"]} == {"Cursor", "Limit", "CorrelationId"}


def test_the_crop_is_a_png_and_the_listing_is_a_page_of_blocks() -> None:
    crop_ok = _operation(CROP_PATH)["responses"]["200"]["content"]
    assert set(crop_ok) == {"image/png"}
    listing_ok = _operation(LIST_PATH)["responses"]["200"]["content"]["application/json"]["schema"]
    assert listing_ok == {"$ref": "#/components/schemas/PortalBlockPage"}


def test_the_portal_block_path_parameter_is_the_external_pattern_and_not_a_ulid() -> None:
    parameter = CONTRACT["components"]["parameters"]["PortalBlockId"]
    assert parameter["name"] == "portal_block_id" and parameter["in"] == "path"
    schema = CONTRACT["components"]["schemas"]["PortalBlockId"]
    assert schema["pattern"] == "^blk_[0-9a-f]{32}$"
    assert re.fullmatch(schema["pattern"], "blk_" + "0123456789abcdef" * 2)
    assert not re.fullmatch(schema["pattern"], "blk_01ARZ3NDEKTSV4RRFFQ69G5FAV")


def test_the_seven_new_schemas_are_declared_and_every_object_is_closed() -> None:
    schemas = CONTRACT["components"]["schemas"]
    for name in NEW_SCHEMAS:
        assert name in schemas, name
        if schemas[name].get("type") == "object":
            assert schemas[name]["additionalProperties"] is False, name


def test_a_portal_block_requires_what_is_always_known_and_omits_the_rest() -> None:
    block = CONTRACT["components"]["schemas"]["PortalBlock"]
    assert set(block["required"]) == {
        "portal_block_id", "page_number", "page_label", "ordinal", "block_type", "status", "bbox_norm", "geometry",
    }
    assert set(block["properties"]) - set(block["required"]) == {
        "polygon_points", "crop", "recognised_text", "portal_description",
    }
    assert block["properties"]["bbox_norm"]["minItems"] == block["properties"]["bbox_norm"]["maxItems"] == 4
    assert CONTRACT["components"]["schemas"]["PortalRecognisedText"]["properties"]["quote_source"]["const"] == "recognised"
    assert CONTRACT["components"]["schemas"]["DocumentVersion"]["properties"]["page_count"]["maximum"] == 500


# --- the wire body ------------------------------------------------------------------------


def _view(**changes: Any) -> PortalBlockView:
    fields: dict[str, Any] = dict(
        portal_block_id="blk_" + "a" * 32, page_number=2, page_label=2, ordinal=0,
        block_type="text", status="recognized", bbox_norm=(0.1, 0.2, 0.3, 0.4), geometry="ok",
    )
    fields.update(changes)
    return PortalBlockView(**fields)


def test_an_absent_optional_member_is_omitted_and_never_null() -> None:
    body = portal_block_body(_view())
    assert set(body) == {
        "portal_block_id", "page_number", "page_label", "ordinal", "block_type", "status", "bbox_norm", "geometry",
    }
    assert None not in [v for k, v in body.items() if k != "ordinal"]
    full = portal_block_body(_view(
        block_type="image", polygon_points=((0.1, 0.1), (0.2, 0.1), (0.2, 0.2)),
        crop=PortalCropView("image/png", 900, 800, "b" * 64),
        recognised_text=PortalRecognisedTextView("текст", ("mixed_script",)),
        portal_description="описание",
    ))
    assert full["polygon_points"] == [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2]]
    assert full["recognised_text"] == {"quote_source": "recognised", "text": "текст", "flags": ["mixed_script"]}
    assert full["crop"]["media_type"] == "image/png"


def test_a_stamp_has_a_null_ordinal_and_the_page_counts_the_whole_version() -> None:
    index = PortalBlockIndexView("ver_x", "produced", "run_y", (_view(), _view(ordinal=None, block_type="stamp")))
    page = portal_block_page_body(index, index.blocks[:1], "cursor")
    assert page["block_count"] == 2 and len(page["items"]) == 1
    assert page["page"] == {"next_cursor": "cursor"}
    assert portal_block_body(index.blocks[1])["ordinal"] is None


# --- the identifier -----------------------------------------------------------------------


def test_portal_block_id_is_an_external_identifier_and_not_one_of_the_identities() -> None:
    assert "portal_block_id" not in IDENTIFIERS["identifiers"]
    assert "blk" not in IDENTIFIERS["identifiers"].values()
    external = IDENTIFIERS["external_identifiers"]["portal_block_id"]
    assert external["prefix"] == "blk" and external["is_entity_identity"] is False
    assert external["pattern"] == "^blk_[0-9a-f]{32}$"
    assert len(IDENTIFIERS["identifiers"]) == 32


# --- the error catalog --------------------------------------------------------------------


def test_the_budget_refusal_is_a_422_that_is_never_retried_and_names_two_integers() -> None:
    entry = ERRORS["codes"]["analysis_input_budget_exceeded"]
    assert (entry["http"], entry["retryable"]) == (422, False)
    assert entry["safe_detail_keys"] == ["character_count", "budget_characters"]
    assert ErrorCode("analysis_input_budget_exceeded").http_status == 422
    assert "analysis_input_budget_exceeded" in CONTRACT["components"]["schemas"]["ErrorCode"]["enum"]
    assert len(ERRORS["codes"]) == 24 == len(CONTRACT["components"]["schemas"]["ErrorCode"]["enum"])


@pytest.mark.parametrize("constraint", BUNDLE_CONSTRAINTS)
def test_every_bundle_constraint_is_registered_in_the_catalog(constraint: str) -> None:
    notes = " ".join(ERRORS["codes"]["validation_failed"]["notes"])
    assert re.search(rf"\b{constraint}\b", notes), constraint


def test_the_busy_refusal_is_a_registered_dependency_class_and_not_a_new_code() -> None:
    notes = " ".join(ERRORS["codes"]["dependency_unavailable"]["notes"])
    assert "upload_capacity" in notes and "Retry-After" in notes
    assert ERRORS["codes"]["dependency_unavailable"]["safe_detail_keys"] == ["dependency"]


# --- the upload ----------------------------------------------------------------------------


def test_the_upload_is_declared_as_a_bundle_with_the_new_limits() -> None:
    operation = CONTRACT["paths"]["/projects/{project_uid}/documents"]["post"]
    assert operation["requestBody"]["content"]["multipart/form-data"]["encoding"]["file"]["contentType"] == "application/zip"
    text = operation["description"]
    for needle in ("portal bundle", "500 pages", "250 MiB", "portal_bundle_required", "_stamp_audit.json",
                   "digest only", "OCR is always marked", "D-110", "upload_capacity", "Retry-After"):
        assert needle in text, needle
    assert "30 pages" not in text and "25 MiB" not in text
    file_part = CONTRACT["components"]["schemas"]["UploadDocumentRequest"]["properties"]["file"]["description"]
    assert "250 MiB" in file_part and "500 pages" in file_part


def test_the_budget_refusal_is_declared_on_both_run_starts() -> None:
    assert "analysis_input_budget_exceeded" in CONTRACT["paths"]["/runs"]["post"]["description"]
    assert "analysis_input_budget_exceeded" in CONTRACT["paths"]["/runs/{run_id}/reaudit"]["post"]["description"]
    assert "analysis_input_budget_exceeded" in CONTRACT["components"]["responses"]["RunInputInvalid"]["description"]


# --- the stage registry --------------------------------------------------------------------


def _stage(stage_id: str) -> dict[str, Any]:
    return next(s for s in REGISTRY["stages"] if s["stage_id"] == stage_id)


def _roles(entries: list[dict[str, Any]]) -> dict[str, bool]:
    return {entry["role"]: entry["required"] for entry in entries}


def test_the_registry_declares_the_bundle_roles_and_keeps_the_manifest_required() -> None:
    sp, pg = _stage("source_preparation"), _stage("page_geometry_extraction")
    assert _roles(sp["required_inputs"]) == {
        "source.document": True, "source.markdown": False,
        "source.structured_companion": False, "source.stamp_audit": False,
    }
    assert _roles(sp["produced_outputs"]) == {
        "prepared.page_inventory": True, "prepared.text_layer": True, "prepared.recognised_text": False,
    }
    assert _roles(pg["required_inputs"]) == {
        "prepared.page_inventory": True, "prepared.text_layer": True, "source.structured_companion": False,
    }
    assert _roles(pg["produced_outputs"]) == {
        "geometry.block_index": True, "geometry.page_crops": True,
        "geometry.portal_blocks": False, "geometry.crop_image": False,
    }
    crop_image = next(o for o in pg["produced_outputs"] if o["role"] == "geometry.crop_image")
    assert crop_image["media_type"] == "image/png"


def test_nothing_that_consumes_a_crop_became_reachable() -> None:
    """`block_analysis` still declares the manifest as a required input and nothing newer."""
    assert _roles(_stage("block_analysis")["required_inputs"]) == {
        "geometry.page_crops": True, "geometry.block_index": True, "context.document_graph": True,
    }


def test_the_two_content_schemas_exist_and_are_closed_where_they_describe_our_artifact() -> None:
    crops = json.loads((ROOT / "contracts/analysis/v1/crop-manifest.schema.json").read_text(encoding="utf-8"))
    assert crops["additionalProperties"] is False and crops["properties"]["crop_policy"]["enum"] == ["none", "portal_image_blocks"]
    assert crops["$defs"]["crop"]["additionalProperties"] is False
    profile = crops["$defs"]["crop"]["properties"]["render_profile"]["properties"]
    assert profile["min_long_side_px"]["const"] == 800 and profile["max_pixels"]["const"] == 4_000_000
    blocks = json.loads((ROOT / "contracts/analysis/v1/portal-blocks.schema.json").read_text(encoding="utf-8"))
    # the portal's file: it may add properties, so ours must not refuse a good bundle for one
    assert "additionalProperties" not in blocks
    assert blocks["properties"]["pages"]["items"]["properties"]["rotation"]["enum"] == [0, 90, 180, 270]
    assert blocks["properties"]["blocks"]["items"]["properties"]["block_type"]["enum"] == ["text", "image", "stamp"]
