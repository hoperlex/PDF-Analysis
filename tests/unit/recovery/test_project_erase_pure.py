"""`PROD-07A-PROJECT-ERASE-CORE-01`: the parts of the project erase that need no database.

``tests/integration/recovery/test_project_erase.py`` drives the whole tool on a real stand. This module
holds what can be decided without one, and what an operator meets before anything is touched:

* the deletion order of a cyclic foreign-key graph (``deletion_order``);
* the canonical forms that are hashed (the plan, the manifest) and what they are independent of;
* the argument guards of ``check_arguments`` -- each one shown refusing, accepting the boundary and
  failing (the refusal gone) when its ``# >>> guard`` block is deleted from a copy of the source.

Nothing here opens a connection, reads a credential or touches the network.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import sys
import types
from pathlib import Path

import pytest

from scripts.recovery import project_erase as tool

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/recovery/project_erase.py"
PROJECT = "prj_01M5F21PBT7E8WRN3M61BDQFDD"
ERASE = "era_01M5F21PBT7E8WRN3M61BDQFDD"
SHA = "a" * 64


# --- the deletion order ---------------------------------------------------------------------------


def test_a_chain_is_deleted_from_the_leaf_to_the_root() -> None:
    order = tool.deletion_order(["a", "b", "c"], [("c", "b"), ("b", "a")])
    assert order == [("c",), ("b",), ("a",)]


def test_a_diamond_waits_for_both_children_and_ties_are_broken_by_name() -> None:
    edges = [("left", "root"), ("right", "root"), ("leaf", "left"), ("leaf", "right")]
    assert tool.deletion_order(["root", "left", "right", "leaf"], edges) == [
        ("leaf",), ("left",), ("right",), ("root",)]


def test_tables_that_reference_each_other_are_one_group_deleted_in_one_statement() -> None:
    # document <-> document_version (the current-version foreign key), with a child of each
    edges = [("document", "document_version"), ("document_version", "document"),
             ("manifest", "document_version"), ("document", "project")]
    assert tool.deletion_order(["project", "document", "document_version", "manifest"], edges) == [
        ("manifest",), ("document", "document_version"), ("project",)]


def test_a_self_reference_is_not_a_cycle_between_tables() -> None:
    assert tool.deletion_order(["audit_run", "job"], [("audit_run", "audit_run"), ("job", "audit_run")]) == [
        ("job",), ("audit_run",)]


def test_names_that_are_not_tables_of_the_closure_are_ignored() -> None:
    assert tool.deletion_order(["a", "b"], [("a", "b"), ("a", "elsewhere"), ("outside", "b")]) == [("a",), ("b",)]


def test_the_order_does_not_depend_on_the_order_the_catalog_listed_things_in() -> None:
    tables = ["project", "document", "document_version", "run", "job", "attempt", "finding", "observation"]
    edges = [("document", "project"), ("document", "document_version"), ("document_version", "document"),
             ("run", "project"), ("run", "document_version"), ("job", "run"), ("job", "attempt"),
             ("attempt", "job"), ("finding", "project"), ("observation", "finding"), ("finding", "observation"),
             ("observation", "run")]
    expected = tool.deletion_order(tables, edges)
    rng = random.Random(7)
    for _ in range(25):
        shuffled_tables, shuffled_edges = tables[:], edges[:]
        rng.shuffle(shuffled_tables)
        rng.shuffle(shuffled_edges)
        assert tool.deletion_order(shuffled_tables, shuffled_edges) == expected
    position = {table: index for index, group in enumerate(expected) for table in group}
    for child, parent in edges:
        assert position[child] <= position[parent]  # a referencing table is never deleted after what it references


def test_every_permutation_of_a_small_graph_gives_a_valid_order() -> None:
    tables = ["a", "b", "c", "d"]
    edges = [("b", "a"), ("c", "a"), ("d", "b"), ("d", "c")]
    for permutation in itertools.permutations(edges):
        order = tool.deletion_order(tables, list(permutation))
        position = {table: i for i, group in enumerate(order) for table in group}
        assert all(position[c] < position[p] for c, p in edges)


# --- the addresses of rows ---------------------------------------------------------------------------


def test_a_row_is_addressed_by_its_primary_key_joined_with_the_unit_separator() -> None:
    assert tool.node_sql("t", ["project_uid"]) == 't."project_uid"::text'
    assert tool.node_sql("t", ["run_id", "stage_id"]) == 'concat_ws(chr(31), t."run_id"::text, t."stage_id"::text)'


def test_a_name_that_is_not_a_plain_identifier_never_reaches_a_statement() -> None:
    for bad in ('x"; DROP TABLE project; --', "Upper", "a b", ""):
        with pytest.raises(tool.EraseFailed):
            tool.node_sql("t", [bad])
        with pytest.raises(tool.EraseFailed):
            tool._identifier(bad)


# --- the canonical forms -------------------------------------------------------------------------------


def _blob(number: int) -> tool.BlobFact:
    return tool.BlobFact(f"blob_{number:026d}", f"{number:064x}", 100 + number, "application/pdf", "available")


def _object(number: int) -> tool.PlanObject:
    return tool.PlanObject(f"blobs/AA/BB/{number:026d}", "canonical", f"blob_{number:026d}", None)


def _document(**changes: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        head="0033_ar_v3_cite_stage_id", project_uid=PROJECT,
        table_facts={"document": (1, "11"), "project": (1, "22"), "audit_run": (0, "0")},
        receipt_fact=(2, "33"), exclusive=[_blob(1), _blob(2)], shared=["blob_S1", "blob_S2"],
        objects=[_object(1), _object(2)])
    base.update(changes)
    return tool.plan_document(**base)  # type: ignore[arg-type]


def test_the_plan_digest_is_over_the_canonical_form_and_ignores_the_order_of_everything() -> None:
    reference = tool.plan_digest(_document())
    assert re.fullmatch(r"[0-9a-f]{64}", reference)
    shuffled = _document(table_facts={"project": (1, "22"), "audit_run": (0, "0"), "document": (1, "11")},
                         exclusive=[_blob(2), _blob(1)], shared=["blob_S2", "blob_S1"],
                         objects=[_object(2), _object(1)])
    assert tool.plan_digest(shuffled) == reference
    assert tool.plan_digest(json.loads(json.dumps(_document()))) == reference  # a file round trip changes nothing


@pytest.mark.parametrize("change", [
    {"head": "0034_next"}, {"project_uid": "prj_01M5F21PBT7E8WRN3M61BDQFDE"},
    {"table_facts": {"document": (2, "11"), "project": (1, "22"), "audit_run": (0, "0")}},
    {"table_facts": {"document": (1, "12"), "project": (1, "22"), "audit_run": (0, "0")}},
    {"table_facts": {"document": (1, "11"), "project": (1, "22")}},
    {"receipt_fact": (3, "33")}, {"receipt_fact": (2, "34")},
    {"exclusive": [_blob(1)]}, {"shared": ["blob_S1"]}, {"objects": [_object(1)]},
    {"objects": [_object(1), tool.PlanObject("temporary/x", "temporary", "x", None)]},
])
def test_every_fact_of_the_plan_moves_the_digest(change: dict[str, object]) -> None:
    assert tool.plan_digest(_document(**change)) != tool.plan_digest(_document())


def test_the_plan_names_nobody_and_gives_no_reason() -> None:
    names = set(tool.plan_document.__code__.co_varnames[:tool.plan_document.__code__.co_argcount])
    assert names == {"head", "project_uid", "table_facts", "receipt_fact", "exclusive", "shared", "objects"}
    assert set(_document()) == {"blobs", "objects", "project_uid", "receipts", "schema_head", "tables", "version"}


def test_object_sizes_are_not_part_of_the_plan() -> None:
    sized = [tool.PlanObject(o.key, o.kind, o.ref, 123) for o in (_object(1), _object(2))]
    assert tool.plan_digest(_document(objects=sized)) == tool.plan_digest(_document())


def test_the_manifest_is_byte_deterministic_sorted_and_carries_no_time() -> None:
    blobs = [_blob(3), _blob(1), _blob(2)]
    first = tool.manifest_bytes(ERASE, PROJECT, blobs)
    assert tool.manifest_bytes(ERASE, PROJECT, list(reversed(blobs))) == first
    assert first.endswith(b"\n") and hashlib.sha256(first).hexdigest() == tool.sha256_text(first)
    document = json.loads(first)
    assert set(document) == {"blobs", "erase_id", "project_uid", "version"}
    assert [b["blob_id"] for b in document["blobs"]] == sorted(b.blob_id for b in blobs)
    assert all(set(b) == {"blob_id", "media_type", "sha256", "size_bytes"} for b in document["blobs"])
    assert tool.manifest_bytes(ERASE, PROJECT, blobs[:2]) != first
    assert tool.manifest_bytes("era_01M5F21PBT7E8WRN3M61BDQFDE", PROJECT, blobs) != first


def test_canonical_json_is_sorted_compact_and_ascii() -> None:
    assert tool.canonical_json({"b": [1, {"z": "я"}], "a": None}) == '{"a":null,"b":[1,{"z":"\\u044f"}]}'


def test_a_file_is_written_whole_and_leaves_no_partial_name(tmp_path: Path) -> None:
    target = tmp_path / "plan.json"
    tool.atomic_write(target, b"one")
    tool.atomic_write(target, b"two")
    assert target.read_bytes() == b"two" and sorted(p.name for p in tmp_path.iterdir()) == ["plan.json"]


def test_the_declared_vocabularies_are_the_adrs() -> None:
    assert tool.REASON_CODES == ("client_request", "end_of_engagement", "test_data", "other")
    assert (tool.EVENT_REQUESTED, tool.EVENT_COMPLETED, tool.EVENT_AGGREGATE) == (
        "erasure.requested", "erasure.completed", "ErasureRequest")
    assert tool.DELETE_GUARD_FUNCTIONS == {"am_immutable_row", "am_append_only"}


def test_the_plan_is_rendered_with_its_counts_and_its_digest() -> None:
    plan = tool.Plan(
        database="d", bucket="b", head="h", project_uid=PROJECT, scope={},
        table_facts={"document": (3, "x"), "audit_run": (0, "0"), "project": (1, "y")}, receipts=("c1", "c2"),
        receipt_fact=(2, "z"), exclusive=(_blob(1),), shared=("blob_S",),
        objects=(tool.PlanObject("k1", "canonical", "r1", 10), tool.PlanObject("k2", "temporary", "r2", None)),
        journal_events=5, sha256=SHA, closure=None)  # type: ignore[arg-type]
    text = tool.render_plan(plan, dry_run=True)
    assert "  document  (3 rows)" in text and "audit_run" not in text.split("-- Blobs --")[0]
    assert "  command_record  (2 idempotency receipts of those rows)" in text and "total: 6 rows in 3 tables" in text
    assert "objects to delete, by exact key: 2 keys, 1 present in the bucket, 10 bytes" in text
    assert "run-journal events of the project (identities only): 5" in text
    assert "--dry-run: NOTHING ABOVE WAS CHANGED." in text and text.endswith(f"plan-sha256: {SHA}")
    assert "NOTHING ABOVE WAS CHANGED" not in tool.render_plan(plan, dry_run=False)


# --- the argument guards ----------------------------------------------------------------------------------


def namespace(**changes: object) -> argparse.Namespace:
    values: dict[str, object] = dict(
        project=PROJECT, apply=True, resume=None, plan_sha256=SHA, actor="admin", reason="test_data",
        owner_permission_ref="owner message 2026-10-26", dump_dir=Path("/dump"), dry_run=False)
    values.update(changes)
    return argparse.Namespace(**values)


def refusal(**changes: object) -> str:
    with pytest.raises(tool.EraseRefused) as caught:
        tool.check_arguments(namespace(**changes))
    return str(caught.value)


def test_the_complete_apply_passes_every_argument_guard() -> None:
    tool.check_arguments(namespace())
    tool.check_arguments(namespace(apply=False, resume=ERASE, project=None, plan_sha256=None, reason=None))
    tool.check_arguments(namespace(apply=False, plan_sha256=None, reason=None, owner_permission_ref=None,
                                   dump_dir=None, actor=None))  # a dry run needs only the project


@pytest.mark.parametrize("project", [None, "", "Школа на 550 мест", "prj_short", PROJECT.lower(), PROJECT + "0",
                                     "doc_01M5F21PBT7E8WRN3M61BDQFDD", PROJECT + "\n"])
def test_a_project_is_an_identity_never_a_name(project: str | None) -> None:
    assert "must be a project identity" in refusal(project=project, apply=False)
    assert "must be a project identity" in refusal(project=project)


@pytest.mark.parametrize("resume", ["", "era_short", PROJECT, ERASE.lower(), ERASE + "x"])
def test_a_resume_names_an_erase_identity(resume: str) -> None:
    assert "must be an erase identity" in refusal(apply=False, resume=resume, project=None)


@pytest.mark.parametrize("reference", [None, "", " ", "\t", "x" * 201, "line one\nline two", "bell\x07", "del\x7f"])
def test_the_owner_permission_reference_must_be_one_clean_line_of_at_most_200_characters(reference: str | None) -> None:
    message = refusal(owner_permission_ref=reference)
    assert "--owner-permission-ref" in message and "R-146aj" in message and "cannot verify" in message
    assert "--owner-permission-ref" in refusal(apply=False, resume=ERASE, project=None, owner_permission_ref=reference)


@pytest.mark.parametrize("reference", ["x" * 200, "  письмо владельца от 26.10.2026  ", "ref #1, see mail (2026-10-26)"])
def test_the_boundary_and_free_text_are_accepted(reference: str) -> None:
    tool.check_arguments(namespace(owner_permission_ref=reference))


@pytest.mark.parametrize("sha", [None, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64, " " + "a" * 63])
def test_an_apply_is_refused_without_the_plan_digest_it_was_shown(sha: str | None) -> None:
    assert "--apply needs --plan-sha256" in refusal(plan_sha256=sha)


@pytest.mark.parametrize("reason", [None, "", "other ", "Client_Request", "the client wrote to me", "test-data"])
def test_the_reason_is_one_of_the_closed_list(reason: str | None) -> None:
    assert "--reason must be one of" in refusal(reason=reason)


@pytest.mark.parametrize("reason", list(tool.REASON_CODES))
def test_each_reason_of_the_list_is_accepted(reason: str) -> None:
    tool.check_arguments(namespace(reason=reason))


def test_the_dump_directory_is_required_for_an_apply_and_a_resume() -> None:
    assert "--dump-dir is required" in refusal(dump_dir=None)
    assert "--dump-dir is required" in refusal(apply=False, resume=ERASE, project=None, dump_dir=None)


def test_the_first_failing_argument_is_the_one_named() -> None:
    assert "must be a project identity" in refusal(project="a name", owner_permission_ref=None, plan_sha256=None)
    assert "--owner-permission-ref" in refusal(plan_sha256=None, reason="x", dump_dir=None, owner_permission_ref="")
    assert "--dump-dir is required" in refusal(plan_sha256=None, reason="x", dump_dir=None)
    assert "--apply needs --plan-sha256" in refusal(plan_sha256=None, reason="x")


# --- every argument guard shown able to fail ---------------------------------------------------------------

_BLOCK = r"^[ \t]*# >>> guard: {name}\n.*?^[ \t]*# <<< guard: {name}\n"
_COUNTER = itertools.count()


def mutant(*guards: str) -> types.ModuleType:
    source = SOURCE.read_text(encoding="utf-8")
    for name in guards:
        source, matched = re.subn(_BLOCK.format(name=re.escape(name)), "", source, flags=re.DOTALL | re.MULTILINE)
        assert matched == 1, name
    module = types.ModuleType(f"scripts.recovery.project_erase_unit_mutant_{next(_COUNTER)}")
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(source, f"<project_erase without {guards}>", "exec"), module.__dict__)  # noqa: S102
    return module


@pytest.mark.parametrize("guard, changes", [
    ("project-identity-shape", {"project": "Школа на 550 мест"}),
    ("owner-permission-ref", {"owner_permission_ref": None}),
    ("owner-permission-ref", {"owner_permission_ref": "x" * 201}),
    ("dump-dir-required", {"dump_dir": None}),
    ("plan-digest-required", {"plan_sha256": None}),
    ("plan-digest-required", {"plan_sha256": "not hex"}),
    ("reason-closed-list", {"reason": "the client wrote to me"}),
])
def test_deleting_an_argument_guard_lets_the_bad_value_through(guard: str, changes: dict[str, object]) -> None:
    refusal(**changes)  # the real module refuses
    broken = mutant(guard)
    # the copy without the block raises nothing: a permission-less, digest-less, free-text apply is accepted
    broken.check_arguments(namespace(**changes))


def test_the_argument_guards_are_all_blocks_of_check_arguments() -> None:
    body = SOURCE.read_text(encoding="utf-8")
    inside = body[body.index("def check_arguments"):body.index("def render_done")]
    assert sorted(re.findall(r"# >>> guard: ([a-z-]+)", inside)) == sorted([
        "dump-dir-required", "owner-permission-ref", "plan-digest-required", "project-identity-shape",
        "reason-closed-list"])


def test_every_guard_block_can_be_deleted_and_what_is_left_still_compiles() -> None:
    """The mutation harness deletes one block at a time: a block that held a needed statement breaks here, early."""
    body = SOURCE.read_text(encoding="utf-8")
    names = re.findall(r"^[ \t]*# >>> guard: ([a-z-]+)$", body, re.MULTILINE)
    assert len(names) == len(set(names)) >= 40
    for name in names:
        mutant(name)
