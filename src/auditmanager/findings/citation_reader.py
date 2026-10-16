"""Unserved, fail-closed read of 0023's certified citation partitions.

The caller supplies the registered v3 profile identity and holds one consistent
database read transaction. This module returns persisted facts for a later
report assembler; it does not authorize a route or infer a certified zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


class CitationReadRefused(ValueError):
    """The requested run or its persisted citation proof is unavailable."""


@dataclass(frozen=True, slots=True)
class VerifiedCitation:
    citation_ordinal: int
    norms_snapshot_id: str
    norm_document_id: str
    norm_paragraph_id: str
    designation: str
    title: str
    clause_number: str | None
    page_label: int
    quote: str
    state: str
    source_attribution: str


@dataclass(frozen=True, slots=True)
class VerifiedObservationPartition:
    finding_observation_id: str
    citation_count: int
    citations: tuple[VerifiedCitation, ...]
    required_value: str | None
    stated_value: str | None


@dataclass(frozen=True, slots=True)
class VerifiedFindingPartitions:
    finding_uid: str
    canonical: VerifiedObservationPartition
    merged_observations: tuple[VerifiedObservationPartition, ...]


@dataclass(frozen=True, slots=True)
class VerifiedCitationRead:
    run_id: str
    project_uid: str
    version_uid: str
    norms_snapshot_id: str
    norm_retrieval_set_id: str
    run_state: str
    findings: tuple[VerifiedFindingPartitions, ...]


_HEADER = text("""
    SELECT r.run_id, r.project_uid, r.version_uid, r.analysis_profile_id,
           r.prompt_bundle_id, r.provider_mode, r.norms_snapshot_id,
           r.norm_retrieval_set_id, r.state AS run_state,
           s.state AS set_state, s.expected_set_sha256, s.observed_set_sha256,
           s.reviewed_content_key, ns.content_key AS snapshot_content_key,
           s.expected_catalogue_sha256, s.observed_catalogue_sha256,
           st.status AS cite_status,
           (SELECT count(*) FROM norm_custody_binding cb JOIN blob b
              ON b.blob_id = cb.blob_id
             WHERE cb.target_kind = 'norm_retrieval_set'
               AND cb.target_id = s.norm_retrieval_set_id
               AND cb.role = 'norm_retrieval_set'
               AND cb.blob_id = s.set_blob_id AND b.state = 'available'
               AND b.sha256 = s.observed_set_sha256
               AND b.size_bytes = s.set_size_bytes) AS set_binding_count,
           (SELECT count(*) FROM norm_custody_binding cb JOIN blob b
              ON b.blob_id = cb.blob_id
             WHERE cb.target_kind = 'norm_retrieval_set'
               AND cb.target_id = s.norm_retrieval_set_id
               AND cb.role = 'norm_catalogue'
               AND cb.blob_id = s.catalogue_blob_id AND b.state = 'available'
               AND b.sha256 = s.observed_catalogue_sha256
               AND b.size_bytes = s.catalogue_size_bytes) AS catalogue_binding_count
      FROM audit_run r
      JOIN norm_retrieval_set s
        ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
       AND s.norms_snapshot_id = r.norms_snapshot_id
      JOIN norms_snapshot ns ON ns.norms_snapshot_id = r.norms_snapshot_id
      JOIN stage_result st ON st.run_id = r.run_id
       AND st.stage_id = 'norm_verification'
     WHERE r.run_id = :run_id AND r.version_uid = :version_uid
       AND r.analysis_profile_id = :profile_id
""")

_OBSERVATIONS = text("""
    SELECT f.finding_uid, f.project_uid, f.version_uid,
           f.canonical_observation_id,
           o.finding_observation_id, o.run_id AS observation_run_id,
           o.finding_uid AS observation_finding_uid,
           o.stage_id, o.grounded, o.category, o.analysis_profile_id,
           o.prompt_bundle_id, o.provider_mode, o.norm_citation_count,
           o.required_value, o.stated_value
      FROM finding f LEFT JOIN finding_observation o
        ON o.finding_uid = f.finding_uid
     WHERE f.allocated_by_run_id = :run_id
     ORDER BY f.finding_uid COLLATE "C", o.finding_observation_id COLLATE "C"
