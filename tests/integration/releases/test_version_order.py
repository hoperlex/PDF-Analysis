"""Canonical release precedence without a database or application stand."""

from __future__ import annotations

import pytest

from auditmanager.releases.public import canonical_semver_sort_key


@pytest.mark.parametrize(
    "ascending",
    [
        ["0.9.0", "0.10.0", "1.0.0", "2.0.0", "10.0.0"],
        [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        ],
        ["1.0.0-1", "1.0.0-2", "1.0.0-10", "1.0.0-alpha"],
        ["1.0.0-a", "1.0.0-a.1", "1.0.0-a-", "1.0.0-b"],
        ["1.0.0-999", "1.0.0-1000"],
        ["1.0.9", "1.1.0", "1.10.0", "2.0.0"],
    ],
)
def test_bytewise_key_orders_versions_by_semver(ascending: list[str]) -> None:
    assert sorted(reversed(ascending), key=canonical_semver_sort_key) == ascending


@pytest.mark.parametrize(
    "version",
    [
        "", "v1.0.0", "1.0", "1.0.0 ", " 1.0.0", "01.0.0", "1.00.0",
        "1.0.01", "1.0.0-01", "1.0.0-alpha.01", "1.0.0-", "1.0.0-a..b",
        "1.0.0+build.1", "1.0.0-α", "1.0.0-alpha_1", "1.0.0\n",
    ],
)
def test_noncanonical_version_is_refused(version: str) -> None:
    with pytest.raises(ValueError, match="noncanonical SemVer"):
        canonical_semver_sort_key(version)


def test_equal_versions_have_equal_keys() -> None:
    assert canonical_semver_sort_key("0.3.0") == canonical_semver_sort_key("0.3.0")
