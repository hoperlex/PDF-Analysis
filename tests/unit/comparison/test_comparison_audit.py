"""`COMPARE-PERSISTED-SUMMARY-01`: the comparison journal keeps ids and digests, nothing else."""

from __future__ import annotations

import pytest

from auditmanager.comparison import audit

CMP = "cmp_01M2545JSD15ETSNNV904XD001"
LINK = "sln_01M2545JSD15ETSNNV904XD001"
V1 = "ver_01M2545JSD15ETSNNV904XD001"
V2 = "ver_01M2545JSD15ETSNNV904XD002"
USER = "usr_01M2545JSD15ETSNNV904XD001"
SEAL = "a" * 64


def _payload(**changes):
    return {
        "comparison_id": CMP, "sheet_link_id": LINK, "link_revision": 1,
        "source_version_uid": V1, "target_version_uid": V2, "source_page_number": 1,
        "target_page_number": 2, "actor_uid": USER, "raw_evidence_seal_sha256": SEAL,
    } | changes


def test_a_complete_payload_is_kept_as_it_is() -> None:
    assert audit.validated(audit.EVENT_SHEET_LINK_APPROVED, _payload()) == _payload()


def test_the_seal_may_be_absent_only_from_a_withdrawal() -> None:
    bare = {k: v for k, v in _payload().items() if k != "raw_evidence_seal_sha256"}
    assert audit.validated(audit.EVENT_SHEET_LINK_WITHDRAWN, bare) == bare
    with pytest.raises(ValueError, match="lacks"):
        audit.validated(audit.EVENT_SHEET_LINK_APPROVED, bare)


@pytest.mark.parametrize("key", ["actor_label", "page_text", "quote", "ip_address", "note"])
def test_a_key_outside_the_allow_list_is_refused(key) -> None:
    with pytest.raises(ValueError, match="non-allowlisted"):
        audit.validated(audit.EVENT_SHEET_LINK_APPROVED, _payload() | {key: "Иванов"})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("comparison_id", "cmp_x"), ("comparison_id", LINK), ("sheet_link_id", CMP),
        ("actor_uid", "ivanov"), ("source_version_uid", USER),
        ("link_revision", 0), ("link_revision", True), ("source_page_number", 501),
        ("target_page_number", 0), ("raw_evidence_seal_sha256", "A" * 64),
        ("raw_evidence_seal_sha256", "a" * 63),
    ],
)
def test_a_value_that_is_not_what_its_key_says_is_refused(key, value) -> None:
    with pytest.raises(ValueError):
        audit.validated(audit.EVENT_SHEET_LINK_APPROVED, _payload() | {key: value})
