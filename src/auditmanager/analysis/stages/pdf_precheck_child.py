"""Standalone isolated page interpreter. Protocol only on stdout; no diagnostics.

Extracted text is an in-process preparation receipt, not an execution-journal field.
The parent validates it and publishes the existing prepared artifacts afterwards.
"""

from __future__ import annotations

import json
import os
import resource
import signal
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


def _emit(kind: str, **payload: Any) -> None:
    sys.stdout.write(json.dumps({"kind": kind, **payload}, ensure_ascii=False, allow_nan=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    settings = json.loads(sys.argv[1])
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    memory = int(settings["address_space_bytes"])
    cpu = int(settings["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    # Remain time-bounded even if the worker disappears before it can kill us.
    signal.setitimer(signal.ITIMER_REAL, float(settings["wall_seconds"]))
    # -I ignores PYTHONPATH and the cwd. Import this exact deployed source tree,
    # rather than a different worktree registered in a shared editable environment.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import pdfplumber

    from auditmanager.analysis.stages.extraction import (
        _document_heap, _extract_page, _release, probe_envelope,
    )
    from auditmanager.shared.errors import DomainError

    _emit("ready")
    try:
        source = f"/proc/self/fd/{int(settings['descriptor'])}"
        count = probe_envelope(source)
        if (not 0 < count <= settings["max_pages"] or
                settings["expected_page_count"] is not None
                and count != settings["expected_page_count"]):
            _emit("failed", reason="page_count_disagreement")
            return 1
        _emit("document", page_count=count)
        characters = 0
        with _document_heap(), pdfplumber.open(source) as pdf:
            pdf.doc.caching = False
            if len(pdf.pages) != count:
                _emit("failed", reason="page_count_disagreement")
                return 1
            for ordinal, page in enumerate(pdf.pages, start=1):
                _emit("page_started", page_number=ordinal)
                try:
                    # This property runs PDFPageInterpreter over every page operator,
                    # fonts and Form XObjects, even for a page without embedded text.
                    _ = page.objects
                    extracted = _extract_page(page, ordinal)
                    characters += extracted.char_count
                    if (extracted.char_count > settings["max_page_characters"] or
                            characters > settings["max_document_characters"]):
                        _emit("failed", reason="pdf_precheck_limits")
                        return 1
                    _emit("page", page=asdict(extracted))
                finally:
                    _release(page)
        _emit("complete", page_count=count)
        return 0
    except MemoryError:
        _emit("failed", reason="pdf_precheck_limits")
        return 1
    except DomainError as exc:
        # Only classifiers cross the process boundary. The parent screens them.
        _emit("failed", reason=exc.detail_fields.get("reason", "source_unreadable"))
        return 1
    except Exception:  # noqa: BLE001 - parser failures become a controlled refusal
        _emit("failed", reason="source_unreadable")
        return 1


if __name__ == "__main__":
    os._exit(main())
