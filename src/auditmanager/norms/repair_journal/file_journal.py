"""The local half of the paid repair journal: an append-only, fsynced file on this machine.

`R-98` (K-11): the journal is a local fsynced file, with no off-host mirror, kept outside any
Docker volume (``.local/norms/repairs/`` by default). `R-106`'s write order puts it first:

1. the **intent** is appended and fsynced here;
2. the ``norm_repair_call`` row is committed;
3. the call is dispatched;
4. every **effect** (the checkpointed response, the settlement) commits to the database
   first and is then appended here.

So the file always holds every intent that may have been dispatched, and never an effect the
database does not hold — except after the database volume is lost and restored from an older
dump, which is exactly the case the file is there to reconcile forward.

**Response bytes live here, not in the database.** `0018`'s row pins ``response_sha256`` only
(``test_schema_shape.py`` bans a model payload from every table). The body is written to
``responses/<nrc id>.body`` — temporary name, fsync, rename, directory fsync — *before* the
database moves the row to ``response_received``, so a checkpointed row always has its bytes,
and a kill after acceptance replays them instead of paying again.

**Each line is chained.** A line is ``{seq, kind, at, body, prev, digest}``; ``digest`` is the
SHA-256 of the canonical JSON of the other five fields and ``prev`` is the previous line's
digest. A torn final line (no newline: the process died inside the write) is dropped — by the
write order it described a step that had not happened yet, or an effect the database already
holds — and the drop is reported. Any other broken, reordered or missing line refuses the
start: the file is the evidence of what may have been paid for, and it is not guessed at.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Self

from .model import CallIntent, JournalCall, JournalRefused, Settlement

FORMAT: str = "norm-repair-journal/1"
JOURNAL_FILENAME: str = "journal.jsonl"
LOCK_FILENAME: str = "journal.lock"
RESPONSES_DIRNAME: str = "responses"
GENESIS: str = "0" * 64

#: Paths a journal must never live under: a Docker volume is lost with the database it holds.
FORBIDDEN_ROOTS: tuple[str, ...] = ("/var/lib/docker",)


def _canonical(document: Any) -> bytes:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class LocalJournal:
    """One journal directory. Open it, read what it holds, append, close."""

    def __init__(self, directory: Path) -> None:
        resolved = directory.resolve()
        for root in FORBIDDEN_ROOTS:
            if resolved == Path(root) or Path(root) in resolved.parents:
                raise JournalRefused(
                    f"the repair journal may not live under {root}: a Docker volume is lost "
                    "with the database it holds, and the journal is what reconciles that loss"
                )
        self.directory = resolved
        self.path = resolved / JOURNAL_FILENAME
        self.responses = resolved / RESPONSES_DIRNAME
        self._lock_handle: Any = None
        self._handle: Any = None
        self._seq = 0
        self._prev = GENESIS
        self.header: dict[str, Any] | None = None
        self.calls: dict[str, JournalCall] = {}
        self.sample_verdict: dict[str, Any] | None = None
        self.owner_decisions: list[dict[str, Any]] = []
        self.dropped_torn_tail = False

    # --- lifecycle ----------------------------------------------------------------------

    def open(
        self,
        *,
        base_snapshot: str | None = None,
        model: str | None = None,
        ceiling_usd: Decimal | None = None,
        now: str = "",
        read_only: bool = False,
    ) -> LocalJournal:
        """Lock, read and verify the file; write the header on first use.

        A writer takes the lock exclusively, so two runners never append to one journal; a
        reader takes it shared. A writer's header must agree with the one on file: a journal
        is bound to one base snapshot, one model and one ceiling.
        """
        if not read_only:
            created = not self.directory.exists()
            self.directory.mkdir(parents=True, exist_ok=True)
            self.responses.mkdir(exist_ok=True)
            if created:
                _fsync_directory(self.directory.parent)
            _fsync_directory(self.directory)
        elif not self.path.is_file():
            raise JournalRefused(f"no repair journal at {self.path}")
        lock_path = self.directory / LOCK_FILENAME
        if read_only and not lock_path.exists():
            self._lock_handle = None
        else:
            self._lock_handle = open(lock_path, "a+b")  # noqa: SIM115 - held until close()
            try:
                fcntl.flock(
                    self._lock_handle.fileno(),
                    (fcntl.LOCK_SH if read_only else fcntl.LOCK_EX) | fcntl.LOCK_NB,
                )
            except BlockingIOError:
                self._lock_handle.close()
                self._lock_handle = None
                raise JournalRefused(
                    "another repair runner holds this journal; one writer at a time"
                ) from None
        self._read(truncate_torn_tail=not read_only)
        if read_only:
            return self
        self._handle = open(self.path, "ab")  # noqa: SIM115 - held until close()
        if self.header is None:
            if base_snapshot is None or model is None or ceiling_usd is None:
                raise JournalRefused("a new journal needs its base snapshot, model and ceiling")
            self._append(
                "header",
                {
                    "format": FORMAT,
                    "base_snapshot": base_snapshot,
                    "model": model,
                    "ceiling_usd": str(ceiling_usd),
                },
                now,
            )
        else:
            expected = {
                "base_snapshot": base_snapshot,
                "model": model,
                "ceiling_usd": None if ceiling_usd is None else str(ceiling_usd),
            }
            for name, value in expected.items():
                if value is not None and self.header.get(name) != value:
                    raise JournalRefused(
                        f"this journal was opened for {name} {self.header.get(name)!r}, not "
                        f"{value!r}; a journal is bound to one base snapshot, model and ceiling"
                    )
        return self

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        if self._lock_handle is not None:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
            self._lock_handle.close()
            self._lock_handle = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # --- reading ------------------------------------------------------------------------

    def _read(self, *, truncate_torn_tail: bool) -> None:
        self.header = None
        self.calls = {}
        self.sample_verdict = None
        self.owner_decisions = []
        self._seq = 0
        self._prev = GENESIS
        if not self.path.is_file():
            return
        data = self.path.read_bytes()
        segments = data.split(b"\n")
        tail = segments.pop()
        if tail:
            # The last write never reached its newline. By the write order the step it
            # described had not happened (an intent) or the database already holds it (an
            # effect), so it is dropped and the file truncated to its last whole line.
            self.dropped_torn_tail = True
            if truncate_torn_tail:
                self._truncate(len(data) - len(tail))
        for index, segment in enumerate(segments):
            try:
                line = json.loads(segment)
                digest = line.pop("digest")
            except (ValueError, KeyError, AttributeError, TypeError):
                raise JournalRefused(f"journal line {index + 1} is not a journal record") from None
            if hashlib.sha256(_canonical(line)).hexdigest() != digest:
                raise JournalRefused(f"journal line {index + 1} fails its digest")
            if line.get("seq") != self._seq + 1 or line.get("prev") != self._prev:
                raise JournalRefused(
                    f"journal line {index + 1} breaks the chain: a line is missing, "
                    "duplicated or out of order"
                )
            self._seq = line["seq"]
            self._prev = digest
            self._apply(line["kind"], line.get("body") or {}, line.get("at") or "", index + 1)

    def _truncate(self, length: int) -> None:
        with open(self.path, "r+b") as handle:
            handle.truncate(length)
            handle.flush()
            os.fsync(handle.fileno())

    def _apply(self, kind: str, body: dict[str, Any], at: str, number: int) -> None:
        if kind == "header":
            if self.header is not None or body.get("format") != FORMAT:
                raise JournalRefused(f"journal line {number}: a second or foreign header")
            self.header = body
            return
        if self.header is None:
            raise JournalRefused(f"journal line {number}: a record before the header")
        if kind == "intent":
            intent = CallIntent.from_document(body)
            if intent.call_id in self.calls:
                raise JournalRefused(f"journal line {number}: a second intent for one call")
            self.calls[intent.call_id] = JournalCall(intent=intent)
            return
        if kind in ("response", "settled"):
            call = self.calls.get(str(body.get("call_id")))
            if call is None:
                raise JournalRefused(f"journal line {number}: an effect for an unknown call")
            if call.settlement is not None:
                raise JournalRefused(f"journal line {number}: an effect after the settlement")
            if kind == "response":
                if call.response_sha256 is not None:
                    raise JournalRefused(f"journal line {number}: a second response")
                call.response_sha256 = str(body["response_sha256"])
            else:
                call.settlement = Settlement.from_document(body["settlement"])
                call.settled_at = at
            return
        if kind == "sample_verdict":
            self.sample_verdict = body
            return
        if kind == "owner_decision":
            self.owner_decisions.append(body)
            return
        raise JournalRefused(f"journal line {number}: unknown record kind {kind!r}")

    # --- appending ----------------------------------------------------------------------

    def _append(self, kind: str, body: dict[str, Any], at: str) -> None:
        if self._handle is None:
            raise JournalRefused("the journal is not open for writing")
        line: dict[str, Any] = {
            "seq": self._seq + 1,
            "kind": kind,
            "at": at,
            "body": body,
            "prev": self._prev,
        }
        digest = hashlib.sha256(_canonical(line)).hexdigest()
        record = dict(line, digest=digest)
        self._handle.write(_canonical(record) + b"\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self._seq += 1
        self._prev = digest
        self._apply(kind, body, at, self._seq)

    def append_intent(self, intent: CallIntent) -> None:
        self._append("intent", intent.as_document(), intent.prepared_at)

    def append_response(self, call_id: str, response_sha256: str, at: str) -> None:
        self._append("response", {"call_id": call_id, "response_sha256": response_sha256}, at)

    def append_settled(self, call_id: str, settlement: Settlement, at: str) -> None:
        self._append("settled", {"call_id": call_id, "settlement": settlement.as_document()}, at)

    def append_sample_verdict(self, verdict: dict[str, Any], at: str) -> None:
        self._append("sample_verdict", verdict, at)

    def append_owner_decision(self, decision: dict[str, Any], at: str) -> None:
        self._append("owner_decision", decision, at)

    # --- response bytes -----------------------------------------------------------------

    def response_path(self, call_id: str) -> Path:
        return self.responses / f"{call_id}.body"

    def write_response(self, call_id: str, raw: bytes) -> str:
        """Write a response body durably and return its SHA-256. Never overwrites."""
        final = self.response_path(call_id)
        sha = hashlib.sha256(raw).hexdigest()
        if final.exists():
            if hashlib.sha256(final.read_bytes()).hexdigest() != sha:
                raise JournalRefused(f"{call_id}: a different response body is already on file")
            return sha
        temporary = final.with_suffix(".body.partial")
        with open(temporary, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, final)
        _fsync_directory(self.responses)
        return sha

    def has_response(self, call_id: str) -> bool:
        return self.response_path(call_id).is_file()

    def read_response(self, call_id: str, expected_sha256: str | None) -> bytes:
        path = self.response_path(call_id)
        if not path.is_file():
            raise JournalRefused(
                f"{call_id}: the checkpointed response body is missing from {self.responses}"
            )
        raw = path.read_bytes()
        if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise JournalRefused(f"{call_id}: the response body on file fails its SHA-256")
        return raw
