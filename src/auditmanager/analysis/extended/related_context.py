"""Literal, object-bound distant source excerpts for the existing comprehensive/critic calls."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import re

from .core import digest

VERSION = "related-review-context-v1"
_OBJECT = re.compile(r"(?<![\w])(?:\d*[А-ЯA-Z]{1,8}[.\-]?[А-ЯA-Z]*\d+[А-ЯA-Z0-9.\-]*|ВРУ[\-–][А-ЯA-Z0-9]+)(?![\w])")


def object_keys(text):
    return sorted({value.replace("–", "-").upper() for value in _OBJECT.findall(text.upper())
        if not re.fullmatch(r"(?:СП|ГОСТ|IEC|ISO)\d+", value)})


def build_related_index(pages, *, version_uid):
    excerpts, by_object = [], defaultdict(list)
    for page in pages:
        text = page.get("text", "")
        if not isinstance(text, str):
            raise ValueError("related_context_text_invalid")
        for match in re.finditer(r"[^\n]+(?:\n|$)", text):
            line = match[0].rstrip("\n")
            keys = object_keys(line)
            if not keys:
                continue
            start = max(0, match.start() - 300)
            end = min(len(text), match.end() + 700)
            quote = text[start:end]
            source_id = "related_" + digest({"version_uid": version_uid, "page": page["page_number"],
                "start": start, "end": end, "text": quote})[:24]
            row = {"source_id": source_id, "kind": "text", "source_type": "related_page_excerpt",
                "version_uid": version_uid, "page_number": page["page_number"], "quote": quote,
                "character_start": start, "character_end": end,
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(), "object_keys": keys}
            index = len(excerpts)
            excerpts.append(row)
            for key in keys:
                by_object[key].append(index)
    return {"version": VERSION, "excerpts": excerpts, "by_object": dict(by_object)}


def select_related_context(index, *, texts, page_numbers, character_budget=24_000):
    keys = sorted({key for text in texts for key in object_keys(text)})
    selected, omitted, seen, characters = [], [], set(), 0
    candidates = sorted({i for key in keys for i in index["by_object"].get(key, [])},
        key=lambda i: (index["excerpts"][i]["page_number"] in page_numbers,
                       index["excerpts"][i]["page_number"], index["excerpts"][i]["character_start"]))
    for i in candidates:
        row = index["excerpts"][i]
        if row["source_id"] in seen:
            continue
        seen.add(row["source_id"])
        if characters + len(row["quote"]) > character_budget:
            omitted.append(row["source_id"])
        else:
            selected.append(dict(row))
            characters += len(row["quote"])
    return {"version": VERSION, "object_keys": keys, "sources": selected, "characters": characters,
        "omitted_source_ids": omitted, "complete": not omitted,
        "selection": "literal_object_reference", "document_completeness_claimed": False}
