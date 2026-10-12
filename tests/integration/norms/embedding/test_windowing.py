"""The ported 512/64 windowing equals the bake-off runner's, and `D-127`'s full window set.

Equality is shown three ways that need no model runtime: on a synthetic fast tokenizer at the
profile's limits and at small limits that force every branch, and on **recorded** tokenizer
answers replayed by a tokenizer that refuses any unrecorded question — so the port must ask the
runner's questions, in the runner's order. The real ``BAAI/bge-m3`` recording is written in the
rebuilt image (``infra/norms-worker/check-windows.sh``); until it is committed its case is
skipped with that instruction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.norms.embedding import windowing
from auditmanager.norms.embedding.windowing import (
    WindowFacts,
    WindowingRefused,
    input_digest,
    paragraph_span,
    verify_window_set,
    window_spans,
)
from tests.integration.norms.embedding.support import (
    RECORDING,
    RECORDINGS,
    RUNNER,
    SYNTHETIC_SOURCE,
    FakeTokenizer,
    chunk,
    paragraph,
)

REAL_RECORDING = RECORDINGS / "bge-m3-5617a9f.v1.json"


def _texts() -> list[str]:
    texts = list(RECORDING.synthetic_texts())
    texts += [paragraph(seed, words) for seed, words in ((1, 3), (2, 40), (3, 400), (4, 900), (5, 2000))]
    texts += ["ёёёё " * 300, "Ё" * 5 + " слово" * 700, "a"]
    return texts


def _equal(tokenizer, text: str, limit: int, overlap: int) -> int:
    """The window count, or 0 when the runner refuses the text and the port refuses it too."""
    try:
        expected, expected_content, expected_inference = RUNNER._windows(
            tokenizer, text, limit, overlap, prefix=""
        )
    except ValueError as refusal:
        with pytest.raises(WindowingRefused) as port_refusal:
            window_spans(tokenizer, text, limit, overlap)
        assert str(port_refusal.value) == str(refusal)
        return 0
    spans, content, inference = window_spans(tokenizer, text, limit, overlap)
    assert [text[span.char_start : span.char_end] for span in spans] == expected
    assert (content, inference) == (expected_content, expected_inference)
    assert all(1 <= span.token_count <= limit for span in spans)
    return len(spans)


@pytest.mark.parametrize(("limit", "overlap"), [(512, 64), (64, 8), (16, 4), (8, 2)])
def test_windows_equal_the_runners_on_a_synthetic_fast_tokenizer(limit: int, overlap: int) -> None:
    windows = [_equal(FakeTokenizer(), text, limit, overlap) for text in _texts()]
    assert max(windows) > 1, "no text needed more than one window"
    assert windows.count(0) <= 2, "the runner refused more than the two ё-heavy texts"


def _replay_cases():
    paths = sorted(RECORDINGS.glob("*.v1.json"))
    assert paths, "no tokenizer recording is committed"
    return paths


@pytest.mark.parametrize("path", _replay_cases(), ids=lambda path: path.name)
def test_windows_equal_the_runners_on_recorded_offsets(path) -> None:
    recording = RECORDING.load_recording(path)
    texts = RECORDING.synthetic_texts()
    assert recording["text_sha256"] == [input_digest(text) for text in texts]
    multi = 0
    for text in texts:
        runner_tokenizer = RECORDING.ReplayTokenizer(recording)
        port_tokenizer = RECORDING.ReplayTokenizer(recording)
        expected = RUNNER._windows(
            runner_tokenizer, text, recording["limit"], recording["overlap"], prefix=""
        )
        spans, content, inference = window_spans(
            port_tokenizer, text, recording["limit"], recording["overlap"]
        )
        assert [text[span.char_start : span.char_end] for span in spans] == expected[0]
        assert (content, inference) == expected[1:]
        assert port_tokenizer.questions == runner_tokenizer.questions
        multi += len(spans) > 1
    assert multi >= 8


def test_the_replay_refuses_a_question_it_was_not_recorded_with() -> None:
    recording = RECORDING.load_recording(RECORDINGS / "synthetic-fake-tokenizer.v1.json")
    tokenizer = RECORDING.ReplayTokenizer(recording)
    with pytest.raises(RECORDING.RecordingMiss):
        window_spans(tokenizer, "a text no recording holds")
    with pytest.raises(RECORDING.RecordingMiss):
        tokenizer.encode("x", add_special_tokens=True, truncation=False)


def test_the_synthetic_recording_is_reproducible_from_the_fake_tokenizer() -> None:
    recorder = RECORDING.RecordingTokenizer(FakeTokenizer())
    texts = RECORDING.synthetic_texts()
    for text in texts:
        window_spans(recorder, text)
    fresh = recorder.document(source=SYNTHETIC_SOURCE, texts=texts, limit=512, overlap=64)
    committed = json.loads((RECORDINGS / "synthetic-fake-tokenizer.v1.json").read_text(encoding="utf-8"))
    assert committed == fresh


def test_the_real_tokenizer_recording_is_committed() -> None:
    if not REAL_RECORDING.exists():
        pytest.skip(
            "heavy step: run infra/norms-worker/check-windows.sh in the rebuilt image and commit "
            f"its bge-m3-5617a9f.v1.json as {REAL_RECORDING.relative_to(RECORDINGS.parents[4])}"
        )
    recording = RECORDING.load_recording(REAL_RECORDING)
    assert recording["source"].startswith("BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181 ")
    assert recording["special_tokens"] == 2


def test_the_port_is_a_line_for_line_copy_of_the_runner_control_flow() -> None:
    """Every runner statement that decides a window appears verbatim in the port."""
    import inspect

    runner = inspect.getsource(RUNNER._windows)
    port = inspect.getsource(windowing.window_spans)
    decisive = [
        "end = min(len(token_ids), start + limit)",
        "char_start = 0 if start == 0 else offsets[start][0]",
        "char_end = len(text) if end == len(token_ids) else offsets[end - 1][1]",
        "end -= max(1, encoded_count - limit)",
        "if end <= start or not value.strip():",
        "start = max(start + 1, end - overlap)",
        "if inference_count <= limit:",
        "len(token_ids) + special_tokens",
    ]
    for line in decisive:
        assert line in runner and line in port, line


@pytest.mark.parametrize(
    ("tokenizer", "text"),
    [
        (type("Slow", (), {"is_fast": False})(), "text"),
        (FakeTokenizer(), "   "),
    ],
)
def test_the_port_refuses_what_the_runner_refuses(tokenizer, text: str) -> None:
    with pytest.raises(ValueError):
        RUNNER._windows(tokenizer, text, 512, 64, prefix="")
    with pytest.raises(WindowingRefused):
        window_spans(tokenizer, text)


# --- paragraph spans and the full window set (`D-127`) ---------------------------------------


def test_a_window_touches_exactly_the_paragraphs_its_slice_overlaps() -> None:
    lengths = (5, 3, 4)  # "aaaaa\n\nbbb\n\ncccc": paragraphs at 0..5, 7..10, 12..16
    assert paragraph_span(lengths, 10, 0, 16) == (10, 12)
    assert paragraph_span(lengths, 10, 0, 5) == (10, 10)
    assert paragraph_span(lengths, 10, 4, 8) == (10, 11)
    assert paragraph_span(lengths, 10, 5, 8) == (11, 11)
    assert paragraph_span(lengths, 10, 12, 16) == (12, 12)
    with pytest.raises(WindowingRefused):
        paragraph_span(lengths, 10, 3, 3)


def _facts(item, tokenizer=None) -> list[WindowFacts]:
    spans, _, _ = window_spans(tokenizer or FakeTokenizer(), item.text)
    return [
        WindowFacts(
            window_ordinal=index,
            char_offset=span.char_start,
            char_length=span.char_end - span.char_start,
            token_count=span.token_count,
            paragraph_ordinal_first=paragraph_span(
                item.paragraph_lengths, item.paragraph_ordinal_first, span.char_start, span.char_end
            )[0],
            paragraph_ordinal_last=paragraph_span(
                item.paragraph_lengths, item.paragraph_ordinal_first, span.char_start, span.char_end
            )[1],
            input_sha256=input_digest(item.text[span.char_start : span.char_end]),
        )
        for index, span in enumerate(spans)
    ]


def _verify(item, windows) -> None:
    verify_window_set(
        label="chunk",
        text=item.text,
        paragraph_ordinal_first=item.paragraph_ordinal_first,
        paragraph_ordinal_last=item.paragraph_ordinal_last,
        paragraph_lengths=item.paragraph_lengths,
        windows=windows,
    )


LONG = chunk("doc", 0, (200, 260, 180), first=7)
SHORT = chunk("doc", 1, (12, 30), first=10)


def test_the_ports_windows_are_a_full_window_set() -> None:
    for item in (LONG, SHORT):
        windows = _facts(item)
        _verify(item, windows)
    assert len(_facts(LONG)) > 1 and len(_facts(SHORT)) == 1


def _one_character(item) -> list[WindowFacts]:
    return [
        WindowFacts(0, 0, 1, 1, item.paragraph_ordinal_first, item.paragraph_ordinal_first, input_digest(item.text[:1]))
    ]


def _shifted(item, window: WindowFacts, start: int) -> WindowFacts:
    """``window`` moved to start at ``start``, keeping its end, with a consistent digest and span."""
    end = window.char_offset + window.char_length
    first, last = paragraph_span(item.paragraph_lengths, item.paragraph_ordinal_first, start, end)
    return replace(
        window,
        char_offset=start,
        char_length=end - start,
        paragraph_ordinal_first=first,
        paragraph_ordinal_last=last,
        input_sha256=input_digest(item.text[start:end]),
    )


def _mutants(item):
    good = _facts(item)
    yield "one one-character window (D-127)", _one_character(item)
    yield "no window", []
    yield "the last window dropped", good[:-1]
    yield "the first window dropped", [replace(window, window_ordinal=index) for index, window in enumerate(good[1:])]
    yield "a gap between windows", [good[0], _shifted(item, good[1], good[0].char_offset + good[0].char_length + 1)] + good[2:]
    yield "windows that touch without overlapping", [good[0], _shifted(item, good[1], good[0].char_offset + good[0].char_length)] + good[2:]
    yield "an input digest of another slice", [replace(good[0], input_sha256=input_digest(item.text[1 : good[0].char_length]))] + good[1:]
    yield "a wrong paragraph span", [replace(good[0], paragraph_ordinal_last=good[0].paragraph_ordinal_last + 1)] + good[1:]
    yield "ordinals not 0..n-1", [replace(good[0], window_ordinal=1)] + good[1:]
    yield "over the token limit", [replace(good[0], token_count=513)] + good[1:]
    yield "zero tokens", [replace(good[0], token_count=0)] + good[1:]
    yield "past the end", good[:-1] + [replace(good[-1], char_length=good[-1].char_length + 1)]


@pytest.mark.parametrize(("name", "windows"), list(_mutants(LONG)), ids=[name for name, _ in _mutants(LONG)])
def test_anything_but_the_full_window_set_is_refused(name: str, windows) -> None:
    with pytest.raises(WindowingRefused):
        _verify(LONG, windows)


def test_a_chunk_whose_text_is_not_the_join_of_its_paragraphs_is_refused() -> None:
    broken = replace(SHORT, paragraph_lengths=(SHORT.paragraph_lengths[0] + 1, SHORT.paragraph_lengths[1] - 1))
    with pytest.raises(WindowingRefused, match="join"):
        _verify(broken, _facts(SHORT))
    with pytest.raises(WindowingRefused, match="layout"):
        _verify(replace(SHORT, paragraph_ordinal_last=SHORT.paragraph_ordinal_last + 1), _facts(SHORT))


def test_input_digest_is_sha256_of_utf8() -> None:
    assert input_digest("ё") == hashlib.sha256("ё".encode()).hexdigest()