""")

_CITATIONS = text("""
    SELECT c.finding_observation_id, c.citation_ordinal, c.run_id,
           c.norms_snapshot_id, c.norm_retrieval_set_id,
           c.norm_document_id, c.norm_paragraph_id, c.quote, c.char_start,
           c.char_length, c.state, d.norms_snapshot_id AS document_snapshot_id,
           d.norm_document_id AS resolved_document_id, d.slug, d.title,
           d.source_attribution, p.norms_snapshot_id AS paragraph_snapshot_id,
           (SELECT count(*) FROM norm_custody_binding cb
              JOIN blob b ON b.blob_id = cb.blob_id
             WHERE cb.role = 'norm_source'
               AND cb.target_kind = 'norm_document'
               AND cb.target_id = d.norm_document_id
               AND cb.anchor_kind = 'pdf'
               AND cb.anchor = d.source_document_ref
               AND b.state = 'available'
               AND b.media_type = 'application/pdf') AS source_pdf_binding_count,
           p.norm_document_pk AS paragraph_document_pk,
           d.norm_document_pk AS document_pk, p.norm_paragraph_id AS resolved_paragraph_id,
           p.clause_number, p.page_label, p.text AS paragraph_text,
           p.text_reliability
      FROM finding_observation_norm_citation c
      JOIN finding_observation o
        ON o.finding_observation_id = c.finding_observation_id
      LEFT JOIN norm_document d ON d.norm_document_id = c.norm_document_id
      LEFT JOIN norm_paragraph p ON p.norm_paragraph_id = c.norm_paragraph_id
     WHERE o.run_id = :run_id
     ORDER BY c.finding_observation_id COLLATE "C", c.citation_ordinal
