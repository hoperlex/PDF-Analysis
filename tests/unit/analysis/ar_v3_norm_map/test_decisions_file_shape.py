"""Shape and honesty checks for the AR v3 beta decision files in ``docs/program/ar-v3-beta/``.

``decisions.json`` is read by the real ``map_pack`` tool; this file checks what the tool does
not: that the 22 items are the ones the integrator ordered (14 ``provisional_citation`` and the
8 policy items ``context_only``), that every span is the proposal's span with consistent ids,
that no sentence claims an edition is current, and that the query-vector placeholder is either
wholly present and marked, or wholly replaced. The tool accepts 64 hex zeros as a digest, so
without this guard a file with the placeholder left in would build and validate.

Every guard has a mutation case (``MUTATIONS``) that must make it report its problem code, so a
guard that can no longer fail is itself a red test. Nothing here reads a database or the
norms corpus; the files hold ids, ordinals, digests and authored text only.

``AR_V3_DECISIONS_REQUIRE_FINAL=1`` additionally requires the final state (real vector digests
in ``decisions.json`` and real map digests in ``scopes.json``); the integrator sets it before
sealing.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

import pytest

from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack
from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import load_beta_source_policy
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.profiles.ar_v3.v3_profile import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.norms.public import EMBEDDING_PROFILE, SET_BUILDER_VERSION
from auditmanager.runs import v3_pack_cli
from auditmanager.runs.v3_pack_manifest import PackManifestRefused
from auditmanager.shared.identity import NormDocumentId, NormParagraphId

ROOT = Path(__file__).resolve().parents[4]
BETA = ROOT / "docs" / "program" / "ar-v3-beta"
SCOPES = ("F1", "F2", "A1", "A2", "S1", "S2")
ITEM_IDS = tuple(f"C{n:02d}" for n in range(1, 23))
POLICY_CONTEXT_ONLY = ("C05", "C06", "C08", "C09", "C10", "C15", "C21", "C22")
EDITION_LABEL = (
    "редакция локального корпуса (ConsultantPlus), "
    "изменения не сверены с официальной редакцией"
)
PROJECT_DATE = "не задана: бета на синтетических документах (R-146bb)"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
BUILD = "bge-m3-dense-v1:characters-v2:1200"
ZERO = "0" * 64
TEXT_LIMIT = 2_000
QUERY_LIMIT = 1_200
SHA = re.compile(r"[0-9a-f]{64}")
# Wording that would assert currency or a human check; the edition label's own negation is
# removed before the search, so «не сверены с официальной редакцией» stays allowed.
CURRENCY = re.compile(r"актуальн|действующ|в силе|утверждён|проверено по|сверено с")
TARGET_KEYS = {
    "norm_document_id", "designation", "edition", "kind", "ordinal_first", "ordinal_last",
    "norm_paragraph_id_first", "norm_paragraph_id_last",
}
KIND_RULE = {"C07": "range", "C21": "table", "C22": "table"}
# The query texts carry no number and no norm designator (the digit test catches clause numbers).
DESIGNATORS = re.compile(
    r"\b(СП|ГОСТ|ФЗ|СНиП|СанПиН|пункт(?:а|е|у|ом|ы|ов)?|стать(?:я|и|е|ю|ёй)|раздел(?:а|е|у|ом|ы|ов)?)\b", re.I)


def _load(name: str) -> Any:
    return json.loads((BETA / name).read_text(encoding="utf-8"))


def _text_ok(value: object, limit: int = TEXT_LIMIT) -> bool:
    return (isinstance(value, str) and bool(value) and len(value) <= limit
            and unicodedata.normalize("NFC", value) == value and value == value.strip())


def _walk_strings(node: object):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_strings(value)


def vector_state(doc: dict[str, Any]) -> str:
    """``placeholder`` (six zero digests), ``final`` (six distinct real digests) or ``mixed``."""
    digests = list(doc["query_vectors"]["sha256_by_scope"].values())
    if all(d == ZERO for d in digests):
        return "placeholder"
    if all(isinstance(d, str) and SHA.fullmatch(d) and d != ZERO for d in digests) \
            and len(set(digests)) == len(digests):
        return "final"
    return "mixed"


def decision_problems(doc: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    policy = load_beta_source_policy()
    proposal = _load("spans.proposal.json")
    if set(doc) != {"decision_version", "synthetic", "comment", "identity", "query_vectors", "items"}:
        problems.append("top_level_keys")
    if "review" in doc:
        problems.append("review_block_present")
    if doc.get("decision_version") != map_pack.DECISIONS_VERSION:
        problems.append("decision_version")
    if doc.get("synthetic") is not False:
        problems.append("synthetic_flag_not_false")
    if not _text_ok(doc.get("comment")):
        problems.append("comment_text")
    if doc.get("identity") != {
        "norms_snapshot_id": policy.snapshot_id,
        "reviewed_content_key": "2026-07-23..2026-08-20+17d+121r.0a1bafe103ff",
        "embedding_build": BUILD,
        "scenario": policy.scenario,
    }:
        problems.append("identity_differs")
    vectors = doc.get("query_vectors", {})
    if vectors.get("profile") != EMBEDDING_PROFILE or vectors.get("model_revision") != MODEL_REVISION:
        problems.append("query_vector_profile_or_revision")
    if tuple(vectors.get("sha256_by_scope", {})) != SCOPES:
        problems.append("query_vector_scopes")
    else:
        state = vector_state(doc)
        if state == "mixed":
            problems.append("vector_digests_mixed")
        if ("PLACEHOLDER" in doc.get("comment", "")) != (state == "placeholder"):
            problems.append("placeholder_marker_mismatch")

    items = doc.get("items", [])
    if [item.get("id") for item in items] != list(ITEM_IDS):
        problems.append("items_not_c01_to_c22_in_order")
        return problems
    modes = {item["id"]: item.get("mode") for item in items}
    context = tuple(i for i in ITEM_IDS if modes[i] == "context_only")
    provisional = tuple(i for i in ITEM_IDS if modes[i] == "provisional_citation")
    if context != POLICY_CONTEXT_ONLY or len(provisional) != 14:
        problems.append("mode_split_differs_from_policy")
    span_of = {
        item["id"]: [(c["norm_document_id"], c["ordinal_first"], c["ordinal_last"])
                     for c in item["candidates"]]
        for item in proposal["items"]
    }
    seen_targets: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["id"]
        has_citation = {"branch", "edition_evidence"} & set(item)
        if modes[item_id] == "context_only":
            if has_citation or set(item) != {"id", "mode", "targets"}:
                problems.append("context_only_carries_citation")
        else:
            if set(item) != {"id", "mode", "targets", "branch", "edition_evidence"}:
                problems.append("provisional_keys")
                continue
            if item["edition_evidence"] != []:
                problems.append("edition_evidence_not_empty")
            branch = item["branch"]
            if set(branch) != {"id", "applicability"} or branch["id"] != "N":
                problems.append("branch_id_not_n")
            if not _text_ok(branch.get("applicability")):
                problems.append("applicability_text")
            elif PROJECT_DATE not in branch["applicability"]:
                problems.append("project_date_not_stated")
        targets = item["targets"]
        if not isinstance(targets, list) or not targets:
            problems.append("targets_not_single")
            continue
        keys = [(t.get("norm_document_id"), t.get("ordinal_first"), t.get("ordinal_last"))
                for t in targets]
        if keys != sorted(set(keys)):
            problems.append("targets_not_sorted_unique")
        if len(targets) != 1:
            problems.append("targets_not_single")
            continue
        target = targets[0]
        seen_targets[item_id] = target
        if set(target) != TARGET_KEYS:
            problems.append("target_keys")
            continue
        for field in ("designation", "edition"):
            if not _text_ok(target[field]):
                problems.append("text_not_nfc_or_blank_or_long")
        if target["edition"] != EDITION_LABEL:
            problems.append("edition_label_differs")
        if target["kind"] != KIND_RULE.get(item_id, "clause"):
            problems.append("kind_differs_from_rule")
        first, last = target["ordinal_first"], target["ordinal_last"]
        if type(first) is not int or type(last) is not int or first < 0 or last < first:
            problems.append("ordinals_invalid")
        try:
            NormDocumentId.parse(target["norm_document_id"])
            NormParagraphId.parse(target["norm_paragraph_id_first"])
            NormParagraphId.parse(target["norm_paragraph_id_last"])
        except (TypeError, ValueError):
            problems.append("identity_invalid")
        if (first == last) != (target["norm_paragraph_id_first"] == target["norm_paragraph_id_last"]):
            problems.append("single_paragraph_ids_differ")
        wanted = span_of[item_id]
        if item_id == "C22":  # the choice recorded in the report: 289-300, a proposal candidate
            wanted = [w for w in wanted if (w[1], w[2]) == (289, 300)]
        if [(target["norm_document_id"], first, last)] != wanted:
            problems.append("span_differs_from_spans_proposal")
    for repeated, original in (("C13", "C12"), ("C20", "C19"), ("C22", "C21")):
        if seen_targets.get(repeated) != seen_targets.get(original):
            problems.append("duplicated_span_not_kept")
    # No sentence may claim currency or a human check; the label's own negation is allowed.
    for text in _walk_strings(doc["items"]):
        if CURRENCY.search(text.replace(EDITION_LABEL, "").lower()):
            problems.append("currency_claim")
        if "официальн" in text.replace(EDITION_LABEL, "").lower():
            problems.append("official_source_mention")
    return sorted(set(problems), key=problems.index)


def query_problems(doc: dict[str, Any], decisions: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    queries = doc.get("queries", [])
    if [q.get("item_id") for q in queries] != list(ITEM_IDS):
        return ["queries_not_c01_to_c22_in_order"]
    scope_of = {i: s for s in SCOPES for i in scope_membership(s).item_ids}
    texts = [q["text"] for q in queries]
    if len(set(texts)) != len(texts):
        problems.append("texts_not_distinct")
    if len({q["topic_label"] for q in queries}) != len(queries):
        problems.append("topic_labels_not_distinct")
    for query in queries:
        if set(query) != {"item_id", "scope_id", "topic_label", "text", "characters", "query_text_sha256"}:
            problems.append("query_keys")
            continue
        if query["scope_id"] != scope_of[query["item_id"]]:
            problems.append("scope_differs_from_membership")
        text = query["text"]
        if not _text_ok(text, QUERY_LIMIT) or not _text_ok(query["topic_label"], 200):
            problems.append("text_not_nfc_or_blank_or_long")
            continue
        if re.search(r"\d", text) or DESIGNATORS.search(text):
            problems.append("number_or_designator_in_text")
        if re.search(r"https?:", text):
            problems.append("url_in_text")
        if query["characters"] != len(text):
            problems.append("characters_differs")
        if query["query_text_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest():
            problems.append("digest_differs")
    rule = doc.get("length_rule", {})
    lengths = [len(q["text"]) for q in queries]
    if rule.get("longest_text_characters") != max(lengths) or rule.get("shortest_text_characters") != min(lengths):
        problems.append("length_rule_differs")
    if rule.get("worst_case_inference_tokens_of_longest") != max(lengths) + 2 \
            or max(lengths) + 2 > rule.get("limit_inference_tokens", 0):
        problems.append("token_bound_differs_or_over_limit")
    return sorted(set(problems), key=problems.index)


def scopes_problems(spec: dict[str, Any], decisions: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if set(spec) != {"analysis_profile_id", "prompt_bundle_id", "scopes"}:
        return ["spec_keys"]
    if spec["analysis_profile_id"] != str(PROFILE_ID) or spec["prompt_bundle_id"] != str(PROMPT_BUNDLE_ID):
        problems.append("profile_or_bundle_differs_from_code")
    scopes = spec["scopes"]
    if [s.get("scope_id") for s in scopes] != list(SCOPES):
        return problems + ["scope_order"]
    identity = decisions["identity"]
    for scope in scopes:
        if set(scope) != {"scope_id", "map_sha256", "snapshot_id", "reviewed_content_key",
                          "embedding_build", "builder_version", "chunking_profile"}:
            problems.append("scope_keys")
            continue
        if (scope["snapshot_id"], scope["reviewed_content_key"], scope["embedding_build"]) != (
                identity["norms_snapshot_id"], identity["reviewed_content_key"], identity["embedding_build"]):
            problems.append("scope_identity_differs_from_decisions")
        if scope["builder_version"] != SET_BUILDER_VERSION:
            problems.append("builder_version_differs_from_code")
        if scope["embedding_build"] != f"{EMBEDDING_PROFILE}:{scope['chunking_profile']}":
            problems.append("embedding_build_differs_from_chunking_profile")
    return sorted(set(problems), key=problems.index)


def scopes_state(spec: dict[str, Any]) -> str:
    digests = [s["map_sha256"] for s in spec["scopes"]]
    if all(isinstance(d, str) and d.startswith("PLACEHOLDER") for d in digests):
        return "placeholder"
    if all(SHA.fullmatch(d) for d in digests) and len(set(digests)) == len(digests):
        return "final"
    return "mixed"


# ------------------------------------------------------------------ the committed files

def test_decisions_file_has_no_problem() -> None:
    assert decision_problems(_load("decisions.json")) == []


def test_there_are_22_distinct_items_14_provisional_and_the_8_policy_items_context_only() -> None:
    doc = _load("decisions.json")
    ids = [item["id"] for item in doc["items"]]
    assert ids == list(ITEM_IDS) and len(set(ids)) == 22
    by_mode = {mode: [i["id"] for i in doc["items"] if i["mode"] == mode]
               for mode in ("provisional_citation", "context_only")}
    assert tuple(by_mode["context_only"]) == POLICY_CONTEXT_ONLY
    assert len(by_mode["provisional_citation"]) == 14
    assert set(by_mode["provisional_citation"]).isdisjoint(POLICY_CONTEXT_ONLY)


def test_targets_are_sorted_unique_and_every_text_is_nfc_and_short() -> None:
    doc = _load("decisions.json")
    for item in doc["items"]:
        keys = [(t["norm_document_id"], t["ordinal_first"], t["ordinal_last"]) for t in item["targets"]]
        assert keys == sorted(set(keys)), item["id"]
    for text in _walk_strings(doc):
        assert unicodedata.normalize("NFC", text) == text
        assert len(text) <= TEXT_LIMIT


def test_the_real_map_tool_accepts_the_decisions_and_builds_six_distinct_maps() -> None:
    maps = map_pack.build_scope_maps(map_pack.parse_decisions((BETA / "decisions.json").read_bytes()))
    assert [m.scope_id for m in maps.maps] == list(SCOPES)
    assert len({m.sha256 for m in maps.maps}) == 6
    assert maps.review is None  # the summary will say pending_expert


def test_the_beta_policy_still_has_the_ordered_split() -> None:
    """The split above is hard-coded from the integrator's order; a policy change must show here."""
    modes = {item.item_id: item.mode for item in load_beta_source_policy().items}
    assert tuple(i for i, m in modes.items() if m == "context_only") == POLICY_CONTEXT_ONLY
    assert sum(m == "provisional_citation" for m in modes.values()) == 14


