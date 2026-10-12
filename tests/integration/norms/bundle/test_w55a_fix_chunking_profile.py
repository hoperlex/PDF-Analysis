"""`W55A-FIX` (JUDGE-Y Y-5): a bundle is over ``characters-v2:<target>`` or it is refused.

Designation admits only a build over the reliability-aware chunking profile
(``current_snapshot.BUILD_COMPLETE_SQL``). Before this fix nothing earlier enforced it: a
bundle over ``characters-v1`` exported, imported and reported clean, and was refused only at
designation, after the stand had taken it in. Now the export refuses such a profile before
it reads or writes anything, and the manifest parser -- which ``verify``, ``import`` and
``report`` all go through -- refuses one too. Container-free.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.norms.bundle.cli import main
from auditmanager.norms.bundle.errors import EXIT_REFUSED, BundleRefused
from auditmanager.norms.bundle.export import read_export_source, write_bundle
from auditmanager.norms.bundle.layout import MANIFEST_NAME
from auditmanager.norms.bundle.manifest import is_designatable_chunking, parse_manifest
from tests.integration.norms.bundle.support import synthetic_rows, write_drop
from tests.integration.norms.bundle.test_export_offline import _source

REFUSED_PROFILES = [
    "characters-v1:1200",   # the profile that joins unreliable text
    "characters-v2",        # no target
    "characters-v2:",       # an empty target
    "characters-v2:01200",  # not the canonical spelling of its target
    "characters-v2:abc",
    "characters-v3:1200",
    "",
]


class _Untouchable:
    """A session that fails the test if the export reaches the database at all."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the export reached the database ({name}) before refusing")


@pytest.fixture
def written(tmp_path: Path) -> dict[str, Any]:
    corpus, sums = write_drop(tmp_path / "drop")
    directory = write_bundle(
        _source(synthetic_rows()), corpus=corpus, drop_sums=sums, ledger=None,
        out=tmp_path / "out",
    ).directory
    return json.loads((directory / MANIFEST_NAME).read_text())


def _rendered(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode()


def test_only_a_well_formed_characters_v2_profile_is_designatable() -> None:
    assert is_designatable_chunking("characters-v2:1200")
    assert is_designatable_chunking("characters-v2:800")
    for profile in REFUSED_PROFILES:
        assert not is_designatable_chunking(profile), profile


@pytest.mark.parametrize("profile", REFUSED_PROFILES)
def test_the_manifest_parser_refuses_another_chunking_profile(
    written: dict[str, Any], profile: str
) -> None:
    written["chunking_profile"] = profile
    with pytest.raises(BundleRefused) as refused:
        parse_manifest(_rendered(written))
    assert refused.value.reason == "manifest_invalid", refused.value
    assert "chunking" in refused.value.message


def test_the_control_manifest_parses_with_its_characters_v2_profile(
    written: dict[str, Any],
) -> None:
    assert written["chunking_profile"] == "characters-v2:1200"
    assert parse_manifest(_rendered(written)).chunking_profile == "characters-v2:1200"


@pytest.mark.parametrize("profile", ["characters-v1:1200", "characters-v2:abc"])
def test_the_export_refuses_before_reading_the_database(profile: str) -> None:
    with pytest.raises(BundleRefused) as refused:
        read_export_source(
            _Untouchable(),  # type: ignore[arg-type]
            snapshot_id="ns_01M2545JSD15ETSNNV904X991N", chunking_profile=profile,
        )
    assert refused.value.reason == "chunking_profile_refused"


def test_the_export_refuses_before_writing_anything(tmp_path: Path) -> None:
    corpus, sums = write_drop(tmp_path / "drop")
    source = dataclasses.replace(_source(synthetic_rows()), chunking_profile="characters-v1:1200")
    out = tmp_path / "out"
    with pytest.raises(BundleRefused) as refused:
        write_bundle(source, corpus=corpus, drop_sums=sums, ledger=None, out=out)
    assert refused.value.reason == "chunking_profile_refused"
    assert not out.exists(), "a refused export left work behind"


def test_the_export_command_refuses_without_opening_the_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def _no_database(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the export command opened the promotion database")

    monkeypatch.setattr("auditmanager.shared.db.session.session_scope", _no_database)
    status = main([
        "export", "--snapshot", "ns_01M2545JSD15ETSNNV904X991N",
        "--chunking-profile", "characters-v1:1200",
        "--corpus", str(tmp_path / "corpus"), "--drop-sums", str(tmp_path / "SHA256SUMS"),
        "--out", str(tmp_path / "out"),
    ])
    assert status == EXIT_REFUSED
    assert "REFUSED [chunking_profile_refused]" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