""")

_NORMATIVE = frozenset({
    "evacuation", "fire_safety", "accessibility", "insulation", "sound",
})
_NON_NORMATIVE = frozenset({
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout",
    "facade", "roof", "documentation",
})


def _designation(slug: str) -> str:
    # The same display projection as norms search, without a deep context import.
    return " ".join(slug.split("__", 1)[0].replace("_", " ").split()) or slug


def _citation(row: dict, header: dict) -> VerifiedCitation:
    if (row["run_id"] != header["run_id"]
            or row["norms_snapshot_id"] != header["norms_snapshot_id"]
            or row["norm_retrieval_set_id"] != header["norm_retrieval_set_id"]
            or row["document_snapshot_id"] != header["norms_snapshot_id"]
            or row["paragraph_snapshot_id"] != header["norms_snapshot_id"]
            or row["resolved_document_id"] != row["norm_document_id"]
            or row["resolved_paragraph_id"] != row["norm_paragraph_id"]
            or row["paragraph_document_pk"] != row["document_pk"]
            or row["text_reliability"] != "reliable"
            or row["source_pdf_binding_count"] != 1
            or row["state"] not in {"verified", "rebound"}
            or row["source_attribution"] not in {"consultant_plus", "unattributed"}):
        raise CitationReadRefused("citation_provenance_invalid")
    quote, offset, length, content = (
        row["quote"], row["char_start"], row["char_length"], row["paragraph_text"]
    )
    if (not isinstance(quote, str) or not 20 <= len(quote) <= 4000
            or type(offset) is not int or offset < 0
            or type(length) is not int or length != len(quote)
            or not isinstance(content, str)
            or content[offset:offset + length] != quote
            or not isinstance(row["slug"], str)
            or not isinstance(row["title"], str)
            or not row["title"]
            or type(row["page_label"]) is not int or row["page_label"] < 1):
        raise CitationReadRefused("citation_source_invalid")
    designation = _designation(row["slug"])
    if not designation:
        raise CitationReadRefused("citation_designation_missing")
    return VerifiedCitation(
        citation_ordinal=row["citation_ordinal"],
        norms_snapshot_id=row["norms_snapshot_id"],
        norm_document_id=row["norm_document_id"],
        norm_paragraph_id=row["norm_paragraph_id"],
        designation=designation, title=row["title"],
        clause_number=row["clause_number"], page_label=row["page_label"],
        quote=quote, state=row["state"],
        source_attribution=row["source_attribution"],
    )


def read_verified_citations(
    session: Session, *, run_id: str, version_uid: str, profile_id: str,
) -> VerifiedCitationRead:
    """Read one terminal Run's exact certified finding partitions, without a commit.

    ``profile_id`` must be the later registered v3 identity, not a caller chosen
    assertion. The caller also owns authorization and a repeatable-read snapshot.
    """
    if not all(isinstance(value, str) and value for value in
               (run_id, version_uid, profile_id)):
        raise CitationReadRefused("read_identity_missing")
    header_row = session.execute(_HEADER, {
        "run_id": run_id, "version_uid": version_uid, "profile_id": profile_id,
    }).mappings().one_or_none()
    if header_row is None:
        raise CitationReadRefused("run_or_v3_profile_unavailable")
    header = dict(header_row)
    if (header["run_id"] != run_id or header["version_uid"] != version_uid
            or header["analysis_profile_id"] != profile_id
            or header["run_state"] not in {"published", "partial"}
            or header["cite_status"] != "succeeded"
            or header["set_state"] != "verified"
            or header["reviewed_content_key"] != header["snapshot_content_key"]
            or header["expected_set_sha256"] != header["observed_set_sha256"]
            or header["expected_catalogue_sha256"] != header["observed_catalogue_sha256"]
            or header["set_binding_count"] != 1
            or header["catalogue_binding_count"] != 1):
        raise CitationReadRefused("verified_run_authority_invalid")
    observations = [dict(row) for row in session.execute(
        _OBSERVATIONS, {"run_id": run_id}
    ).mappings().all()]
    citation_rows = [dict(row) for row in session.execute(
        _CITATIONS, {"run_id": run_id}
    ).mappings().all()]
    citations: dict[str, list[VerifiedCitation]] = {}
    for row in citation_rows:
        observation_id = row["finding_observation_id"]
        citations.setdefault(observation_id, []).append(_citation(row, header))
    grouped: dict[str, list[dict]] = {}
    canonical_ids: dict[str, str] = {}
    for row in observations:
        finding_uid = row["finding_uid"]
        observation_id = row["finding_observation_id"]
        if (observation_id is None or row["project_uid"] != header["project_uid"]
                or row["version_uid"] != version_uid
                or row["observation_run_id"] != run_id
                or row["observation_finding_uid"] != finding_uid
                or row["stage_id"] != "text_analysis" or row["grounded"] is not True
                or row["analysis_profile_id"] != profile_id
                or row["prompt_bundle_id"] != header["prompt_bundle_id"]
                or row["provider_mode"] != header["provider_mode"]):
            raise CitationReadRefused("finding_provenance_invalid")
        if finding_uid in canonical_ids and canonical_ids[finding_uid] != row["canonical_observation_id"]:
            raise CitationReadRefused("canonical_identity_conflict")
        canonical_ids[finding_uid] = row["canonical_observation_id"]
        grouped.setdefault(finding_uid, []).append(row)
    if set(citations) - {row["finding_observation_id"] for row in observations}:
        raise CitationReadRefused("orphan_citation_partition")
    findings: list[VerifiedFindingPartitions] = []
    for finding_uid, rows in grouped.items():
        canonical_id = canonical_ids[finding_uid]
        if canonical_id is None or sum(row["finding_observation_id"] == canonical_id for row in rows) != 1:
            raise CitationReadRefused("canonical_observation_missing")
        partitions: dict[str, VerifiedObservationPartition] = {}
        for row in rows:
            observation_id = row["finding_observation_id"]
            count = row["norm_citation_count"]
            items = tuple(citations.get(observation_id, ()))
            if (type(count) is not int or not 0 <= count <= 5
                    or count != len(items)
                    or tuple(item.citation_ordinal for item in items)
                    != tuple(range(1, count + 1))
                    or row["category"] not in _NORMATIVE | _NON_NORMATIVE
                    or (row["category"] in _NORMATIVE) != (count >= 1)
                    or (row["required_value"] is None) != (row["stated_value"] is None)
                    or ((row["category"] in _NORMATIVE)
                        != (row["required_value"] is not None))
                    or any(value is not None and (
                        not isinstance(value, str) or not 1 <= len(value) <= 200
                    ) for value in (row["required_value"], row["stated_value"]))):
                raise CitationReadRefused("citation_partition_invalid")
            partitions[observation_id] = VerifiedObservationPartition(
                finding_observation_id=observation_id,
                citation_count=count, citations=items,
                required_value=row["required_value"],
                stated_value=row["stated_value"],
            )
        findings.append(VerifiedFindingPartitions(
            finding_uid=finding_uid,
            canonical=partitions[canonical_id],
            merged_observations=tuple(
                partitions[row["finding_observation_id"]] for row in rows
                if row["finding_observation_id"] != canonical_id
            ),
        ))
    return VerifiedCitationRead(
        run_id=run_id, project_uid=header["project_uid"], version_uid=version_uid,
        norms_snapshot_id=header["norms_snapshot_id"],
        norm_retrieval_set_id=header["norm_retrieval_set_id"],
        run_state=header["run_state"], findings=tuple(findings),
    )
