"""What one call asks and what identifies it: the prompt, the pictures, the content key (`CMP-VC-AIPAIR-01`).

A **call plan** is everything about one model call that is known without making it: the text, the pages whose stored previews
go with it in the order the model sees them, and the **content key** under which its answer is stored. The estimate counts plans;
the handler runs them. Both build them here, so what was priced is what is asked.

The content key (ADR-0025 decision 15, the wave brief's rule 5) is a digest of the prompt version, the project, the pinned model,
the process's provider mode (a recorded answer is never mistaken for a live one), the kind of the question, the digest of the
exact prompt text and, for each picture in order, the content key of its page and the digest of its stored preview. Two questions with the same key are the same question: the second is never sent. A new prompt
version, another model, another project or another page content is another key.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from auditmanager.comparison.ai_pairs.decide import reverse_candidates
from auditmanager.comparison.ai_pairs.model import (
    KIND_REVERSE,
    MAX_OUTPUT_TOKENS,
    PROMPT_VERSION,
    PageFacts,
    Question,
)
from auditmanager.comparison.ai_pairs.prompt import build_prompt
from auditmanager.comparison.ai_pairs.questions import askable

__all__ = ["CallPlan", "PlanContext", "content_key", "forward_plan", "reverse_plan"]

_CODE_MAX: Final[int] = 120


@dataclass(frozen=True, slots=True)
class PlanContext:
    """What a plan needs besides the question: the project, the model that answers, the order of the versions (a version is
    named in the prompt by its place in it), the page counts and what the stored profiles say of the pages."""

    project_uid: str
    model_identity: str
    provider_mode: str
    order: tuple[str, ...]
    page_counts: Mapping[str, int]
    facts: Mapping[tuple[str, int], PageFacts]
    document_title: str = ""

    def label(self, version_uid: str) -> str:
        return f"№{self.order.index(version_uid) + 1}" if version_uid in self.order else version_uid[:12]

    def page(self, version_uid: str, page_number: int) -> PageFacts:
        try:
            return self.facts[(version_uid, page_number)]
        except KeyError:
            raise LookupError("a page of the question has no stored profile") from None


@dataclass(frozen=True, slots=True)
class CallPlan:
    """One call: the question kind its answer is stored under, the prompt, the pages shown (sheet first), the candidate page
    numbers the answer chooses among, and the content key."""

    kind: str
    prompt: str
    pages: tuple[PageFacts, ...]
    cands: tuple[int, ...]
    key: str

    @property
    def images(self) -> int:
        return len(self.pages)

    @property
    def image_bytes(self) -> int:
        return sum(page.preview_size for page in self.pages)


def content_key(
    *, project_uid: str, model_identity: str, provider_mode: str, kind: str, prompt: str, pages: Sequence[PageFacts],
) -> str:
    """The key an answer is stored under (see the module docstring)."""
    document = {
        "prompt_version": PROMPT_VERSION, "project_uid": project_uid, "model": model_identity, "mode": provider_mode, "kind": kind,
        "max_tokens": MAX_OUTPUT_TOKENS, "prompt": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "images": [[page.content_key, page.preview_sha256] for page in pages],
    }
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _code(context: PlanContext, sheet: PageFacts) -> str:
    return (sheet.designation or context.document_title)[:_CODE_MAX]


def forward_plan(question: Question, context: PlanContext) -> CallPlan:
    """The question to the model: sheet A against the candidates of the next version."""
    sheet = context.page(question.a.version_uid, question.a.page_number)
    candidates = tuple(context.page(question.b_version_uid, page.page_number) for page in question.candidates)
    prompt = build_prompt(
        code=_code(context, sheet), a_label=context.label(question.a.version_uid), a_facts=sheet,
        a_page_count=int(context.page_counts.get(question.a.version_uid, 0)), b_label=context.label(question.b_version_uid),
        candidates=candidates, b_page_count=int(context.page_counts.get(question.b_version_uid, 0)), back=False,
    )
    pages = (sheet, *candidates)
    return CallPlan(
        kind=question.kind, prompt=prompt, pages=pages, cands=tuple(page.page_number for page in candidates),
        key=content_key(
            project_uid=context.project_uid, model_identity=context.model_identity, provider_mode=context.provider_mode,
            kind=question.kind, prompt=prompt, pages=pages,
        ),
    )


def reverse_plan(question: Question, b_page: int, context: PlanContext) -> CallPlan | None:
    """The reverse question: sheet ``b_page`` of B's version against the pages of A's version it could be the new edition of
    (``sheet_match.py:318-324``, ``:573-582``). ``None`` when it cannot be asked: the sheet is a specification sheet or has no
    stored preview, or no candidate is left once the specification sheets and the pages without a preview are taken out
    (the original answers «none» for those, ``:247-250``; here there is simply no reverse answer, so nothing is accepted)."""
    sheet = context.page(question.b_version_uid, b_page)
    if not askable(sheet):
        return None
    numbers = reverse_candidates(question, b_page, int(context.page_counts.get(question.a.version_uid, 0)))
    candidates = tuple(
        context.facts[(question.a.version_uid, number)] for number in numbers
        if askable(context.facts.get((question.a.version_uid, number)))
    )
    if not candidates:
        return None
    prompt = build_prompt(
        code=_code(context, sheet), a_label=context.label(question.b_version_uid), a_facts=sheet,
        a_page_count=int(context.page_counts.get(question.b_version_uid, 0)), b_label=context.label(question.a.version_uid),
        candidates=candidates, b_page_count=int(context.page_counts.get(question.a.version_uid, 0)), back=True,
    )
    pages = (sheet, *candidates)
    return CallPlan(
        kind=KIND_REVERSE, prompt=prompt, pages=pages, cands=tuple(page.page_number for page in candidates),
        key=content_key(
            project_uid=context.project_uid, model_identity=context.model_identity, provider_mode=context.provider_mode,
            kind=KIND_REVERSE, prompt=prompt, pages=pages,
        ),
    )
