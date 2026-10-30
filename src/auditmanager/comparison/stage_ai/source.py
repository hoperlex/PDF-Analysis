"""Build source-bound reviewer/classifier groups from stored C3 raw rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .model import AtomicEvidence, EvidenceGroup, Fragment, ReviewGroup, ReviewItem
from .validation import digest


@dataclass(frozen=True, slots=True)
class SourceGroup:
    review: ReviewGroup
    evidence: EvidenceGroup


def link_components(links: Sequence[Mapping[str, Any]]) -> tuple[tuple[Mapping[str, Any], ...], ...]:
    paired = [link for link in links if link["relation"] == "paired"]
    unseen = set(range(len(paired)))
    out = []
    while unseen:
        index = min(unseen)
        unseen.remove(index)
        component, pending = [], [index]
        profiles: set[str] = set()
        while pending:
            current = paired[pending.pop()]
            component.append(current)
            profiles.update((current["left_profile_id"], current["right_profile_id"]))
            for other in list(unseen):
                if paired[other]["left_profile_id"] in profiles or paired[other]["right_profile_id"] in profiles:
                    unseen.remove(other)
                    pending.append(other)
        out.append(tuple(sorted(component, key=lambda link: link["stage_link_item_id"])))
    return tuple(out)


def build_source_groups(snapshot: Mapping[str, Any], reviews: Mapping[str, Mapping[str, Any]] | None = None) -> tuple[SourceGroup, ...]:
    fragments = {}
    for row in snapshot["fragments"]:
        box = row["box_anchor"]
        fragments[row["stage_text_fragment_id"]] = Fragment(
            str(row["stage_text_fragment_id"]), str(row["page_profile_id"]), str(row["side"]),
            str(row["normalised_text"]), str(row["content_key"]),
            (float(box["x0"]), float(box["top"]), float(box["x1"]), float(box["bottom"])),
        )
    result = []
    for links in link_components(snapshot["links"]):
        group_id = "grp:" + digest([link["stage_link_item_id"] for link in links])[:24]
        left_profiles = tuple(sorted({str(link["left_profile_id"]) for link in links}))
        right_profiles = tuple(sorted({str(link["right_profile_id"]) for link in links}))
        profiles = set(left_profiles + right_profiles)
        diffs = []
        for row in snapshot["differences"]:
            refs = tuple(ref for ref in (row["left_fragment_id"], row["right_fragment_id"]) if ref is not None)
            if any(ref not in fragments for ref in refs):
                raise ValueError("stage_ai_raw_fragment_missing")
            if any(fragments[ref].profile_id in profiles for ref in refs):
                diffs.append(row)
        if not diffs:
            continue
        if len(diffs) > 400:
            raise ValueError("stage_ai_group_evidence_budget")
        items = tuple(ReviewItem(
            str(row["stage_text_difference_id"]),
            () if row["left_fragment_id"] is None else (str(row["left_fragment_id"]),),
            () if row["right_fragment_id"] is None else (str(row["right_fragment_id"]),),
            str(row["status"]).upper(),
        ) for row in diffs)
        included = {fragment_id for item in items for fragment_id in item.left_fragment_ids + item.right_fragment_ids}
        for hint in snapshot.get("hints", ()):
            if hint["source_fragment_id"] in included and hint["target_fragment_id"] in fragments:
                included.add(str(hint["target_fragment_id"]))
        group_fragments = tuple(f for key, f in sorted(fragments.items()) if f.profile_id in profiles or key in included)
        uncertain = any(link["confidence"] == "review" for link in links)
        review = ReviewGroup(group_id, group_fragments, items, left_profiles, right_profiles)
        decisions = list((reviews or {}).get(group_id, {}).get("decisions", ()))
        evidence = []
        for row, item in zip(diffs, items, strict=True):
            original_refs = set(item.left_fragment_ids + item.right_fragment_ids)
            touching = [decision for decision in decisions if original_refs & set(
                decision["left_fragment_ids"] + decision["right_fragment_ids"]
            )]
            left, right = item.left_fragment_ids, item.right_fragment_ids
            status = item.deterministic_status
            if len(touching) == 1 and original_refs <= set(touching[0]["left_fragment_ids"] + touching[0]["right_fragment_ids"]):
                chosen = touching[0]
                status = chosen["status"]
                left, right = tuple(chosen["left_fragment_ids"]), tuple(chosen["right_fragment_ids"])
            elif touching:
                status = "UNCERTAIN"
            hint = "REVIEW" if uncertain or status == "UNCERTAIN" else (
                "SERVICE_STRUCTURE" if status in {"SAME", "MOVED"} else "UNCLASSIFIED"
            )
            evidence.append(AtomicEvidence(
                item.evidence_id, digest({"raw": row["content_key"], "review": touching}), status,
                left, right,
                "\n".join(fragments[ref].text for ref in left),
                "\n".join(fragments[ref].text for ref in right),
                "Изменение текста по исходным фрагментам.", hint,
            ))
        result.append(SourceGroup(review, EvidenceGroup(group_id, tuple(evidence), uncertain)))
    return tuple(result)
