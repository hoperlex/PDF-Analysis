"""The run of one sheet: packet -> call -> context request -> check -> description (`CMP-VC-AISHEET-01`).

A port of the original's ``sheet_changes/run.py`` (`23f379fd`, lines 1-287) and ``single.py`` (lines 117-197) on this tree's spend wrapper.
The limits of one sheet are the original's: at most ``MAX_LAUNCHES`` (3) launches of the model -- the main call, one technical retry,
one context request and one pass over the candidates the model left unsorted (``run.py:3-8``, ``:33``). The program executes the context
request: it looks for the designations and rows on the pages of the **two chosen versions** only and cuts crops from those two; the model
runs no command (``run.py:57-114``).

**Every call goes through** :class:`~auditmanager.comparison.spend.caller.ComparisonModelCaller`: the ``prepared`` row is committed
before the request leaves, an outcome that is not known is never repeated (the wrapper raises ``OutcomeUnknown`` and this module lets it
through), a cost above the consent pauses the job (``CallResult.pause``: the reply is kept, **no further call is made** for the job).

What is different from the original, each for a stated reason:

* **a technical retry is a retry of a proven non-delivery or of an unusable answer only** (an answer that is not JSON or not in the
  schema). The original also retried ``UNKNOWN`` and ``TIMEOUT``; here those are an outcome nobody knows, and ADR-0025 decision 5 forbids
  sending again by itself. A refusal of the provider that proves nothing was processed (``CallFailed.retry_safe``) is retried; the waits
  of 20 s .. 600 s are the queue's retry back-off, not a sleep in a handler;
* **the pictures of a follow-up request are at most eight in all** (``A-12``): the extra pictures and as many of the first request's as
  fit, the overview first;
* **no cache directory**: the stored description is the cache, and it is looked up by its content key before any call (the handler's
  step), so a described sheet is never asked again whatever the job.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from auditmanager.analysis.public import ModelRequest, ModelResponse
from auditmanager.comparison.ai_jobs.model import (
    CHARS_PER_TOKEN_DENOMINATOR,
    CHARS_PER_TOKEN_NUMERATOR,
    TOKENS_PER_IMAGE,
)
from auditmanager.comparison.ai_sheets import geometry as geo
from auditmanager.comparison.ai_sheets.images import fit_total_bytes
from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.ai_sheets import schema as sc
from auditmanager.comparison.ai_sheets.check import check, state_of
from auditmanager.comparison.ai_sheets.description import build_description, build_single_description, check_single
from auditmanager.comparison.ai_sheets.material import SheetMaterial
from auditmanager.comparison.ai_sheets.model import (
    IMAGE_MAX_PX,
    MAX_CONTEXT_REQUESTS,
    MAX_EXTRA_IMAGES,
    MAX_LAUNCHES,
    MAX_OUTPUT_TOKENS,
    SINGLE_TEXT_LIMIT,
)
from auditmanager.comparison.spend.errors import CallFailed, CallLost, CallRefused, OutcomeUnknown, SpendError
from auditmanager.comparison.spend.model import CallEstimate, CallRoute, Consent
from auditmanager.comparison.work.model import WorkItem
from auditmanager.executors.public import MAX_IMAGE_BYTES, MAX_IMAGES, MAX_TOTAL_IMAGE_BYTES, CropImage, attach_images

__all__ = [
    "SheetInterrupted",
    "SheetRun",
    "build_request",
    "describe_pair",
    "describe_single",
    "estimate_for",
    "resolve_context",
]

_VALUE: Final = re.compile(r"^[0-9A-Za-zА-Яа-яЁё*/().,\- ]{1,40}$")  # run.py:37


def estimate_for(prompt_chars: int, images: int) -> CallEstimate:
    """What one call is estimated at: the characters at the conversion of the AI-job core, the pictures at their price, and the output at
    the ceiling of the request."""
    prompt_chars += len(sc.SYSTEM_PROMPT)
    tokens = -(-prompt_chars * CHARS_PER_TOKEN_NUMERATOR // CHARS_PER_TOKEN_DENOMINATOR) + images * TOKENS_PER_IMAGE
    return CallEstimate(input_tokens=tokens, output_tokens=MAX_OUTPUT_TOKENS)


def build_request(
    model_id: str, prompt: str, schema: Mapping[str, Any], images: Sequence[tuple[str, bytes]] = (),
) -> ModelRequest:
    """The request body (the same shape as ``analysis.text.adapter.build_request``): one user message holding the instructions, the task
    and the fenced data, a structured answer by the schema, and the pictures as crops with opaque references in the order given."""
    if len(images) > MAX_IMAGES:
        raise ValueError(f"a request carries at most {MAX_IMAGES} images")
    body = {
        "model": model_id, "max_tokens": MAX_OUTPUT_TOKENS,
        "system": sc.SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    }
    request = ModelRequest(model_id=model_id, body=body)
    if not images:
        return request
    # the limits of a request (16 MiB a picture, 32 MiB in all) are kept whatever the sheet looked like
    fitted = fit_total_bytes([data for _name, data in images], per_image=MAX_IMAGE_BYTES, total=MAX_TOTAL_IMAGE_BYTES)
    return attach_images(request, [CropImage(crop_id=name, data=data) for (name, _old), data in zip(images, fitted)])


@dataclass(slots=True)
class SheetRun:
    """What one sheet's run made. ``description`` is the document to store, or ``None``; ``failure`` is the reason code of a sheet that
    ended with no description; ``pause`` is the spend reason (``overrun`` ...) the job is to pause for; ``call_ids`` are the journal rows."""

    description: dict[str, Any] | None = None
    state: str = "failed"
    failure: str | None = None
    pause: str | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    call_ids: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    launches: int = 0
    elapsed_ms: int = 0
    context: list[dict[str, Any]] = field(default_factory=list)

    @property
    def last_call_id(self) -> str | None:
        return self.call_ids[-1] if self.call_ids else None


class SheetInterrupted(Exception):
    """A typed spend error ended the run before a description: ``cause`` is the wrapper's error (``CallRefused``, ``CallLost``,
    ``OutcomeUnknown``) and ``run`` what was spent so far (so the item's counts are right)."""

    def __init__(self, cause: SpendError, run: SheetRun) -> None:
        super().__init__(cause.reason)
        self.cause = cause
        self.run = run


Checkpoint = Callable[[], None]


class _Caller:
    """The calls of one run: counts the launches, the tokens and the journal rows, and parses what comes back."""

    def __init__(self, caller: Any, item: WorkItem, route: CallRoute, consent: Consent | None, model_id: str, run: SheetRun,
                 checkpoint: Checkpoint) -> None:
        self.caller, self.item, self.route, self.consent, self.model_id, self.run = caller, item, route, consent, model_id, run
        self.checkpoint = checkpoint

    def attempt(
        self, prompt: str, schema: Mapping[str, Any], images: Sequence[tuple[str, bytes]], purpose: str, tries: int,
        accept: Callable[[Any], bool],
    ) -> Any | None:
        """Up to ``tries`` launches for one purpose within the sheet's budget (``run.py:162-214``). Answers the parsed answer that
        ``accept`` allows, or ``None``. A spend error that is not a proven non-delivery ends the run (:class:`SheetInterrupted`)."""
        tried = 0
        while tried < tries:
            if self.run.launches >= MAX_LAUNCHES or self.run.pause is not None:
                return None
            self.checkpoint()
            self.run.launches += 1
            request = build_request(self.model_id, prompt, schema, images)
            started = time.monotonic()
            record: dict[str, Any] = {
                "launch": self.run.launches, "purpose": purpose, "images": len(images), "prompt_chars": len(prompt),
                "ok": False, "error_kind": None,
            }
            self.run.calls.append(record)
            try:
                result = self.caller.call(
                    self.item, self.route, request, estimate=estimate_for(len(prompt), len(images)), consent=self.consent,
                )
            except CallFailed as failed:
                record.update(error_kind=failed.reason)
                self.run.call_ids.append(failed.call_id)
                self.run.elapsed_ms += int((time.monotonic() - started) * 1000)
                if failed.retry_safe:
                    tried += 1
                    continue  # nothing was processed: the same launch may be made again
                self.run.failure = failed.reason
                return None
            except (CallRefused, CallLost, OutcomeUnknown) as stopped:
                record.update(error_kind=stopped.reason)
                call_id = getattr(stopped, "call_id", None)
                if call_id:
                    self.run.call_ids.append(call_id)
                self.run.elapsed_ms += int((time.monotonic() - started) * 1000)
                raise SheetInterrupted(stopped, self.run) from None
            self.run.elapsed_ms += int((time.monotonic() - started) * 1000)
            response: ModelResponse = result.response
            self.run.call_ids.append(result.call_id)
            self.run.input_tokens += int(response.input_tokens)
            self.run.output_tokens += int(response.output_tokens)
            record.update(input_tokens=int(response.input_tokens), output_tokens=int(response.output_tokens), ok=True)
            if result.pause is not None:
                self.run.pause = result.pause.reason  # the reply is paid for and kept; no more calls for the job
            parsed = _parse(response.output_text)
            if parsed is not None and accept(parsed):
                return parsed
            record.update(ok=False, error_kind="INVALID_JSON")
            tried += 1
        return None


def _parse(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


# -- the context request (run.py:57-142) --------------------------------------------------------------------------------------------


def resolve_context(
    document: Mapping[str, Any], requests: Sequence[Mapping[str, Any]], material: SheetMaterial, facts: pk.SheetFacts,
) -> dict[str, Any]:
    """Execute the model's requests inside the two versions: the text, the extra pictures, a log (``run.py:57-114``). A request the
    program does not understand is rejected and logged, never executed."""
    by_id = {c["id"]: c for c in document["candidates"]}
    transform = document.get("transform") or geo.IDENTITY
    lines: list[str] = []
    images: list[tuple[str, bytes]] = []
    log: list[dict[str, Any]] = []
    texts: dict[str, list[str]] = {"A": [], "B": []}
    for request in list(requests)[:MAX_CONTEXT_REQUESTS]:
        kind, value, side = request["kind"], (request.get("value") or "").strip(), request.get("side") or "AB"
        entry: dict[str, Any] = {"request": dict(request), "status": "done", "found": []}
        if kind in ("mark", "rows"):
            if not _VALUE.match(value):
                entry.update(status="rejected", reason="недопустимое значение запроса")
                log.append(entry)
                continue
            hits = material.find_marks({"A": facts.version_a, "B": facts.version_b}, [value], skip_pages={}, limit=4)
            hits = [h for h in hits if side == "AB" or h["side"] == side]
            if not hits:
                lines.append(f"- Запрос {kind} «{value}» ({side}): в двух версиях не найдено.")
            for hit in hits:
                label = f" ({hit['page_label']})" if hit.get("page_label") else ""
                lines.append(f"- «{value}»: {hit['side']}, стр. PDF {hit['page']}{label}: {pk.cell(hit['text'], 900)}")
                texts[hit["side"]].append(str(hit["text"]))
                entry["found"].append({"side": hit["side"], "page": hit["page"], "bbox": hit["bbox"]})
                if len(images) < MAX_EXTRA_IMAGES and hit.get("bbox"):
                    x0, y0, x1, y1 = hit["bbox"]
                    profile = facts.page_profile_a if hit["side"] == "A" else facts.page_profile_b
                    data = material.crop(profile, [x0 - 250, y0 - 4, x1 + 250, y1 + 4], long_side_px=IMAGE_MAX_PX)
                    if data is not None:
                        name = f"IX{len(images) + 1}"
                        images.append((name, data))
                        lines[-1] += f" Изображение: {name}."
        elif kind == "zoom":
            candidate = by_id.get(value)
            if not candidate or not (candidate.get("context_a") or candidate.get("region_a") or candidate.get("area")):
                entry.update(status="rejected", reason="нет такого кандидата")
                log.append(entry)
                continue
            box_a = candidate.get("context_a") or candidate.get("region_a") or candidate["area"]
            for each in (["A", "B"] if side == "AB" else [side]):
                if len(images) >= MAX_EXTRA_IMAGES:
                    break
                box = box_a if each == "A" else (
                    candidate.get("context_b") or candidate.get("region_b") or geo.a_to_b_page(transform, box_a)
                )
                long_side = min(IMAGE_MAX_PX, max(1, int(max(box[2] - box[0], box[3] - box[1], 1) * 400 / 72)))
                profile = facts.page_profile_a if each == "A" else facts.page_profile_b
                data = material.crop(profile, box, long_side_px=long_side)
                if data is not None:
                    name = f"IX{len(images) + 1}"
                    images.append((name, data))
                    lines.append(f"- Увеличение {value}, сторона {each}: изображение {name}.")
        else:
            entry.update(status="rejected", reason="неизвестный вид запроса")
        log.append(entry)
    return {"text": "\n".join(lines), "images": images, "log": log, "texts": texts}


def _addendum_prompt(base: str, document: Mapping[str, Any], extra: Mapping[str, Any], first: Mapping[str, Any]) -> str:
    """``run.py:125-132``."""
    body = (extra["text"] or "- ничего не найдено") + "\n\nПредварительный ответ (JSON):\n" + json.dumps(first, ensure_ascii=False)
    begin, end = pk.boundary(str(document["packet_id"]) + "-ctx", base + body)
    attached = ", ".join(name for name, _ in extra["images"]) or "нет"
    return (
        base + "\nДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ по твоим запросам — только страницы этих же двух версий. "
        f"Новые изображения приложены после прежних: {attached}.\n{begin}\n{body}\n{end}\n"
        "Верни полный окончательный ответ по той же схеме (все пункты, не только изменённые); context_requests — пустой список.\n"
    )


def _coverage_prompt(base: str, document: Mapping[str, Any], missing: Sequence[str], first: Mapping[str, Any]) -> str:
    """``run.py:135-142``."""
    body = "Не разобраны записи: " + ", ".join(missing) + "\n\nПредварительный ответ (JSON):\n" + json.dumps(first, ensure_ascii=False)
    begin, end = pk.boundary(str(document["packet_id"]) + "-cov", base + body)
    return (
        base + "\nДОРАЗБОР: в предварительном ответе часть записей не попала ни в changes, ни в unresolved, ни в excluded.\n"
        f"{begin}\n{body}\n{end}\n"
        "Верни полный окончательный ответ по той же схеме: каждую запись отнеси к changes, unresolved или excluded; "
        "прежние пункты сохрани. context_requests — пустой список.\n"
    )


# -- a pair ---------------------------------------------------------------------------------------------------------------------


def describe_pair(
    caller: Any, item: WorkItem, route: CallRoute, consent: Consent | None, model_id: str, packet: pk.Packet,
    material: SheetMaterial, facts: pk.SheetFacts, *, checkpoint: Checkpoint, recorded: bool,
) -> SheetRun:
    """Describe one sheet pair (``run.py:147-272``). Returns the run; raises :class:`SheetInterrupted` on a typed spend error."""
    run = SheetRun()
    started = time.monotonic()
    document = packet.document
    calls = _Caller(caller, item, route, consent, model_id, run, checkpoint)
    primary_images = [(i["id"], packet.image_bytes[i["id"]]) for i in packet.images]

    def acceptable(answer: Any) -> bool:
        return bool(check(document, answer).get("ok"))

    answer = calls.attempt(packet.prompt, sc.SHEET_CHANGES_SCHEMA, primary_images, "primary", MAX_LAUNCHES, acceptable)
    extra: dict[str, Any] | None = None
    requests: list[Any] = []
    # one context round: the program executes what the model asked for, and the model answers again (run.py:226-236)
    if answer is not None and answer.get("context_requests") and run.launches < MAX_LAUNCHES and run.pause is None:
        requests = list(answer["context_requests"])
        extra = resolve_context(document, requests, material, facts)
        document["_extra_texts"] = extra["texts"]
        document["_extra_images"] = [name for name, _ in extra["images"]]
        keep = primary_images[: max(0, MAX_IMAGES - len(extra["images"]))]
        followup = calls.attempt(
            _addendum_prompt(packet.prompt, document, extra, answer), sc.SHEET_CHANGES_SCHEMA, [*keep, *extra["images"]], "context", 1,
            acceptable,
        )
        if followup is not None:
            answer = followup
    if answer is not None:
        requests = requests or list(answer.get("context_requests") or [])
        answer["context_requests"] = []
    # the model left candidates with no decision: one pass over them, taken if it leaves fewer (run.py:240-249)
    missing = (check(document, answer).get("coverage") or {}).get("not_reviewed") if answer is not None else None
    if missing and run.launches < MAX_LAUNCHES and run.pause is None:
        keep = primary_images[: max(0, MAX_IMAGES - len((extra or {}).get("images", [])))]
        third = calls.attempt(
            _coverage_prompt(packet.prompt, document, missing, answer), sc.SHEET_CHANGES_SCHEMA,
            [*keep, *(extra or {}).get("images", [])], "coverage", 1, acceptable,
        )
        if third is not None and len(check(document, third)["coverage"]["not_reviewed"]) < len(missing):
            third["context_requests"] = []
            answer = third
    run.elapsed_ms = max(run.elapsed_ms, int((time.monotonic() - started) * 1000))
    run.context = list((extra or {}).get("log", []))
    if answer is None:
        run.failure = run.failure or "model_answer_invalid"
        return run
    checked = check(document, answer)
    if not checked.get("ok"):
        run.failure = "model_answer_invalid"
        return run
    run.state = state_of(checked, document)
    run.description = build_description(document, checked, run.state, calls=run.calls, launches=run.launches, recorded=recorded,
                                        context=run.context)
    run.description["context_requests"] = requests
    run.failure = None  # a later phase that failed after a usable answer does not make the sheet fail
    return run


# -- a sheet that is in one version only -------------------------------------------------------------------------------------------


def describe_single(
    caller: Any, item: WorkItem, route: CallRoute, consent: Consent | None, model_id: str, *, kind: str, side: str, page: int,
    title: str, label: str, project: str, sheet_text: str, image: bytes | None, material_tag: str, checkpoint: Checkpoint,
    recorded: bool,
) -> SheetRun:
    """Describe an added or a removed sheet by itself (``single.py:73-102``, ``:117-197``): one call, up to ``MAX_LAUNCHES`` launches."""
    run = SheetRun()
    started = time.monotonic()
    words_text = sheet_text[: SINGLE_TEXT_LIMIT]
    prompt = sc.SINGLE_PROMPT.format(
        what="появился новый лист" if kind == "added" else "лист удалён (был в прежней версии)",
        verb="добавлено" if kind == "added" else "убрано", title=title or "—", side=side, label=label, page=page,
        project=project or "—", limit=SINGLE_TEXT_LIMIT, text=words_text or "(текстового слоя нет)",
    )
    images = [("I1", image)] if image else []
    calls = _Caller(caller, item, route, consent, model_id, run, checkpoint)

    def acceptable(answer: Any) -> bool:
        return (
            not sc.validate_answer(answer, sc.SINGLE_SCHEMA) and bool(str(answer["summary"]).strip())
        )

    answer = calls.attempt(prompt, sc.SINGLE_SCHEMA, images, "single", MAX_LAUNCHES, acceptable)
    run.elapsed_ms = max(run.elapsed_ms, int((time.monotonic() - started) * 1000))
    if answer is None:
        run.failure = run.failure or "model_answer_invalid"
        return run
    checked = check_single(answer, sheet_text)
    packet_id = hashlib.sha256(f"{material_tag}|{kind}|{prompt}".encode()).hexdigest()[:16]
    run.state = "done"
    run.description = build_single_description(
        kind, checked, packet_id=packet_id, side=side, page=page, calls=run.calls, launches=run.launches, recorded=recorded,
    )
    return run
