"""Strict presentation groups over saved observations, never an expert decision.

Only identical wording and an actually bound shared source can connect records.
The caller keeps every raw observation and window; origins reference that same
array, so disagreeing critique, normative annotations or corrections are retained.
"""
from __future__ import annotations

from .core import digest

VERSION = "strict-cross-window-v1"
METHOD = "identical_text_shared_source"
MAX_RECORDS = 20_000
_SOURCE_FIELDS = ("source_id", "version_uid", "kind", "source_type", "page_number",
    "bbox_norm", "blob_id", "crop_sha256", "text_sha256", "artifact_sha256",
    "source_sha256", "quote_source", "quote")


def consolidate_observations(observations, *, sources, version_uid):
    if (not isinstance(observations, list) or len(observations) > MAX_RECORDS
            or not isinstance(sources, list) or not isinstance(version_uid, str)
            or not version_uid):
        raise ValueError("consolidation_input_invalid")
    source_keys, conflicts = {}, set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            raise ValueError("consolidation_source_invalid")
        identity = source["source_id"]
        fingerprint = digest({field: source[field] for field in _SOURCE_FIELDS if field in source})
        if identity in source_keys and source_keys[identity] != fingerprint:
            conflicts.add(identity)
        source_keys[identity] = fingerprint
    known_sources = set(source_keys) - conflicts
    parents = list(range(len(observations)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def connect(left, right):
        first, second = find(left), find(right)
        if first != second:
            # The first occurrence remains the stable representative.
            parents[max(first, second)] = min(first, second)

    identities, words, hashes, unbound = [], [], [], []
    owners = {}
    for index, observation in enumerate(observations):
        if (not isinstance(observation, dict) or not isinstance(observation.get("title"), str)
                or not isinstance(observation.get("description"), str)
                or not isinstance(observation.get("source_ids"), list)
                or any(not isinstance(value, str) or not value for value in observation["source_ids"])):
            raise ValueError("consolidation_observation_invalid")
        references = set(observation["source_ids"])
        primary = observation.get("original_primary_observation")
        full_description = observation["description"]
        recommendation = None
        if isinstance(primary, dict):
            if isinstance(primary.get("finding_text"), str):
                full_description = primary["finding_text"]
            recommendation = primary.get("recommendation_text")
        wording = digest({"title": observation["title"], "description": observation["description"],
                          "full_description": full_description, "recommendation": recommendation,
                          "category": observation.get("category")})
        identities.append(references)
        words.append(wording)
        hashes.append(digest(observation))
        missing = references - known_sources
        bound = bool(references) and not missing
        unbound.append(not bound)
        if not bound:
            continue
        for reference in sorted(references):
            key = (wording, reference)
            previous = owners.setdefault(key, index)
            connect(previous, index)

    components = {}
    for index in range(len(observations)):
        components.setdefault(find(index), []).append(index)
    groups = []
    for indices in components.values():
        first = observations[indices[0]]
        references = sorted(set().union(*(identities[index] for index in indices)))
        windows = sorted({observations[index]["window_id"] for index in indices
            if isinstance(observations[index].get("window_id"), str)})
        missing = sorted(set(references) - known_sources)
        origins = [{"raw_index": index, "window_id": observations[index].get("window_id"),
                    "observation_id": observations[index].get("observation_id"),
                    "observation_sha256": hashes[index]} for index in indices]
        group_id = "xgrp_" + digest({"version": VERSION, "version_uid": version_uid,
            "wording_sha256": words[indices[0]], "source_ids": references,
            **({"unbound_origin": origins[0]} if unbound[indices[0]] else {})})[:32]
        groups.append({"group_id": group_id, "title": first["title"],
            "description": first["description"], "source_ids": references,
            "origin_count": len(indices), "source_count": len(references), "window_ids": windows,
            "origin_records": origins, "requires_expert_review": True,
            "grouping_status": "source_binding_unavailable" if missing or not references else METHOD,
            "unresolved_source_ids": missing})
    merged = sum(group["origin_count"] > 1 for group in groups)
    return {"consolidation": {"version": VERSION, "method": METHOD,
        "raw_count": len(observations), "group_count": len(groups),
        "coalesced_count": len(observations) - len(groups), "merged_group_count": merged,
        "ungrouped_count": len(groups) - merged, "unbound_observation_count": sum(unbound),
        "conflicting_source_ids": sorted(conflicts), "complete": True,
        "canonical_findings_unchanged": True, "expert_decisions_written": False},
        "consolidated_observations": groups}
