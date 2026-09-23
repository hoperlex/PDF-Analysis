"""The re-recognition runner: the only place in this context that spends money.

`R-19` re-recognises the pages whose text is the recognition model's own reasoning. `R-27`
authorises the stand's own provider credential for it and `R-29` caps a wave at roughly five
dollars. This module is where those three meet, and it is deliberately the only file in
`auditmanager.norms` that knows a provider exists.

    # what it would cost and what it would read, with no call made
    PYTHONPATH=src .venv/bin/python -m auditmanager.norms \\
        --corpus /path/to/corpus --ledger /path/to/repairs.json --dry-run

    # the real run, with the credential injected for that command only
    set -a; . infra/deploy/env/provider.env; set +a
    PYTHONPATH=src .venv/bin/python -m auditmanager.norms \\
        --corpus /path/to/corpus --ledger /path/to/repairs.json --ceiling-usd 5.00

**The credential is read from the process environment and from nowhere else.** Not from a
path this module knows, not from a lane `.env`, and it is never printed — not into the
ledger, not into an error, not into the summary. That is `live.py`'s rule, restated here
because this runner is reached by hand and a hand-run is where a credential gets echoed.
`D-42` measured `docker compose config` printing such a value in clear; the same care applies.

**Three refusals before a single call, and each of them has cost somebody a wave.**

*A proxy URL with no host.* ``ProxySettings`` checks only that the string starts with
``http://`` or ``https://``, so ``http://:59990`` is accepted and fails later as a transport
error that reads like an outage. It is not an outage; it is a lane pointed at nothing.

*A transport that prices nothing.* The proxy returns the real spend for a call, and the
ledger's whole answer to *"what did this cost"* is that number. A run whose calls come back
unpriced is not a cheap run — it is a run that **cannot say** what it spent, and under `R-29`
that is the same as not knowing whether the ceiling was crossed. It stops on the first one
unless the operator says otherwise, because a local stub of the proxy's contract answers
exactly that way and looks, from here, like a very good deal.

*The ceiling.* Checked **before** each call against what has already been spent and **after**
each call against what it actually cost, which is ``cost.py``'s rule and catches two different
failures: a run already at the ceiling never issues another request, and one call far more
expensive than expected halts the run rather than being noticed in a bill.

**A partially completed run is resumable and never re-spends.** The ledger is written after
every page, and a re-run skips every block already in it. Five waves of this programme have
lost work to a session that died mid-task; a paid run that has to start over is that lesson
with an invoice attached.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _datetime
import io
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from auditmanager.norms.corpus_source import degenerate_pages
from auditmanager.norms.repair import (
    LEDGER_VERSION,
    PageRepair,
    RepairLedger,
    ledger_of,
)
from auditmanager.norms.rerecognition import (
    RECOGNITION_SYSTEM_PROMPT,
    PageToRecognise,
    RecognisedPage,
    rerecognise,
)

#: `R-29`'s first stopping condition, as the default rather than as a paragraph.
DEFAULT_CEILING_USD: float = 5.00

#: The render resolution for a crop. 150 dpi over an A4 page is 1241×1754, which is what the
#: original recognition pass worked from and is enough for the 8 pt footnotes in these norms.
RENDER_DPI: int = 150

ENV_BASE_URL = "PROXY_LLM_BASE_URL"
ENV_TOKEN = "PROXY_LLM_TOKEN"
ENV_MODEL = "PROXY_LLM_MODEL"


class RunRefused(RuntimeError):
    """The run stopped before or during spending, and says why in words, never in values."""


def _now() -> str:
    return _datetime.datetime.now(tz=_datetime.timezone.utc).isoformat(timespec="seconds")


def render_crop_png(crop: bytes, *, dpi: int = RENDER_DPI) -> bytes:
    """One single-page crop PDF, rendered to PNG.

    `pdfplumber` is the repository's pinned PDF library (`OD-01`, MIT over MIT `pdfminer.six`)
    and it already carries the rasteriser. Nothing is added to `pyproject.toml` for this.
    """
    import pdfplumber

    with pdfplumber.open(io.BytesIO(crop)) as document:
        if not document.pages:
            raise RunRefused("a crop carries no page, so there is nothing to re-recognise")
        image = document.pages[0].to_image(resolution=dpi)
        buffer = io.BytesIO()
        image.original.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


class ProxyPageRecogniser:
    """A :class:`~auditmanager.norms.rerecognition.PageRecogniser` over the LLM proxy.

    It builds the body the proxy adapter translates and hands the adapter the call. The
    adapter is imported here and nowhere else in this context: `norms` owns a port, and the
    composition of that port with a transport is this module's whole job.
    """

    __slots__ = ("_adapter", "_model", "_max_output_tokens", "_dpi")

    def __init__(self, *, base_url: str, token: str, model: str, max_output_tokens: int, dpi: int) -> None:
        from auditmanager.analysis.text import ProxyAdapter, ProxySettings

        self._adapter = ProxyAdapter(ProxySettings(base_url=base_url, token=token, model=model))
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._dpi = dpi

    def recognise(self, page: PageToRecognise) -> RecognisedPage:
        from auditmanager.analysis.text import ModelRequest

        png = render_crop_png(page.crop, dpi=self._dpi)
        encoded = base64.b64encode(png).decode("ascii")
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_output_tokens,
            "system": RECOGNITION_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                    ],
                }
            ],
        }
        response = self._adapter.complete(ModelRequest(model_id=self._model, body=body))
        return RecognisedPage(
            text=response.output_text,
            model=self._model,
            stop_reason=response.stop_reason,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.reported_cost_usd,
        )


def resolve_transport(environment: dict[str, str] | None = None) -> tuple[str, str, str]:
    """The three proxy values, or a refusal that names the missing one and never its value."""
    source = os.environ if environment is None else environment
    base_url = (source.get(ENV_BASE_URL) or "").strip()
    token = (source.get(ENV_TOKEN) or "").strip()
    model = (source.get(ENV_MODEL) or "").strip()

    missing = [
        name
        for name, value in ((ENV_BASE_URL, base_url), (ENV_TOKEN, token), (ENV_MODEL, model))
        if not value
    ]
    if missing:
        raise RunRefused(
            "the provider credential is not in this process's environment: "
            + ", ".join(sorted(missing))
            + " is unset. It is injected for the command and never read from a file here."
        )

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise RunRefused(
            f"{ENV_BASE_URL} names no host. A URL of the form 'http://:<port>' is accepted by "
            f"ProxySettings, which checks only the scheme, and then fails at call time as a "
            f"transport error that reads like a provider outage. It is a lane pointed at "
            f"nothing, and a paid run does not start against one."
        )
    return base_url, token, model


def _load_ledger(path: Path) -> RepairLedger | None:
    if not path.is_file():
        return None
    return RepairLedger.from_document(json.loads(path.read_text(encoding="utf-8")))


def _write_ledger(path: Path, ledger: RepairLedger) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ledger.as_json(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="auditmanager.norms", description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True, help="the corpus root directory")
    parser.add_argument("--ledger", type=Path, required=True, help="where the repair ledger is written")
    parser.add_argument("--snapshot-id", default="", help="the base corpus snapshot the ledger is taken against")
    parser.add_argument("--ceiling-usd", type=float, default=DEFAULT_CEILING_USD)
    parser.add_argument("--max-output-tokens", type=int, default=8000)
    parser.add_argument("--dpi", type=int, default=RENDER_DPI)
    parser.add_argument("--limit", type=int, default=0, help="stop after this many pages; 0 means all")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="enumerate and render, make no call, spend nothing",
    )
    parser.add_argument(
        "--allow-unpriced",
        action="store_true",
        help=(
            "continue when the transport reports no cost. Off by default: a run that cannot "
            "say what it spent cannot be held to R-29's ceiling, and a local stub of the "
            "proxy contract answers exactly this way."
        ),
    )
    args = parser.parse_args(argv)

    pages = degenerate_pages(args.corpus)

    if args.dry_run:
        rendered = 0
        crop_bytes = png_bytes = 0
        for page in pages:
            png = render_crop_png(page.crop, dpi=args.dpi)
            rendered += 1
            crop_bytes += len(page.crop)
            png_bytes += len(png)
            if args.limit and rendered >= args.limit:
                break
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "pages": rendered,
                    "crop_bytes": crop_bytes,
                    "png_bytes": png_bytes,
                    "spent_usd": 0.0,
                },
                indent=2,
            )
        )
        return 0

    base_url, token, model = resolve_transport()
    recogniser = ProxyPageRecogniser(
        base_url=base_url,
        token=token,
        model=model,
        max_output_tokens=args.max_output_tokens,
        dpi=args.dpi,
    )

    existing = _load_ledger(args.ledger)
    repairs: list[PageRepair] = list(existing.repairs) if existing is not None else []
    done = {repair.key for repair in repairs}
    snapshot_id = args.snapshot_id or (existing.base_snapshot_id if existing else "")
    spent = sum(repair.cost_usd for repair in repairs)
    attempted = 0
    stopped = ""

    for page in pages:
        if (page.document_slug, page.block_id) in done:
            continue
        if args.limit and attempted >= args.limit:
            stopped = "limit reached"
            break
        if spent >= args.ceiling_usd:
            # Before the call, so a run already at the ceiling never issues another request.
            stopped = "ceiling reached before the call"
            break

        repair = rerecognise(page, recogniser, now=_now())
        repairs.append(repair)
        attempted += 1
        spent += repair.cost_usd
        _write_ledger(
            args.ledger, ledger_of(snapshot_id, _now(), repairs)
        )

        if repair.unpriced_attempts and not args.allow_unpriced:
            stopped = (
                "the transport priced nothing for this call, so this run cannot state what it "
                "spent. Re-run with --allow-unpriced only if the transport is known not to "
                "charge."
            )
            break
        if spent > args.ceiling_usd:
            # After the call, on measured usage, so one unexpectedly expensive call halts.
            stopped = "ceiling exceeded by the last call"
            break

    ledger = ledger_of(snapshot_id, _now(), repairs)
    _write_ledger(args.ledger, ledger)
    print(
        json.dumps(
            {
                "version": LEDGER_VERSION,
                "ledger": str(args.ledger),
                "pages_in_ledger": len(ledger.repairs),
                "attempted_this_run": attempted,
                "repaired": len(ledger.applied),
                "still_degenerate": len(ledger.still_degenerate),
                "unusable": len(ledger.unusable),
                "unpriced_attempts": ledger.unpriced_attempts,
                "spent_usd": round(ledger.total_cost_usd, 4),
                "ceiling_usd": args.ceiling_usd,
                "stopped": stopped or "every page in scope was read",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not stopped or stopped.startswith(("limit", "every")) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunRefused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        raise SystemExit(2) from None