def test_the_vector_placeholder_is_wholly_present_and_marked_or_wholly_replaced() -> None:
    doc = _load("decisions.json")
    assert vector_state(doc) in {"placeholder", "final"}
    assert ("PLACEHOLDER" in doc["comment"]) == (vector_state(doc) == "placeholder")


def test_query_texts_file_has_no_problem() -> None:
    assert query_problems(_load("query-texts.json"), _load("decisions.json")) == []


def test_query_texts_are_short_without_digits_and_their_digest_is_the_nfc_utf8_sha256() -> None:
    doc = _load("query-texts.json")
    assert len(doc["queries"]) == 22
    for query in doc["queries"]:
        text = query["text"]
        assert unicodedata.normalize("NFC", text) == text
        assert 0 < len(text) <= QUERY_LIMIT
        assert not re.search(r"\d", text)
        assert query["query_text_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_scopes_skeleton_has_no_problem_and_the_scope_definitions_match_the_code() -> None:
    decisions = _load("decisions.json")
    assert scopes_problems(_load("scopes.json"), decisions) == []
    definitions = _load("scope-definitions.json")
    assert [s["scope_id"] for s in definitions["scopes"]] == list(SCOPES)
    modes = {i["id"]: i["mode"] for i in decisions["items"]}
    for scope in definitions["scopes"]:
        membership = scope_membership(scope["scope_id"])
        assert tuple(scope["item_ids"]) == membership.item_ids
        assert definitions["composition_sha256"] == membership.composition_sha256
        assert scope["provisional_citation_item_ids"] == [
            i for i in scope["item_ids"] if modes[i] == "provisional_citation"]
        assert scope["context_only_item_ids"] == [
            i for i in scope["item_ids"] if modes[i] == "context_only"]


def test_the_real_seal_reader_refuses_the_skeleton_for_its_placeholders_only(tmp_path: Path) -> None:
    spec = _load("scopes.json")
    assert scopes_state(spec) == "placeholder"
    path = tmp_path / "scopes.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(PackManifestRefused) as refused:
        v3_pack_cli._read_spec(str(path))
    assert refused.value.reason == "spec_value"  # a map digest that is not lowercase SHA-256
    for index, scope in enumerate(spec["scopes"]):  # six distinct real-looking digests
        scope["map_sha256"] = f"{index + 1:x}" * 64
    path.write_text(json.dumps(spec), encoding="utf-8")
    profile_id, bundle_id, scopes = v3_pack_cli._read_spec(str(path))
    assert (profile_id, bundle_id, len(scopes)) == (str(PROFILE_ID), str(PROMPT_BUNDLE_ID), 6)


@pytest.mark.skipif(os.environ.get("AR_V3_DECISIONS_REQUIRE_FINAL") != "1",
                    reason="final state is required only before sealing")
def test_final_state_has_no_placeholder_left() -> None:
    assert vector_state(_load("decisions.json")) == "final"
    assert scopes_state(_load("scopes.json")) == "final"


# ------------------------------------------------------------------ every guard can fail

def _set(path: tuple[Any, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(doc: dict[str, Any]) -> None:
        node = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return apply


def _item(doc: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(item for item in doc["items"] if item["id"] == item_id)


def _upgrade_c05(doc: dict[str, Any]) -> None:
    item = _item(doc, "C05")
    item["mode"] = "provisional_citation"
    item["branch"] = {"id": "N", "applicability": "x " + PROJECT_DATE}
    item["edition_evidence"] = []


def _downgrade_c01(doc: dict[str, Any]) -> None:
    item = _item(doc, "C01")
    item["mode"] = "context_only"
    del item["branch"], item["edition_evidence"]


def _duplicate_target(doc: dict[str, Any]) -> None:
    item = _item(doc, "C01")
    item["targets"].append(copy.deepcopy(item["targets"][0]))


def _decomposed(doc: dict[str, Any]) -> None:
    _item(doc, "C02")["targets"][0]["designation"] = unicodedata.normalize("NFD", "СП й")


def _move_c13(doc: dict[str, Any]) -> None:
    _item(doc, "C13")["targets"][0]["norm_paragraph_id_first"] = _item(doc, "C14")["targets"][0]["norm_paragraph_id_first"]


DECISION_MUTATIONS: dict[str, tuple[Callable[[dict[str, Any]], None], str]] = {
    "item_missing": (lambda d: d["items"].pop(21), "items_not_c01_to_c22_in_order"),
    "item_duplicated": (lambda d: d["items"].__setitem__(21, copy.deepcopy(d["items"][20])),
                        "items_not_c01_to_c22_in_order"),
    "policy_item_upgraded": (_upgrade_c05, "mode_split_differs_from_policy"),
    "provisional_item_downgraded": (_downgrade_c01, "mode_split_differs_from_policy"),
    "context_only_carries_branch": (
        lambda d: _item(d, "C06").__setitem__("branch", {"id": "N", "applicability": "x"}),
        "context_only_carries_citation"),
    "evidence_not_empty": (
        lambda d: _item(d, "C01").__setitem__("edition_evidence", [{"source_id": "D1_MCHS_1"}]),
        "edition_evidence_not_empty"),
    "branch_is_not_n": (lambda d: _item(d, "C01")["branch"].__setitem__("id", "R"), "branch_id_not_n"),
    "project_date_missing": (
        lambda d: _item(d, "C01")["branch"].__setitem__("applicability", "Применимо."),
        "project_date_not_stated"),
    "targets_duplicated": (_duplicate_target, "targets_not_sorted_unique"),
    "text_not_nfc": (_decomposed, "text_not_nfc_or_blank_or_long"),
    "text_too_long": (
        lambda d: _item(d, "C01")["targets"][0].__setitem__("designation", "я" * 2001),
        "text_not_nfc_or_blank_or_long"),
    "text_blank": (lambda d: _item(d, "C01")["targets"][0].__setitem__("edition", ""),
                   "text_not_nfc_or_blank_or_long"),
    "edition_label_changed": (
        lambda d: _item(d, "C01")["targets"][0].__setitem__("edition", "редакция 2020"),
        "edition_label_differs"),
    "span_moved": (lambda d: _item(d, "C01")["targets"][0].__setitem__("ordinal_last", 138),
                   "span_differs_from_spans_proposal"),
    "c22_takes_the_other_candidate": (
        lambda d: _item(d, "C22")["targets"][0].update(ordinal_first=301, ordinal_last=308),
        "span_differs_from_spans_proposal"),
    "duplicated_span_diverges": (_move_c13, "duplicated_span_not_kept"),
    "paragraph_id_malformed": (
        lambda d: _item(d, "C01")["targets"][0].__setitem__("norm_paragraph_id_first", "npar_x"),
        "identity_invalid"),
    "one_paragraph_span_with_two_ids": (
        lambda d: _item(d, "C07")["targets"][0].__setitem__(
            "norm_paragraph_id_last", _item(d, "C01")["targets"][0]["norm_paragraph_id_last"]),
        "single_paragraph_ids_differ"),
    "kind_changed": (lambda d: _item(d, "C07")["targets"][0].__setitem__("kind", "clause"),
                     "kind_differs_from_rule"),
    "review_block_added": (lambda d: d.__setitem__("review", {}), "review_block_present"),
    "synthetic_true": (_set(("synthetic",), True), "synthetic_flag_not_false"),
    "snapshot_changed": (_set(("identity", "norms_snapshot_id"), "ns_01M4ZW72BS7QHAMDJ993VHNJ7K"),
                         "identity_differs"),
    "model_revision_changed": (_set(("query_vectors", "model_revision"), "0" * 40),
                               "query_vector_profile_or_revision"),
    # The file is final since the vectors exist (2026-10-27): the placeholder state is entered by the
    # mutation, so each case fails whichever of the two states the stored file is in.
    "vector_digests_mixed": (_set(("query_vectors", "sha256_by_scope", "F1"), "0" * 64),
                             "vector_digests_mixed"),
    "placeholder_left_unmarked": (
        lambda d: (d["query_vectors"]["sha256_by_scope"].update({s: "0" * 64 for s in SCOPES}),
                   d.__setitem__("comment", "Decisions without the marker word.")),
        "placeholder_marker_mismatch"),
    "marker_left_on_final_vectors": (
        lambda d: d.__setitem__("comment", d["comment"] + " PLACEHOLDER: not final."),
        "placeholder_marker_mismatch"),
    "currency_claimed": (
        lambda d: _item(d, "C01")["branch"].__setitem__(
            "applicability", PROJECT_DATE + "; редакция актуальна"),
        "currency_claim"),
    "official_check_claimed": (
        lambda d: _item(d, "C01")["branch"].__setitem__(
            "applicability", PROJECT_DATE + "; сверено с официальным источником"),
        "currency_claim"),
}


@pytest.mark.parametrize("name", sorted(DECISION_MUTATIONS))
def test_each_decision_guard_fails_under_its_mutation(name: str) -> None:
    mutate, code = DECISION_MUTATIONS[name]
    doc = copy.deepcopy(_load("decisions.json"))
    mutate(doc)
    assert code in decision_problems(doc), name


def _query(doc: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(q for q in doc["queries"] if q["item_id"] == item_id)


QUERY_MUTATIONS: dict[str, tuple[Callable[[dict[str, Any]], None], str]] = {
    "query_missing": (lambda d: d["queries"].pop(), "queries_not_c01_to_c22_in_order"),
    "digit_in_text": (lambda d: _query(d, "C01").update(text=_query(d, "C01")["text"] + " 2"),
                      "number_or_designator_in_text"),
    "designator_in_text": (lambda d: _query(d, "C01").update(text=_query(d, "C01")["text"] + " по СП"),
                           "number_or_designator_in_text"),
    "text_too_long": (lambda d: _query(d, "C01").update(text="я" * 1201), "text_not_nfc_or_blank_or_long"),
    "text_not_nfc": (lambda d: _query(d, "C01").update(text=unicodedata.normalize("NFD", "йй")),
                     "text_not_nfc_or_blank_or_long"),
    "digest_stale": (lambda d: _query(d, "C01").update(query_text_sha256=ZERO), "digest_differs"),
    "length_stale": (lambda d: _query(d, "C01").update(characters=1), "characters_differs"),
    "wrong_scope": (lambda d: _query(d, "C01").update(scope_id="S2"), "scope_differs_from_membership"),
    "texts_equal": (lambda d: _query(d, "C02").update(text=_query(d, "C01")["text"]), "texts_not_distinct"),
    "token_bound_stale": (lambda d: d["length_rule"].update(worst_case_inference_tokens_of_longest=1),
                          "token_bound_differs_or_over_limit"),
}


@pytest.mark.parametrize("name", sorted(QUERY_MUTATIONS))
def test_each_query_guard_fails_under_its_mutation(name: str) -> None:
    mutate, code = QUERY_MUTATIONS[name]
    doc = copy.deepcopy(_load("query-texts.json"))
    mutate(doc)
    assert code in query_problems(doc, _load("decisions.json")), name


SCOPES_MUTATIONS: dict[str, tuple[Callable[[dict[str, Any]], None], str]] = {
    "profile_changed": (lambda d: d.update(analysis_profile_id="ap_x"), "profile_or_bundle_differs_from_code"),
    "scope_order": (lambda d: d["scopes"].reverse(), "scope_order"),
    "builder_changed": (lambda d: d["scopes"][0].update(builder_version="norm-retrieval-set-prep-v0"),
                        "builder_version_differs_from_code"),
    "build_without_chunking": (lambda d: d["scopes"][0].update(chunking_profile="characters-v2:1000"),
                               "embedding_build_differs_from_chunking_profile"),
    "snapshot_changed": (lambda d: d["scopes"][0].update(snapshot_id="ns_x"),
                         "scope_identity_differs_from_decisions"),
    "extra_key": (lambda d: d.update(extra=1), "spec_keys"),
}


@pytest.mark.parametrize("name", sorted(SCOPES_MUTATIONS))
def test_each_scopes_guard_fails_under_its_mutation(name: str) -> None:
    mutate, code = SCOPES_MUTATIONS[name]
    spec = copy.deepcopy(_load("scopes.json"))
    mutate(spec)
    assert code in scopes_problems(spec, _load("decisions.json")), name
