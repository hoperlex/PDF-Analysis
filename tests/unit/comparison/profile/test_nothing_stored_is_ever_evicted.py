"""No eviction, no blob delete (`CMP-PROFILE-01`, ADR-0025 decision 9).

«There is **no eviction** of stored blobs in the beta: the storage boundary offers no delete of a published blob, and
a delete from a lane would be a dual write.» The lane's code is held to it statically: the storage port is never asked
to discard or purge, and the one SQL ``DELETE`` of the package removes the row of a page that ended without a result
(``needs_review`` / ``RENDER_FAILED``) and no other row -- a profile that is ``ready`` or ``refused`` is never deleted.
"""

from __future__ import annotations

import re
from pathlib import Path

PROFILE = Path(__file__).resolve().parents[4] / "src" / "auditmanager" / "comparison" / "profile"
FORBIDDEN_STORE_CALLS = ("discard_temporary", "_purge", "delete_object", "purge_published", "erase")


def _sources() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in PROFILE.glob("*.py")}


def test_no_module_asks_the_object_store_to_remove_anything() -> None:
    offenders = {
        name: [call for call in FORBIDDEN_STORE_CALLS if re.search(rf"\.{call}\(|\b{call}\b", text.split('"""', 2)[-1])]
        for name, text in _sources().items()
    }
    assert {name: calls for name, calls in offenders.items() if calls} == {}


def test_the_only_delete_statement_removes_rows_that_ended_without_a_result() -> None:
    statements = [
        (name, match)
        for name, text in _sources().items()
        for match in re.findall(r'"(DELETE FROM[^"]*)"(?:\s*"([^"]*)")*', text)
    ]
    assert [name for name, _ in statements] == ["repository.py"]
    source = _sources()["repository.py"]
    assert source.count("DELETE FROM") == 1
    assert "AND status = 'needs_review' AND reason = 'RENDER_FAILED'" in source
    assert "comparison_page_profile WHERE version_uid" in source
