"""Versioned authority for the owner-approved v2 quality hotfix, never retroactive."""
from __future__ import annotations

import hashlib
from pathlib import Path

VERSION = "v2-quality-hotfix-v1"
POLICY_KEY = "quality_policy"


def quality_policy():
    root = Path(__file__).parent
    names = ("v2_quality.py", "input_passport.py", "related_context.py", "substantive_review.py", "consolidation.py")
    sha = hashlib.sha256()
    for name in names:
        sha.update(name.encode()); sha.update((root / name).read_bytes())
    return {"version": VERSION, "bundle_sha256": sha.hexdigest()}


def validate_quality_policy(value, *, compare_bundle=True):
    if (not isinstance(value, dict) or set(value) != {"version", "bundle_sha256"}
            or value["version"] != VERSION or not isinstance(value["bundle_sha256"], str)
            or len(value["bundle_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in value["bundle_sha256"])
            or compare_bundle and value != quality_policy()):
        raise ValueError("v2_quality_changed_requires_consent")
    return True
