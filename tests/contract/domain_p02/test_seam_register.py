"""`docs/program/P02_SEAMS.md` declares a producer and a consumer for every seam.

This is the Gate A gate for `A1b`: "a test asserts every declared stage-artifact
shape has a named producer and consumer". A shape with no producer is a promise
nobody keeps; a shape with no consumer is work nobody needs, and both are cheap to
find here and expensive to find at the Gate B convergence.

The tables the tests read are the same tables a reader reads. Duplicating them into a
JSON block would create two descriptions that drift.
"""

from __future__ import annotations

import re

import pytest

SESSION_PATTERN = re.compile(r"\b[AB][1-9][a-z]?\b")

#: The stages PC-01 executes, and therefore the artifacts that must have an owner.
PC01_STAGES = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
)


@pytest.fixture(scope="session")
def seam_rows(seam_register_text: str, markdown_table) -> list[dict[str, str]]:
    return markdown_table(seam_register_text, "What crosses it")


@pytest.fixture(scope="session")
def artifact_rows(seam_register_text: str, markdown_table) -> list[dict[str, str]]:
    return markdown_table(seam_register_text, "Artifact role")


# ---------------------------------------------------------------------------
# The seam register
# ---------------------------------------------------------------------------


def test_the_seam_register_carries_every_declared_seam(seam_rows) -> None:
    seams = {row["Seam"] for row in seam_rows}
    assert {f"S{index}" for index in range(1, 14)} <= seams


def test_every_seam_names_a_producer_and_at_least_one_consumer(seam_rows) -> None:
    for row in seam_rows:
        seam = row["Seam"]
        assert row["What crosses it"].strip(), f"{seam} declares no payload"
        producers = SESSION_PATTERN.findall(row["Producer"])
        consumers = SESSION_PATTERN.findall(row["Consumers"])
        assert producers, f"{seam} has no named producer: {row['Producer']!r}"
        assert consumers, f"{seam} has no named consumer: {row['Consumers']!r}"


def test_no_seam_is_produced_and_consumed_only_by_its_own_producer(seam_rows) -> None:
    """A seam nobody else crosses is not a seam."""
    for row in seam_rows:
        producers = set(SESSION_PATTERN.findall(row["Producer"]))
        consumers = set(SESSION_PATTERN.findall(row["Consumers"]))
        assert consumers - producers, f"{row['Seam']} is only consumed by its producer"


def test_the_gate_a_sessions_own_the_seams_gate_b_consumes(seam_rows) -> None:
    """S8, S10, S11 and S12 are Gate A deliverables; a Gate B producer is a defect."""
    by_seam = {row["Seam"]: row for row in seam_rows}
    for seam in ("S8", "S10", "S11", "S12"):
        producers = SESSION_PATTERN.findall(by_seam[seam]["Producer"])
        assert all(producer.startswith("A") for producer in producers), (
            f"{seam} is produced by {producers}; it is frozen at Gate A"
        )


# ---------------------------------------------------------------------------
# The stage-artifact shapes
# ---------------------------------------------------------------------------


def test_every_pc01_produced_output_is_declared(
    artifact_rows, stage_registry_contract: dict
) -> None:
    """Nothing a PC-01 stage produces may be missing from the register."""
    declared = {row["Artifact role"].strip("`") for row in artifact_rows}
    required = {
        output["role"]
        for stage in stage_registry_contract["stages"]
        if stage["stage_id"] in PC01_STAGES
        for output in stage["produced_outputs"]
    }
    missing = required - declared
    assert missing == set(), f"stage outputs with no declared shape: {sorted(missing)}"


def test_every_pc01_required_input_is_produced_by_a_declared_shape(
    artifact_rows, stage_registry_contract: dict
) -> None:
    """And nothing a PC-01 stage consumes may be unaccounted for."""
    declared = {row["Artifact role"].strip("`") for row in artifact_rows}
    for stage in stage_registry_contract["stages"]:
        if stage["stage_id"] not in PC01_STAGES:
            continue
        for required_input in stage["required_inputs"]:
            if not required_input["required"]:
                continue
            role = required_input["role"]
            if role.startswith("source."):
                continue  # ingest input, seam S1/S2, not a stage artifact
            assert role in declared, f"{stage['stage_id']} requires undeclared {role}"


def test_every_artifact_shape_names_a_producer(artifact_rows) -> None:
    for row in artifact_rows:
        role = row["Artifact role"]
        assert SESSION_PATTERN.findall(row["Produced by"]), (
            f"{role} has no named producer: {row['Produced by']!r}"
        )


def test_every_artifact_shape_names_a_consumer_or_declares_it_has_none(
    artifact_rows,
) -> None:
    """A shape with no consumer must say so, and say under which decision.

    `geometry.page_crops` is the one such case: the registry marks it a required
    output of a stage that allows neither `partial` nor `skipped`, while its only
    contract consumer, `block_analysis`, is out of PC-01 scope. `OD-04` resolves it
    with a declared empty manifest. That is a recorded decision, not a gap - and this
    test is what keeps the difference visible.
    """
    for row in artifact_rows:
        role = row["Artifact role"]
        consumers = row["Consumed by"]
        assert consumers.strip(), f"{role} declares nothing about its consumers"
        if SESSION_PATTERN.findall(consumers):
            continue
        assert "none" in consumers.lower(), f"{role} has no consumer and does not say so"
        assert re.search(r"OD-\d+", consumers), (
            f"{role} has no consumer and cites no owner decision: {consumers!r}"
        )


