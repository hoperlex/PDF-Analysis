"""`W54-BUNDLE-01`: ``manifest.json`` is canonical and refuses any figure that does not add up.

Container-free. A manifest the export wrote is the starting point; each case changes one
figure and shows the parser refuses it, so a manifest that lies about itself cannot reach
custody.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.norms.bundle.errors import BundleRefused
from auditmanager.norms.bundle.export import write_bundle
from auditmanager.norms.bundle.layout import MANIFEST_NAME
from auditmanager.norms.bundle.manifest import MANIFEST_FORMAT, parse_manifest
from tests.integration.norms.bundle.support import synthetic_rows, write_drop
from tests.integration.norms.bundle.test_export_offline import _source


@pytest.fixture
def document(tmp_path: Path) -> dict:
    corpus, sums = write_drop(tmp_path / "drop")
    directory = write_bundle(
        _source(synthetic_rows()), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out"
    ).directory
    return json.loads((directory / MANIFEST_NAME).read_text())


def test_the_manifest_renders_canonically_and_parses_back(document: dict) -> None:
    data = (json.dumps(document, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode()
    manifest = parse_manifest(data)
    assert manifest.render() == data
    assert document["format"] == MANIFEST_FORMAT and document["manifest_version"] == 1
    assert document["min_migration_head"] == "0018_norm_custody"
    assert data.isascii()


def _object(document: dict) -> dict:
    return next(entry for entry in document["files"] if entry["kind"] == "object")


EDITS = {
    "version": lambda d: d.update(manifest_version=2),
    "unknown-key": lambda d: d.update(extra=1),
    "binding-digest": lambda d: d["custody"].update(binding_digest="0" * 64),
    "slot-count": lambda d: d["counts"].update(slots=d["counts"]["slots"] + 1),
    "object-count": lambda d: d["counts"].update(objects=1),
    "object-bytes": lambda d: d.update(object_bytes=d["object_bytes"] + 1),
    "object-path": lambda d: _object(d).update(path="objects/00/" + "0" * 64 + ".pdf"),
    "media-type": lambda d: _object(d).update(media_type="image/png"),
    "duplicate-slot": lambda d: _object(d)["slots"].append(dict(_object(d)["slots"][0])),
    "anchor-kind": lambda d: _object(d)["slots"][0].update(anchor_kind="page"),
    "target": lambda d: _object(d)["slots"][0].update(target_id="ndoc_not_an_id"),
    "build-counts": lambda d: d["build"].update(window_count=d["build"]["window_count"] + 1),
    "build-files-without-build": lambda d: d.update(build=None),
    "repair-without-ledger": lambda d: d["snapshot"].update(repair_count=1),
    "row-digest-version": lambda d: d["row_digest"].update(version="norm-snapshot-rows/0"),
    "embedding-profile": lambda d: d["build"].update(embedding_profile="other"),
    "content-key": lambda d: d.update(content_key="not a key"),
    "results-for-another-document": lambda d: d["drop"]["results_md_sha256"].update({"ndoc_x": "0" * 64}),
    "manifest-lists-itself": lambda d: d["files"].append(
        {"path": "manifest.json", "kind": "rows", "sha256": "0" * 64, "size": 1}
    ),
}


@pytest.mark.parametrize("edit", sorted(EDITS))
def test_a_manifest_that_does_not_add_up_is_refused(document: dict, edit: str) -> None:
    EDITS[edit](document)
    data = (json.dumps(document, sort_keys=True, indent=1) + "\n").encode()
    with pytest.raises(BundleRefused) as refused:
        parse_manifest(data)
    assert refused.value.reason in ("manifest_invalid", "content_key_grammar", "bundle_path_grammar"), refused.value


def test_one_slot_served_by_two_objects_is_refused_even_when_every_figure_adds_up(document: dict) -> None:
    import dataclasses

    from auditmanager.norms.bundle.manifest import validate_manifest
    from auditmanager.norms.custody import binding_digest

    manifest = parse_manifest((json.dumps(document, sort_keys=True, indent=1) + "\n").encode())
    first, second = manifest.files_of("object")[:2]
    doubled = dataclasses.replace(second, slots=(*second.slots, first.slots[0]))
    files = tuple(doubled if entry is second else entry for entry in manifest.files)
    forged = dataclasses.replace(manifest, files=files)
    forged = dataclasses.replace(forged, binding_digest=binding_digest(forged.binding_entries()))
    with pytest.raises(BundleRefused, match="served by two objects"):
        validate_manifest(forged)
