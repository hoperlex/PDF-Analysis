"""Window equality between the embedder and the bake-off runner, on the real tokenizer.

HEAVY STEP (W54-FREEZE-01): run only through ``infra/norms-worker/check-windows.sh`` inside the
rebuilt norms-worker image, with the network absent, the checkout mounted read-only at
``/work`` and the corpus drop read-only at ``/corpus``.

For every text it is given, it computes the runner's windows
(``/work/tools/norms/embedding_bakeoff.py``'s ``_windows``) and the baked embedder's
(``auditmanager.norms.embedding.windowing.window_spans``) with the ``BAAI/bge-m3`` tokenizer of
the frozen revision, and requires the window texts, the content-token count and the inference
count to be equal. The texts are

* the synthetic set of ``tokenizer_recording.synthetic_texts`` (always), and
* with ``--corpus``, every canonical paragraph and every chunk of the drop's projection.

With ``--record PATH`` it also writes a recording of the real tokenizer's answers over the
synthetic set; committed under ``tests/integration/norms/embedding/recordings/``, it lets the
container-free test replay the real offsets. No corpus text is ever recorded.

The last line is ``norms-worker windows equal: <n> texts, <w> windows`` and the exit status 0,
or one ``MISMATCH`` line per differing text and exit status 1.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _corpus_texts(corpus: Path) -> Iterator[str]:
    from auditmanager.norms.corpus_source import open_corpus_projection

    projection = open_corpus_projection(corpus)
    for document in projection.iter_documents():
        for paragraph in document.paragraphs:
            yield paragraph.text
        for chunk in document.chunks:
            yield chunk.text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, default=Path("/work/tools/norms/embedding_bakeoff.py"))
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args(argv)

    from transformers import AutoTokenizer

    from auditmanager.norms.embedding import windowing
    from auditmanager.norms.embedding.encoder import require_offline
    from auditmanager.norms.embedding.profile import (
        MAX_TOKENS,
        MODEL_REPOSITORY,
        MODEL_REVISION,
        OVERLAP_TOKENS,
    )

    require_offline()
    recording = _load(HERE / "tokenizer_recording.py", "norms_worker_tokenizer_recording")
    runner = _load(args.runner, "norms_worker_bakeoff_runner")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_REPOSITORY, revision=MODEL_REVISION)
    print(
        f"runner {hashlib.sha256(args.runner.read_bytes()).hexdigest()} "
        f"port {hashlib.sha256(Path(windowing.__file__).read_bytes()).hexdigest()}",
        flush=True,
    )

    def texts() -> Iterator[str]:
        yield from recording.synthetic_texts()
        if args.corpus is not None:
            yield from _corpus_texts(args.corpus)

    compared = windows = mismatches = 0
    for text in texts():
        expected, expected_content, expected_inference = runner._windows(
            tokenizer, text, MAX_TOKENS, OVERLAP_TOKENS, prefix=""
        )
        spans, content, inference = windowing.window_spans(tokenizer, text)
        actual = [text[span.char_start : span.char_end] for span in spans]
        compared += 1
        windows += len(actual)
        if (actual, content, inference) != (expected, expected_content, expected_inference):
            mismatches += 1
            key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            print(
                f"MISMATCH text {key}: runner {len(expected)} windows {expected_content}/"
                f"{expected_inference} tokens, port {len(actual)} windows {content}/{inference}",
                file=sys.stderr,
            )

    if args.record is not None:
        recorder = recording.RecordingTokenizer(tokenizer)
        synthetic = recording.synthetic_texts()
        for text in synthetic:
            windowing.window_spans(recorder, text)
        import tokenizers
        import transformers

        recording.write_recording(
            args.record,
            recorder.document(
                source=(
                    f"{MODEL_REPOSITORY}@{MODEL_REVISION} tokenizers=={tokenizers.__version__} "
                    f"transformers=={transformers.__version__}"
                ),
                texts=synthetic,
                limit=MAX_TOKENS,
                overlap=OVERLAP_TOKENS,
            ),
        )
        print(f"recorded {len(synthetic)} synthetic texts to {args.record}", flush=True)

    if mismatches:
        print(f"norms-worker windows DIFFER: {mismatches} of {compared} texts", file=sys.stderr)
        return 1
    print(f"norms-worker windows equal: {compared} texts, {windows} windows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