def test_every_artifact_shape_points_at_its_section(artifact_rows) -> None:
    for row in artifact_rows:
        section = next(value for key, value in row.items() if key.strip() == "§")
        assert re.fullmatch(r"4\.\d", section.strip()), (
            f"{row['Artifact role']} points at section {section!r}"
        )


def test_each_declared_shape_has_a_body_in_section_4(
    artifact_rows, seam_register_text: str
) -> None:
    """The table may not point at a section that does not exist."""
    for row in artifact_rows:
        role = row["Artifact role"].strip("`")
        section = next(value for key, value in row.items() if key.strip() == "§").strip()
        heading = f"### {section} `{role}`"
        assert heading in seam_register_text, f"no body for {role} at {heading!r}"
        body = seam_register_text.split(heading, 1)[1]
        assert f'"artifact_role": "{role}"' in body.split("\n### ")[0], (
            f"{role}'s example does not declare its own artifact_role"
        )


def test_the_offset_rule_is_stated_once_and_unambiguously(seam_register_text: str) -> None:
    """The most expensive thing in this document to get wrong.

    Whitespace is collapsed first: the document is hard-wrapped prose, so a phrase
    that happens to straddle a line break must still count as present.
    """
    flat = " ".join(seam_register_text.split())
    for phrase in (
        "Unicode code points",
        "no separator inserted between pages",
        "Not bytes. Not UTF-16 code units.",
        "No later stage normalizes again",
        "compares exactly, after that one declared normalization and nothing else",
    ):
        assert phrase in flat, f"the offset rule does not state {phrase!r}"


# ---------------------------------------------------------------------------
# The CSV column contract
# ---------------------------------------------------------------------------


def test_the_csv_column_contract_is_frozen_in_order(
    seam_register_text: str, markdown_table
) -> None:
    rows = markdown_table(seam_register_text, "| # | Column | Source |")
    columns = [row["Column"].strip("`") for row in rows]
    assert columns == [
        "project_uid",
        "document_uid",
        "version_uid",
        "run_id",
        "run_state",
        "provider_mode",
        "finding_uid",
        "finding_observation_id",
        "category",
        "finding_text",
        "recommendation_text",
        "evidence_page",
        "evidence_quote",
        "current_verdict",
        "latest_comment",
        "latest_decision_id",
        "decision_recorded_at",
    ]
    assert [row["#"] for row in rows] == [str(index) for index in range(1, 18)]


def test_every_csv_column_names_its_source(seam_register_text: str, markdown_table) -> None:
    for row in markdown_table(seam_register_text, "| # | Column | Source |"):
        assert row["Source"].strip(), f"{row['Column']} has no declared source"


def test_the_od11_byte_decisions_are_all_recorded(seam_register_text: str) -> None:
    for decision in (
        "UTF-8 with a byte-order mark",
        "comma delimiter",
        "CRLF",
        "RFC 4180",
        "byte-identical",
    ):
        assert decision in seam_register_text, f"OD-11 does not record {decision!r}"


def test_the_export_policy_switches_on_publishes_result(seam_register_text: str) -> None:
    assert "publishes_result" in seam_register_text
    assert "not a hand-written state list" in seam_register_text


# ---------------------------------------------------------------------------
# What PC-01 does not claim
# ---------------------------------------------------------------------------


def test_the_unallocated_identifiers_are_recorded(seam_register_text: str) -> None:
    from auditmanager.shared.identity import UNALLOCATED_IN_PC01

    section = seam_register_text.split("### 9.1")[1].split("### 9.2")[0]
    for identifier in UNALLOCATED_IN_PC01:
        assert f"`{identifier}`" in section, f"{identifier} is not recorded as unallocated"


def test_the_unevaluated_guards_are_recorded(seam_register_text: str) -> None:
    section = seam_register_text.split("### 9.2")[1].split("### 9.3")[0]
    assert "OD-24" in seam_register_text.split("### 9.2")[0][-400:] or "OD-24" in section
    for clause in ("NormsSnapshot", "queued → running", "running → validating", "ResultPackage"):
        assert clause in section, f"{clause} is not recorded as unevaluated"
    assert "asserts these guards **absent**" in section


def test_the_error_codes_without_a_producer_are_recorded(
    seam_register_text: str,
) -> None:
    section = seam_register_text.split("### 9.4")[1].split("## 10.")[0]
    for code in (
        "execution_token_invalid",
        "stale_attempt",
        "partial_result_not_publishable",
        "required_norm_unavailable",
        "unsupported_contract_version",
    ):
        assert code in section, f"{code} has no producer and is not recorded"


def test_the_api_operation_table_matches_the_frozen_document(
    seam_register_text: str, markdown_table, openapi_document: dict
) -> None:
    """The register and the document cannot describe different surfaces."""
    rows = markdown_table(seam_register_text, "Method and path")
    documented = set()
    for path, item in openapi_document["paths"].items():
        for method, operation in item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                documented.add((operation["operationId"], f"{method.upper()} {path}"))
    registered = {
        (row["Operation"].strip("`"), row["Method and path"].strip("`")) for row in rows
    }
    assert registered == documented
