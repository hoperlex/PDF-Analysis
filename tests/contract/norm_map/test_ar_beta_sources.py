"""The beta source policy cannot turn a known source gap into a citation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auditmanager.analysis.profiles.ar_v3.norm_map import beta_sources


def _canonical(document: dict[str, object]) -> bytes:
    return json.dumps(document, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _altered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
             mutate) -> None:
    document = json.loads(beta_sources.POLICY_PATH.read_bytes())
    mutate(document)
    canonical = _canonical(document)
    path = tmp_path / "beta_sources.json"
    path.write_bytes(canonical + b"\n")
    monkeypatch.setattr(beta_sources, "POLICY_PATH", path)
    monkeypatch.setattr(beta_sources, "POLICY_SHA256", hashlib.sha256(canonical).hexdigest())
    beta_sources.load_beta_source_policy()


def test_exact_beta_policy_has_all_six_groups_and_names_deferred_work() -> None:
    policy = beta_sources.load_beta_source_policy()
    assert policy.sha256 == beta_sources.POLICY_SHA256
    assert tuple(item.item_id for item in policy.items) == tuple(
        f"C{index:02d}" for index in range(1, 23)
    )
    assert policy.provisional_item_ids("F1") == ("C01", "C02", "C03")
    assert policy.context_only_item_ids("F2") == (
        "C05", "C06", "C08", "C09", "C10",
    )
    assert policy.provisional_item_ids("A2") == (
        "C16", "C17", "C18", "C19", "C20",
    )
    assert policy.context_only_item_ids("S1") == ("C21",)
    assert policy.context_only_item_ids("S2") == ("C22",)
    assert all(item.reason for item in policy.items)


def test_known_source_gap_cannot_be_promoted_by_editing_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(document: dict[str, object]) -> None:
        document["items"][20]["mode"] = "provisional_citation"

    with pytest.raises(beta_sources.BetaSourcePolicyRefused,
                       match="blocked_item_cannot_cite"):
        _altered(tmp_path, monkeypatch, mutate)


def test_metadata_card_alone_cannot_support_citation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(document: dict[str, object]) -> None:
        document["items"][0]["sources"] = ["D1_LOCAL", "D2_ROS_CARD"]

    with pytest.raises(beta_sources.BetaSourcePolicyRefused,
                       match="provisional_text_source_missing"):
        _altered(tmp_path, monkeypatch, mutate)


def test_source_reference_and_item_totality_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(document: dict[str, object]) -> None:
        document["items"][1]["id"] = "C01"

    with pytest.raises(beta_sources.BetaSourcePolicyRefused,
                       match="item_identity_or_mode_invalid"):
        _altered(tmp_path, monkeypatch, mutate)


def test_actual_policy_edit_without_reviewed_digest_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "beta_sources.json"
    path.write_bytes(beta_sources.POLICY_PATH.read_bytes().replace(
        b"D4_FAU_EXCERPT", b"D4_FAU_EXCERPx", 1,
    ))
    monkeypatch.setattr(beta_sources, "POLICY_PATH", path)
    with pytest.raises(beta_sources.BetaSourcePolicyRefused,
                       match="policy_digest_invalid"):
        beta_sources.load_beta_source_policy()
