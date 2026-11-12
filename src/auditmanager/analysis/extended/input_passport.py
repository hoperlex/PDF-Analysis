"""Read-only input custody and conservative sheet-register coverage for v2 review."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import re

from .core import digest

VERSION = "review-input-passport-v1"
_REGISTER = re.compile(r"ведомость\s+(?:рабочих\s+)?(?:чертежей|листов)", re.I)
_SHEET = re.compile(r"(?:^|\n)\s*(?:лист\s*)?(\d+(?:[.,]\d+)?)"
    r"(?:[ \t]*[|;\t][ \t]*|[ ]+(?=(?:Общие|Схема|План|Узел|Ведомость|Спецификация|Разрез|Расч[её]т)\b))"
    r"(\S[^\n]{2,})", re.I)
_STAMP = re.compile(r"(?:^|[\s|])лист\s*[:№|]?\s*(\d+(?:[.,]\d+)?)(?=\s|[|;]|$)", re.I)
_HEX = re.compile(r"[a-f0-9]{64}\Z")


def build_input_passport(*, version_uid, pdf_sha256, page_count, pages, sources, skipped=()):
    """A hash is custody, not completeness. Ambiguous register/stamp text stays unresolved."""
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
        raise ValueError("input_passport_page_count_invalid")
    by_page = defaultdict(list)
    for source in sources:
        if source.get("kind") == "image":
            by_page[source["page_number"]].append(source)
    text_pages = {p["page_number"] for p in pages if isinstance(p.get("text"), str)}
    crops = sorted(({key: deepcopy(source[key]) for key in
        ("source_id", "blob_id", "page_number", "bbox_norm", "crop_sha256", "size_bytes") if key in source}
        for values in by_page.values() for source in values), key=lambda row: row["source_id"])
    pages_read = [{"page_number": number, "text_available": number in text_pages,
        "crop_ids": [source["source_id"] for source in by_page[number]],
        "skipped": [deepcopy(row) for row in skipped if row.get("page_number") == number]}
        for number in range(1, page_count + 1)]
    stamps = defaultdict(set)
    registers = []
    for page in pages:
        text = page.get("text", "")
        if _REGISTER.search(text):
            for match in _SHEET.finditer(text):
                registers.append({"sheet_label": match[1].replace(",", "."), "title": match[2].strip(),
                    "register_page": page["page_number"], "quote": match[0].strip()})
        else:
            for match in _STAMP.finditer(text):
                stamps[match[1].replace(",", ".")].add(page["page_number"])
    entries = []
    for row in registers:
        found = sorted(stamps[row["sheet_label"]])
        external = bool(re.search(r"(?:см\.?\s+(?:том|раздел)|отдельн\w*\s+(?:том|проект)|внешн)", row["title"], re.I))
        entries.append({**row, "page_numbers": found,
            "status": "external" if external else "found" if len(found) == 1 else "unresolved",
            "reason": "external_reference" if external else "exact_unique_sheet_label" if len(found) == 1
                else "sheet_label_ambiguous" if found else "sheet_not_located_in_available_text"})
    pdf_known = isinstance(pdf_sha256, str) and _HEX.fullmatch(pdf_sha256) is not None
    incomplete = [row["page_number"] for row in pages_read if not row["text_available"] and not row["crop_ids"]]
    return {"version": VERSION, "version_uid": version_uid, "pdf_sha256": pdf_sha256 if pdf_known else None,
        "pdf_hash_status": "recorded" if pdf_known else "unavailable", "page_count": page_count,
        "crop_count": len(crops), "crops": crops, "crop_manifest_sha256": digest(crops),
        "crop_verification": "pending" if crops else "not_required", "verified_crop_ids": [], "pages": pages_read,
        "unrepresented_pages": incomplete, "source_coverage_complete": not incomplete,
        "sheet_register": {"status": "not_located" if not entries else "resolved" if all(
            row["status"] in {"found", "external"} for row in entries) else "unresolved",
            "entries": entries, "absence_proved": False}, "document_completeness_claimed": False}


def verify_passport_crop(passport, source, raw):
    import hashlib
    if len(raw) != source["size_bytes"] or hashlib.sha256(raw).hexdigest() != source["crop_sha256"]:
        raise ValueError("extended_crop_digest_invalid")
    if source["source_id"] not in {row["source_id"] for row in passport["crops"]}:
        raise ValueError("input_passport_unknown_crop")
    verified = passport["verified_crop_ids"]
    if source["source_id"] not in verified:
        verified.append(source["source_id"])
    passport["crop_verification"] = "verified" if len(verified) == passport["crop_count"] else "partial"
