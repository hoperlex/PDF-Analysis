"""A replay-only diagnostic runner for the recorded text-analysis corpus.

Live provider effects require committed Run/Job/Attempt authority and the durable call
journal owned by :mod:`auditmanager.runs.executor`. This standalone module has neither,
so it deliberately refuses ``AUDITMANAGER_PROVIDER_MODE=live`` before constructing a
provider adapter. Public alpha acceptance exercises the durable Run path instead.

    # replay - the default, and what every suite does
    PYTHONPATH=src .venv/bin/python -m auditmanager.analysis.text \\
        fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json

    # optionally write a normalized copy of the replayed exchange
    PYTHONPATH=src .venv/bin/python -m auditmanager.analysis.text \\
        fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json \\
        --capture /tmp/auditmanager-recorded-capture

``--capture`` writes the response through
:func:`auditmanager.analysis.text.recorded.recording_document`, which is the only
supported constructor and which has no parameter that could stamp a provider mode into
the file. Capturing therefore cannot produce a recording that claims to be live.

Nothing here initializes a live client or reads a provider credential.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from auditmanager.analysis.text.adapter import ModelRequest, ModelResponse
from auditmanager.analysis.text.config import ProviderMode, load_provider_config
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.stage import run_text_analysis
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId


class _Capturing:
    """Wraps an adapter and keeps the last exchange, so it can be written out.

    ``provider_mode`` is forwarded from the wrapped adapter rather than stored, so
    wrapping cannot relabel a run.
    """

    __slots__ = ("_inner", "exchange")

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.exchange: tuple[ModelRequest, ModelResponse] | None = None

    @property
    def provider_mode(self) -> ProviderMode:
        return self._inner.provider_mode

    def complete(self, request: ModelRequest) -> ModelResponse:
        response = self._inner.complete(request)
        self.exchange = (request, response)
        return response


def _build_adapter(config: Any) -> Any:
    if config.mode is ProviderMode.LIVE:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the standalone text-analysis runner is replay-only",
            reason="durable_call_journal_required",
        )
    return RecordedAdapter()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="auditmanager.analysis.text", description=__doc__)
    parser.add_argument("text_layer", type=Path, help="a prepared.text_layer JSON document")
    parser.add_argument(
        "--capture",
        type=Path,
        default=None,
        metavar="DIR",
        help="write the response as a recording into DIR",
    )
    args = parser.parse_args(argv)

    config = load_provider_config()
    document = json.loads(args.text_layer.read_text(encoding="utf-8"))
    adapter = _Capturing(_build_adapter(config))

    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=document,
        adapter=adapter,
        config=config,
    )

    report: dict[str, Any] = {
        "status": outcome.status,
        "metrics": dict(outcome.metrics),
        "model_calls": [call.as_dict() for call in outcome.model_calls],
    }
    if outcome.error is not None:
        report["error"] = outcome.error.envelope("manual-run").as_dict()
    if outcome.artifact is not None:
        report["artifact"] = outcome.artifact
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.capture is not None and adapter.exchange is not None:
        request, response = adapter.exchange
        args.capture.mkdir(parents=True, exist_ok=True)
        path = args.capture / f"{request.request_sha256}.json"
        path.write_text(
            json.dumps(
                recording_document(
                    request=request,
                    output_text=response.output_text,
                    stop_reason=response.stop_reason,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency_ms=response.latency_ms,
                    note="captured from a manual run",
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"captured recording {path.name}", file=sys.stderr)

    return 0 if outcome.status != "failed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DomainError as error:
        # The envelope is the only externally visible failure shape, and its screen
        # has already refused anything carrying a path, a URL or a credential.
        print(json.dumps(error.envelope("manual-run").as_dict(), ensure_ascii=False))
        raise SystemExit(1) from None
