"""The pre-FastAPI response baseline: the journey, and the rules that make it comparable.

Wave 13 retires ``Router``/``dispatch``/``http.py``/``multipart.py`` and rebuilds the
twelve operations as FastAPI path operations. This module drives the **current, certified**
implementation the way ``tests/e2e/pc01/driver.py`` drives it -- ``Request.build`` plus
``dispatch`` over a real ``create_app()`` -- and records status, **every** response header
and the body bytes for each case.

After the rewrite, the FastAPI implementation must reproduce these bytes exactly. One path
is allowed to differ and is marked in its own record: see ``EXCEPTION_D7``.

Comparability without hiding a difference
-----------------------------------------
A response carries values that cannot repeat across runs: ULID identities the database
allocates, timestamps it stamps, and the correlation id the edge assigns. Those are
replaced by a **token**, and there are exactly two ways a value may earn one:

1. **The journey already knows it.** It supplied the value, or read it out of an earlier
   response in the same journey (``project_uid``, ``version_uid``, ``run_id``,
   ``finding_uid``, the cursor, ...). Substitution is by *exact value*, never by pattern.
2. **It sits under a declared field name and matches a pinned format.**
   :data:`TIMESTAMP_FIELDS` names them one by one and :data:`TIMESTAMP_FORMAT` /
   :data:`CORRELATION_FORMAT` are literal patterns written out here, not imported from the
   code under test. The value is checked against the pattern first and only then replaced,
   again by exact value.

Nothing is substituted by scanning a body for things that look generated. So a changed key
order, a changed separator, a changed message, a dropped field, a renamed constraint, a
moved status code or a different header is a byte difference and reddens the comparison.

``Content-Length`` is the one header given a token unconditionally. It is a function of the
body, the body is compared byte for byte, and the comparison separately asserts
``Content-Length == str(len(body))``. Pinning the number as well would only re-state the
body comparison -- and would go red for a token whose replacement happens to be a different
length, which is noise rather than signal.

Every literal in this file is a pin. Not one expectation is computed from the module it is
checking: ``OPERATING_CONSTRAINTS.md`` section 12 records three instances of that failure.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECORDS = Path(__file__).resolve().with_name("records")
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE_PDF = CORPUS / "ar_baseline.pdf"
NEGATIVE = CORPUS / "negative"

# --- pinned literals ---------------------------------------------------------------
# Each of these is written out here rather than imported from the code it describes.

#: ``#/components/schemas/CorrelationId`` as the edge assigns it: ``new_correlation_id``
#: emits ``cid-`` and 16 bytes of hex. Pinned, not imported.
CORRELATION_FORMAT = re.compile(r"^cid-[0-9a-f]{32}$")

#: ``format: date-time`` as ``schemas/common.timestamp`` renders it: UTC, ``Z``, and a
#: fractional part that is present or absent depending on the instant.
TIMESTAMP_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")

#: Identity properties whose value a *run* allocates and which appear nowhere else in the
#: journey, so they cannot be learned from an earlier response. Named one by one, with the
#: shape each must have, for the same reason the timestamp fields are.
GENERATED_ID_FIELDS = (("model_call_id", re.compile(r"^mc_[0-9A-HJKMNP-TV-Z]{26}$")),)

#: Every property under which a timestamp may appear in a response of this surface.
#: Named one by one so that a *new* timestamp field in a rewritten body is a byte
#: difference and not a silently-tokenised one.
TIMESTAMP_FIELDS = (
    "created_at",
    "published_at",
    "terminal_at",
    "recorded_at",
    "started_at",
    "completed_at",
)

#: The transport's multipart body limit, ``multipart.MAX_BODY``. 26 MiB.
TRANSPORT_MAX_BODY = 27262976
#: The admission envelope's size bound, ``ingest.MAX_BYTES``. 25 MiB, and the number that
#: appears in the refusal as ``byte_size <= 26214400``.
ENVELOPE_MAX_BYTES = 26214400

#: The AR baseline document, measured. Also pinned by ``tests/e2e/pc01``.
BASELINE_SHA256 = "6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f"
BASELINE_BYTE_SIZE = 58978

#: The analysis profile and prompt bundle are constants in ``src`` -- not per-database
#: seed rows -- so they are literals here and not tokens.
#: ``tests/integration/analysis/test_profile_identity_is_pinned.py`` pins the same two.
ANALYSIS_PROFILE_ID = "ap_01M25P3TH08VVTTGJRXYBZZ7RP"
PROMPT_BUNDLE_ID = "pb_01M25P3TH0PDQYVKTRQFEM0CYS"

#: The one path wave 13 is allowed to change, named before the baseline existed.
#: ``OWNER_RULINGS_2026-09-17.md`` R-3 and ``DEBT_REGISTER.md`` D-7: the contract reseal
#: gives the storage credential refusal a code of its own, so this record's
#: ``error_code`` and status may move. Nothing else in this directory may.
EXCEPTION_D7 = {
    "debt": "D-7",
    "ruling": "OWNER_RULINGS_2026-09-17.md R-3 -- tokens *and* the storage code",
    "permitted_change": (
        "StoragePermissionDeniedError currently emits `permission_denied` with the "
        "catalog's authenticated-subject message. The reseal moves it to a code of its "
        "own, so this record's status, error_code, message and details may all change. "
        "The commit that decides it is cited beside the new expectation."
    ),
    "everything_else": (
        "Every other difference in this directory is a failure of the wave, whatever "
        "argument accompanies it."
    ),
}

MULTIPART_BOUNDARY = "w13baselineboundary"


# --- the exchange record -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Exchange:
    """One request and the response the current implementation gives it."""

    case: str
    operation: str | None
    purpose: str
    method: str
    target: str
    request_headers: tuple[tuple[str, str], ...]
    request_body: bytes
    request_body_note: str
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    tokens: "Tokens"
    body_kind: str = "text"
    body_note: str = ""
    exception: Mapping[str, str] | None = None


class Tokens:
    """The declared substitutions for one case, each with the reason it is allowed."""

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, str]] = {}

    def add(self, name: str, value: str, why: str) -> str:
        """Declare ``value`` replaceable by ``{{name}}``, and say why.

        A value already declared under another name keeps that name. Two tokens with one
        value would otherwise let the substitution of the first rewrite the second, and a
        token name is never allowed to contain a value for the same reason.
        """
        assert value, f"token {name} was given an empty value"
        assert "{{" not in value and "}}" not in value, (
            f"token {name} was given a value that looks like a token: {value!r}"
        )
        for token, (declared, reason) in self._entries.items():
            if declared == value:
                if why not in reason:
                    self._entries[token] = (declared, f"{reason}; also {why}")
                return token
        token = "{{%s}}" % name
        assert token not in self._entries, (
            f"token {token} was declared twice with different values: "
            f"{self._entries[token][0]!r} then {value!r}"
        )
        self._entries[token] = (value, why)
        return token

    def timestamps(self, payload: Any) -> None:
        """Declare every value under a :data:`TIMESTAMP_FIELDS` name, format-checked."""
        for name, value in _walk_named(payload, TIMESTAMP_FIELDS):
            assert isinstance(value, str) and TIMESTAMP_FORMAT.match(value), (
                f"{name} carried {value!r}, which is not the pinned date-time format "
                f"{TIMESTAMP_FORMAT.pattern}"
            )
            self.add(
                f"ts_{len(self._entries) + 1}",
                value,
                f"a timestamp the database stamped, read from the declared field "
                f"{name!r} and checked against the pinned format "
                f"{TIMESTAMP_FORMAT.pattern}",
            )

    def generated_ids(self, payload: Any) -> None:
        """Declare every value under a :data:`GENERATED_ID_FIELDS` name, shape-checked."""
        for name, pattern in GENERATED_ID_FIELDS:
            for found, value in _walk_named(payload, (name,)):
                assert isinstance(value, str) and pattern.match(value), (
                    f"{found} carried {value!r}, which is not the pinned shape "
                    f"{pattern.pattern}"
                )
                self.add(
                    f"gid_{len(self._entries) + 1}",
                    value,
                    f"an identity this run allocated, read from the declared field "
                    f"{found!r} and checked against the pinned shape {pattern.pattern}",
                )

    def apply(self, raw: bytes) -> bytes:
        """Replace every declared value, longest first so none can clip another."""
        out = raw
        for token, (value, _) in sorted(
            self._entries.items(), key=lambda item: -len(item[1][0])
        ):
            out = out.replace(value.encode("utf-8"), token.encode("ascii"))
        return out

    def as_dict(self) -> dict[str, str]:
        return {token: why for token, (_, why) in sorted(self._entries.items())}

    def values(self) -> dict[str, str]:
        return {token: value for token, (value, _) in self._entries.items()}


def _walk_named(node: Any, names: Sequence[str]) -> Iterator[tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in names:
                yield key, value
            else:
                yield from _walk_named(value, names)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_named(item, names)


# --- the caller --------------------------------------------------------------------


class Caller:
    """``Request.build`` plus ``dispatch``, the way ``tests/e2e/pc01/driver.py`` does it."""

    __slots__ = ("_app",)

    def __init__(self, app: Any) -> None:
        self._app = app

    def send(
        self,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] = {},
        body: bytes = b"",
    ) -> tuple[int, tuple[tuple[str, str], ...], bytes]:
        from auditmanager.api.routers import Request, dispatch

        request = Request.build(method, target, headers=headers, body=body)
        response = dispatch(self._app.router, request)
        return response.status, tuple(response.headers), response.body


def load_env_file() -> None:
    """Put this worktree's ``.env`` into the environment, the way the PC-01 driver does."""
    if os.environ.get("DATABASE_URL") and os.environ.get("S3_ENDPOINT_URL"):
        return
    path = REPOSITORY_ROOT / ".env"
    if not path.is_file():
        raise RuntimeError(
            f"{path} is missing. This baseline runs against real services: "
            "copy .env.example and set this session's instance."
        )
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip())


def build_apps() -> tuple[Any, Any]:
    """The application, and a second one whose storage credential is wrong.

    The second exists only for the D-7 case. It is a *configuration* override through the
    composition root's own ``environ`` parameter -- nothing under ``src/`` is touched and
    no module is patched.
    """
    load_env_file()
    os.environ["AUDITMANAGER_PROVIDER_MODE"] = "recorded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, (
            f"{leaked} reached the baseline; a recorded capture must not be able to spend"
        )
    from auditmanager.api.app import create_app

    environ = dict(os.environ) | {"AUDITMANAGER_PROVIDER_MODE": "recorded"}
    good = create_app(environ=environ)
    refused = create_app(
        environ=environ | {"S3_SECRET_ACCESS_KEY": "not-the-configured-secret"}
    )
    return good, refused


def multipart(
    payload: bytes,
    *,
    filename: str = "ar_baseline.pdf",
    title: str | None = "AR baseline",
    extra_part: tuple[str, str] | None = None,
    boundary: str = MULTIPART_BOUNDARY,
) -> bytes:
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'
    ).encode("utf-8")
    parts = [head, payload]
    if title is not None:
        parts.append(
            (
                f'\r\n--{boundary}\r\nContent-Disposition: form-data; '
                f'name="display_title"\r\n\r\n{title}'
            ).encode("utf-8")
        )
    if extra_part is not None:
        name, value = extra_part
        parts.append(
            (
                f'\r\n--{boundary}\r\nContent-Disposition: form-data; '
                f'name="{name}"\r\n\r\n{value}'
            ).encode("utf-8")
        )
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts)


def sized_multipart(total: int) -> bytes:
    """A framed multipart body of exactly ``total`` bytes, whose file part is a PDF header.

    Used for both sides of the transport boundary. The payload is padded, so the body
    reaches the size the case names without any fixture being added to the repository --
    ``fixtures/synthetic/ar/**`` and ``fixtures/validation/PC-02/**`` are frozen evidence
    and this session adds no bytes to either.
    """
    frame = len(multipart(b"", filename="between.pdf", title=None))
    payload = b"%PDF-1.7\n" + b"0" * (total - frame - 9)
    body = multipart(payload, filename="between.pdf", title=None)
    assert len(body) == total, (len(body), total)
    return body


# --- the journey -------------------------------------------------------------------


def run_journey(good: Any, refused: Any) -> list[Exchange]:
    """Drive every case, in order, and return what came back.

    **``startRun`` is reached as early as its own prerequisites allow** -- third request,
    directly after the project and the document it needs. ``DEBT_REGISTER.md`` D-5 records
    that the first browser-driven ``POST /api/v1/runs`` answered 500 twice while every
    in-process suite had it green, so it is the one operation where this in-process
    baseline is likeliest to disagree with what a socket produces. Capturing it first
    means a wrong capture shows up at the start of a run rather than at the end.
    """
    api = Caller(good)
    denied = Caller(refused)
    tag = uuid.uuid4().hex[:10]
    out: list[Exchange] = []

    def record(
        case: str,
        operation: str | None,
        purpose: str,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] = {},
        body: bytes = b"",
        body_note: str = "",
        caller: Caller | None = None,
        tokens: Tokens | None = None,
        body_kind: str = "text",
        response_note: str = "",
        exception: Mapping[str, str] | None = None,
    ) -> Exchange:
        status, response_headers, payload = (caller or api).send(
            method, target, headers=headers, body=body
        )
        exchange = Exchange(
            case=case,
            operation=operation,
            purpose=purpose,
            method=method,
            target=target,
            request_headers=tuple(sorted(headers.items())),
            request_body=body,
            request_body_note=body_note,
            status=status,
            headers=response_headers,
            body=payload,
            tokens=tokens or Tokens(),
            body_kind=body_kind,
            body_note=response_note,
            exception=exception,
        )
        exchange.tokens.add(
            "session_tag", tag, "this capture run's tag, carried by every idempotency key"
        )
        out.append(exchange)
        return exchange

    def json_of(exchange: Exchange) -> Any:
        return json.loads(exchange.body.decode("utf-8"))

    def correlation(exchange: Exchange, tokens: Tokens) -> None:
        value = dict(exchange.headers).get("X-Correlation-Id", "")
        assert CORRELATION_FORMAT.match(value), (
            f"the assigned correlation id {value!r} is not the pinned shape "
            f"{CORRELATION_FORMAT.pattern}"
        )
        tokens.add(
            "correlation_id",
            value,
            "assigned by the edge because the request carried none; checked against the "
            "pinned CorrelationId shape before being tokenised",
        )

    def content_length(exchange: Exchange, tokens: Tokens) -> None:
        value = dict(exchange.headers).get("Content-Length")
        assert value == str(len(exchange.body)), (
            f"Content-Length {value!r} does not describe the {len(exchange.body)} bytes "
            "of the body"
        )
        tokens.add(
            "content_length",
            value,
            "a function of the body, which is compared byte for byte; the comparison "
            "asserts Content-Length == str(len(body)) separately",
        )

    json_headers = {"Content-Type": "application/json"}

    # -- setup, deliberately not a record ---------------------------------------------
    # One project created before case 01, so that case 16's `limit=1` listing has a second
    # row behind it and `next_cursor` is non-null **by construction**.
    #
    # `W13-CONF` found case 16 failing inside the battery and passing alone. The cause was
    # not its own code: `next_cursor` is non-null only when a second project exists, the
    # journey guarded the assertion with `if cursor is not None:`, and the record froze
    # whichever branch the shared database happened to produce at capture time. So the
    # wave's safety net contained one record that was a function of residue -- and it is
    # the safety net stage 2 will be judged by, which makes it the record most likely to be
    # argued past at the end of a long wave.
    #
    # `OPERATING_CONSTRAINTS.md` §9 is the standing form of this: §6 covers residue, not
    # accumulated population, and telling them apart means running the suite alone. Wave 2
    # lost time to the same shape in a paging test.
    #
    # Created *before* case 01 so that case 01's project is still the newest and case 16's
    # `items[0]` assertion is unchanged.
    api.send(
        "POST",
        "/projects",
        headers={"Idempotency-Key": f"w13base-{tag}-cursor-setup", **json_headers},
        body=b'{"name": "W13 baseline cursor setup"}',
    )

    # 1 -- createProject ------------------------------------------------------------
    t = Tokens()
    project = record(
        "01-createProject.success",
        "createProject",
        "the write that every other case needs, and the 201 the frozen document gives "
        "both a creation and a replay",
        "POST",
        "/projects",
        headers={"Idempotency-Key": f"w13base-{tag}-project", **json_headers},
        body=b'{"name": "W13 response baseline"}',
        body_note="CreateProjectRequest, one declared property",
        tokens=t,
    )
    project_uid = json_of(project)["project_uid"]
    t.add("project_uid", project_uid, "the identity this request allocated")
    t.timestamps(json_of(project))
    correlation(project, t)
    content_length(project, t)

    # 2 -- uploadDocument -----------------------------------------------------------
    t = Tokens()
    pdf = BASELINE_PDF.read_bytes()
    assert hashlib.sha256(pdf).hexdigest() == BASELINE_SHA256, (
        "the AR baseline document is not the one this baseline was measured against"
    )
    assert len(pdf) == BASELINE_BYTE_SIZE
    upload = record(
        "02-uploadDocument.success",
        "uploadDocument",
        "the only multipart operation on the surface, and startRun's second prerequisite",
        "POST",
        f"/projects/{project_uid}/documents",
        headers={
            "Idempotency-Key": f"w13base-{tag}-upload",
            "Content-Type": f"multipart/form-data; boundary={MULTIPART_BOUNDARY}",
        },
        body=multipart(pdf),
        body_note=(
            "multipart/form-data: the file part is fixtures/synthetic/ar/ar_baseline.pdf "
            f"(sha256 {BASELINE_SHA256}), plus display_title"
        ),
        tokens=t,
    )
    version = json_of(upload)
    version_uid = version["version_uid"]
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity this request allocated")
    t.add("document_uid", version["document_uid"], "the identity this request allocated")
    t.timestamps(version)
    correlation(upload, t)
    content_length(upload, t)

    # 3 -- startRun -----------------------------------------------------------------
    # D-5: the operation a browser saw answer 500 twice. Captured as early as its
    # prerequisites allow, and in full -- status, every header, every byte.
    t = Tokens()
    started = record(
        "03-startRun.success",
        "startRun",
        "D-5's operation. 202, and the run's whole published shape: state, provider "
        "mode, the four stages, the pinned profile and bundle identities, the empty "
        "degradation set",
        "POST",
        "/runs",
        headers={"Idempotency-Key": f"w13base-{tag}-run", **json_headers},
        body=json.dumps({"version_uid": version_uid}).encode("utf-8"),
        body_note="StartRunRequest, version_uid only; provider_mode omitted",
        tokens=t,
    )
    run = json_of(started)
    run_id = run["run_id"]
    assert run["analysis_profile_id"] == ANALYSIS_PROFILE_ID, run["analysis_profile_id"]
    assert run["prompt_bundle_id"] == PROMPT_BUNDLE_ID, run["prompt_bundle_id"]
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity this request allocated")
    t.timestamps(run)
    correlation(started, t)
    content_length(started, t)

    # 4 -- startRun, replayed under the same key ------------------------------------
    t = Tokens()
    replay = record(
        "04-startRun.replay",
        "startRun",
        "the same key with the same payload: the frozen document gives a replay the "
        "same 202 and the same run, and nothing new is created",
        "POST",
        "/runs",
        headers={"Idempotency-Key": f"w13base-{tag}-run", **json_headers},
        body=json.dumps({"version_uid": version_uid}).encode("utf-8"),
        body_note="byte-identical to case 03, under the same Idempotency-Key",
        tokens=t,
    )
    assert json_of(replay)["run_id"] == run_id, "the replay produced a different run"
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated; the replay returns it")
    t.timestamps(json_of(replay))
    correlation(replay, t)
    content_length(replay, t)

    # 5 -- startRun, same key, a payload that differs only by a normalised property ---
    # Measured, not assumed. `provider_mode` is normalised away before the command
    # fingerprint is taken -- the adapter refuses a mode that disagrees with the
    # deployment's and otherwise passes the configured one -- so this is a *replay* and
    # answers 202 with the original run, byte for byte. It is captured because it is
    # exactly the kind of thing a rewrite can move without any test noticing.
    t = Tokens()
    normalised = record(
        "05-startRun.replay_with_normalised_property",
        "startRun",
        "the same key with a payload that differs only by `provider_mode`. That property "
        "is normalised away before the fingerprint, so this replays rather than "
        "conflicting: 202, and the run of case 03",
        "POST",
        "/runs",
        headers={"Idempotency-Key": f"w13base-{tag}-run", **json_headers},
        body=json.dumps(
            {"version_uid": version_uid, "provider_mode": "recorded"}
        ).encode("utf-8"),
        body_note="the key of case 03, with provider_mode stated explicitly",
        tokens=t,
    )
    assert json_of(normalised)["run_id"] == run_id
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated")
    t.timestamps(json_of(normalised))
    correlation(normalised, t)
    content_length(normalised, t)

    # 5b -- the key-reuse conflict ---------------------------------------------------
    t = Tokens()
    conflict = record(
        "05b-createProject.idempotency_key_reuse",
        "createProject",
        "the same key with a genuinely different payload: idempotency_key_reuse, and "
        "nothing is created",
        "POST",
        "/projects",
        headers={"Idempotency-Key": f"w13base-{tag}-project", **json_headers},
        body=b'{"name": "W13 response baseline, a different name"}',
        body_note="the key of case 01 with a different name",
        tokens=t,
    )
    assert json_of(conflict)["error_code"] == "idempotency_key_reuse", json_of(conflict)
    correlation(conflict, t)
    content_length(conflict, t)

    # 5c -- the replay ---------------------------------------------------------------
    t = Tokens()
    project_replay = record(
        "05c-createProject.replay",
        "createProject",
        "the same key with the same payload: 201 again, the same project, nothing new",
        "POST",
        "/projects",
        headers={"Idempotency-Key": f"w13base-{tag}-project", **json_headers},
        body=b'{"name": "W13 response baseline"}',
        body_note="byte-identical to case 01, under the same Idempotency-Key",
        tokens=t,
    )
    assert json_of(project_replay)["project_uid"] == project_uid
    t.add("project_uid", project_uid, "the identity case 01 allocated; the replay returns it")
    t.timestamps(json_of(project_replay))
    correlation(project_replay, t)
    content_length(project_replay, t)

    # 6 -- getRunStatus -------------------------------------------------------------
    t = Tokens()
    status_case = record(
        "06-getRunStatus.success",
        "getRunStatus",
        "the run read back; no correlation id supplied, so the edge assigns one",
        "GET",
        f"/runs/{run_id}",
        tokens=t,
    )
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated")
    t.timestamps(json_of(status_case))
    correlation(status_case, t)
    content_length(status_case, t)

    # 7 -- getRunStatus with a supplied correlation id -------------------------------
    t = Tokens()
    supplied = record(
        "07-getRunStatus.correlation_supplied",
        "getRunStatus",
        "X-Correlation-Id supplied: the edge honours it and echoes it back. The value "
        "below is a literal, so the echo is pinned rather than tokenised",
        "GET",
        f"/runs/{run_id}",
        headers={"X-Correlation-Id": "w13base-supplied-correlation-id"},
        tokens=t,
    )
    assert dict(supplied.headers)["X-Correlation-Id"] == "w13base-supplied-correlation-id"
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated")
    t.timestamps(json_of(supplied))
    content_length(supplied, t)

    # 8 -- listRunFindings ----------------------------------------------------------
    t = Tokens()
    findings = record(
        "08-listRunFindings.success",
        "listRunFindings",
        "the page envelope, the finding shape, the Russian text unescaped "
        "(ensure_ascii=False) and the evidence offsets",
        "GET",
        f"/runs/{run_id}/findings",
        tokens=t,
    )
    page = json_of(findings)
    finding_uid = page["items"][0]["finding_uid"]
    observation_id = page["items"][0]["observation"]["finding_observation_id"]
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated")
    for index, item in enumerate(page["items"]):
        t.add(
            f"finding_uid_{index}",
            item["finding_uid"],
            "a finding identity this run allocated, read from this response",
        )
        t.add(
            f"finding_observation_id_{index}",
            item["observation"]["finding_observation_id"],
            "an observation identity this run allocated, read from this response",
        )
    t.timestamps(page)
    t.generated_ids(page)
    correlation(findings, t)
    content_length(findings, t)

    # 9 -- getFinding ---------------------------------------------------------------
    t = Tokens()
    finding = record(
        "09-getFinding.success",
        "getFinding",
        "the composed finding detail",
        "GET",
        f"/findings/{finding_uid}",
        tokens=t,
    )
    detail = json_of(finding)
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated")
    t.add("finding_uid", finding_uid, "the identity case 08 read")
    t.add("finding_observation_id", observation_id, "the identity case 08 read")
    t.timestamps(detail)
    t.generated_ids(detail)
    correlation(finding, t)
    content_length(finding, t)

    # 10 -- appendDecision ----------------------------------------------------------
    t = Tokens()
    decision = record(
        "10-appendDecision.success",
        "appendDecision",
        "the append-only ledger's 201, the event and the verdict it produces",
        "POST",
        f"/findings/{finding_uid}/decisions",
        headers={"Idempotency-Key": f"w13base-{tag}-decision", **json_headers},
        body=json.dumps(
            {
                "event_type": "accept",
                "finding_observation_id": observation_id,
                "comment": "W13 response baseline",
            }
        ).encode("utf-8"),
        body_note="AppendDecisionRequest with all three declared properties",
        tokens=t,
    )
    appended = json_of(decision)
    decision_id = _first_value(appended, "decision_id")
    decision_recorded_at = _first_value(appended, "recorded_at")
    t.add("finding_uid", finding_uid, "the identity case 08 read")
    t.add("finding_observation_id", observation_id, "the identity case 08 read")
    t.add("run_id", run_id, "the identity case 03 allocated")
    t.add("decision_id", decision_id, "the identity this request allocated")
    t.timestamps(appended)
    correlation(decision, t)
    content_length(decision, t)

    # 11 -- listDecisionHistory -----------------------------------------------------
    t = Tokens()
    history = record(
        "11-listDecisionHistory.success",
        "listDecisionHistory",
        "the ledger read back, ordered by (recorded_at, decision_id) and carrying no "
        "sequence number",
        "GET",
        f"/findings/{finding_uid}/decisions",
        tokens=t,
    )
    events = json_of(history)
    t.add("finding_uid", finding_uid, "the identity case 08 read")
    t.add("finding_observation_id", observation_id, "the identity case 08 read")
    t.add("run_id", run_id, "the identity case 03 allocated")
    t.add("decision_id", decision_id, "the identity case 10 allocated")
    t.timestamps(events)
    correlation(history, t)
    content_length(history, t)

    # 12 -- exportRunCsv ------------------------------------------------------------
    t = Tokens()
    csv_case = record(
        "12-exportRunCsv.success",
        "exportRunCsv",
        "the CSV with its BOM and its CRLF line terminators, byte for byte, and the "
        "Content-Disposition built from the run identity alone",
        "GET",
        f"/runs/{run_id}/export.csv",
        tokens=t,
        body_kind="base64",
        response_note=(
            "text/csv bytes: b'\\xef\\xbb\\xbf' BOM then RFC 4180 rows with CRLF. "
            "Compared as bytes, so a lost BOM or an LF is a difference"
        ),
    )
    assert csv_case.body.startswith(b"\xef\xbb\xbf"), "the CSV lost its BOM"
    assert b"\r\n" in csv_case.body, "the CSV lost its CRLF terminator"
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("document_uid", version["document_uid"], "the identity case 02 allocated")
    t.add("run_id", run_id, "the identity case 03 allocated")
    for index, item in enumerate(page["items"]):
        t.add(f"finding_uid_{index}", item["finding_uid"], "a finding identity from case 08")
        t.add(
            f"finding_observation_id_{index}",
            item["observation"]["finding_observation_id"],
            "an observation identity from case 08",
        )
    t.add("decision_id", decision_id, "the identity case 10 allocated")
    t.add(
        "decision_recorded_at",
        decision_recorded_at,
        "the decision timestamp case 10 returned; the CSV repeats it in "
        "decision_recorded_at",
    )
    correlation(csv_case, t)
    content_length(csv_case, t)

    # 13 -- getDocumentVersion ------------------------------------------------------
    t = Tokens()
    got = record(
        "13-getDocumentVersion.success",
        "getDocumentVersion",
        "the published version read back; source_filename is deliberately never emitted",
        "GET",
        f"/versions/{version_uid}",
        tokens=t,
    )
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    t.add("document_uid", version["document_uid"], "the identity case 02 allocated")
    t.timestamps(json_of(got))
    correlation(got, t)
    content_length(got, t)

    # 14 -- streamDocumentVersionContent, whole body --------------------------------
    t = Tokens()
    content = record(
        "14-streamDocumentVersionContent.success",
        "streamDocumentVersionContent",
        "the server streams the bytes itself: 200, application/pdf, Accept-Ranges",
        "GET",
        f"/versions/{version_uid}/content",
        tokens=t,
        body_kind="fixture-bytes",
        response_note=(
            "exactly the bytes of fixtures/synthetic/ar/ar_baseline.pdf. Recorded as that "
            "path with its pinned sha256 and length rather than copied in, so this "
            "directory adds no duplicate of frozen evidence"
        ),
    )
    assert content.body == pdf, "the streamed body is not the document that was uploaded"
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    correlation(content, t)
    content_length(content, t)

    # 15 -- streamDocumentVersionContent, a Range read ------------------------------
    t = Tokens()
    ranged = record(
        "15-streamDocumentVersionContent.range",
        "streamDocumentVersionContent",
        "a single byte range: 206, Content-Range, and a window of exactly 64 bytes",
        "GET",
        f"/versions/{version_uid}/content",
        headers={"Range": "bytes=100-163"},
        tokens=t,
        body_kind="base64",
        response_note="the 64 bytes at offsets 100..163 of the AR baseline document",
    )
    assert ranged.body == pdf[100:164], "the window is not the bytes that were asked for"
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    correlation(ranged, t)
    content_length(ranged, t)

    # 16 -- listProjects ------------------------------------------------------------
    t = Tokens()
    listed = record(
        "16-listProjects.success",
        "listProjects",
        "the page envelope with a bounded page. The listing is newest-first, so the "
        "project of case 01 is the one row, and next_cursor is the opaque continuation "
        "token -- asserted to decode to exactly that project_uid before it is tokenised",
        "GET",
        "/projects?limit=1",
        tokens=t,
    )
    listing = json_of(listed)
    assert listing["items"][0]["project_uid"] == project_uid, (
        "the newest-first listing did not put this journey's project first"
    )
    cursor = listing["page"]["next_cursor"]
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    # Unconditional. The setup project above guarantees a second row, so a null cursor here
    # is a defect in the listing rather than a property of the database -- which is exactly
    # the distinction the conditional used to hide.
    assert cursor is not None, (
        "next_cursor is null although a second project exists; a bounded page with more "
        "rows behind it must carry a continuation token"
    )
    assert _decode_cursor(cursor) == [project_uid], (
        f"the cursor decodes to {_decode_cursor(cursor)!r}, not to the page's last "
        "project_uid; it is not the sort key the frozen Cursor schema promises"
    )
    t.add(
        "next_cursor",
        cursor,
        "base64url of the page's last sort key; asserted to decode to exactly "
        "[project_uid] before being tokenised",
    )
    t.timestamps(listing)
    correlation(listed, t)
    content_length(listed, t)

    # --- the five negative-envelope refusals, each with its own constraint ----------
    for case, filename, label, constraint, purpose in (
        (
            "17-uploadDocument.refusal.pdf_magic_bytes",
            "not_a_pdf.txt",
            "magic",
            "pdf_magic_bytes",
            "content that does not begin with a PDF header, whatever its name says",
        ),
        (
            "19-uploadDocument.refusal.not_encrypted",
            "encrypted.pdf",
            "encrypted",
            "not_encrypted",
            "an encrypted document, refused before any page is read",
        ),
        (
            "20-uploadDocument.refusal.page_count",
            "too_many_pages.pdf",
            "pages",
            "1 <= page_count <= 30",
            "a document outside the one-to-thirty page bound",
        ),
        (
            "21-uploadDocument.refusal.every_page_has_extractable_text",
            "image_only.pdf",
            "imageonly",
            "every_page_has_extractable_text",
            "a page with no embedded text; OCR is never silently substituted",
        ),
    ):
        t = Tokens()
        refusal = record(
            case,
            "uploadDocument",
            f"negative envelope: {purpose}",
            "POST",
            f"/projects/{project_uid}/documents",
            headers={
                "Idempotency-Key": f"w13base-{tag}-{label}",
                "Content-Type": f"multipart/form-data; boundary={MULTIPART_BOUNDARY}",
            },
            body=multipart((NEGATIVE / filename).read_bytes(), filename=filename),
            body_note=f"the file part is fixtures/synthetic/ar/negative/{filename}",
            tokens=t,
        )
        observed = json_of(refusal)["details"]["constraint"]
        assert observed == constraint, (
            f"{case} was refused by {observed!r}, not by the rule it names"
        )
        t.add("project_uid", project_uid, "the identity case 01 allocated")
        correlation(refusal, t)
        content_length(refusal, t)

    # 18 -- the envelope's own size bound, reached through the transport -------------
    # tests/integration/ingest/test_size_guard_boundary.py: every oversize fixture in the
    # repository is over BOTH limits, so the transport always answers first. The body
    # below is framed to exactly the transport limit, so the transport lets it through
    # and the envelope is the guard that speaks.
    assert ENVELOPE_MAX_BYTES < TRANSPORT_MAX_BODY, (
        "no body can reach the envelope's size bound through the transport"
    )
    t = Tokens()
    at_limit = record(
        "18-uploadDocument.refusal.byte_size",
        "uploadDocument",
        "the 26 MiB transport boundary, under side: a framed body of exactly "
        f"{TRANSPORT_MAX_BODY} bytes passes the transport, and the envelope refuses it "
        f"with byte_size <= {ENVELOPE_MAX_BYTES}",
        "POST",
        f"/projects/{project_uid}/documents",
        headers={
            "Idempotency-Key": f"w13base-{tag}-atlimit",
            "Content-Type": f"multipart/form-data; boundary={MULTIPART_BOUNDARY}",
        },
        body=sized_multipart(TRANSPORT_MAX_BODY),
        body_note=(
            f"a framed multipart body of exactly {TRANSPORT_MAX_BODY} bytes, built in "
            "process; no fixture is added to the repository"
        ),
        tokens=t,
    )
    assert json_of(at_limit)["details"]["constraint"] == f"byte_size <= {ENVELOPE_MAX_BYTES}", (
        "the transport answered first; this case is not measuring the envelope"
    )
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    correlation(at_limit, t)
    content_length(at_limit, t)

    # 22 -- the same boundary, over side --------------------------------------------
    t = Tokens()
    over = record(
        "22-uploadDocument.refusal.max_bytes",
        "uploadDocument",
        "the 26 MiB transport boundary, over side: one byte more and the transport "
        "guard answers instead, with a different constraint",
        "POST",
        f"/projects/{project_uid}/documents",
        headers={
            "Idempotency-Key": f"w13base-{tag}-overlimit",
            "Content-Type": f"multipart/form-data; boundary={MULTIPART_BOUNDARY}",
        },
        body=sized_multipart(TRANSPORT_MAX_BODY + 1),
        body_note=f"a framed multipart body of exactly {TRANSPORT_MAX_BODY + 1} bytes",
        tokens=t,
    )
    assert json_of(over)["details"]["constraint"] == "max_bytes", (
        "one byte over the transport limit did not reach the transport guard"
    )
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    correlation(over, t)
    content_length(over, t)

    # --- the additionalProperties refusal on every write body ----------------------
    t = Tokens()
    extra_project = record(
        "23-createProject.refusal.additionalProperties",
        "createProject",
        "a closed request schema: an undeclared property is refused, and the offending "
        "name is never echoed",
        "POST",
        "/projects",
        headers={"Idempotency-Key": f"w13base-{tag}-extraproject", **json_headers},
        body=b'{"name": "W13 response baseline", "nmae": "typo"}',
        tokens=t,
    )
    correlation(extra_project, t)
    content_length(extra_project, t)

    t = Tokens()
    extra_run = record(
        "24-startRun.refusal.additionalProperties",
        "startRun",
        "the same rule on StartRunRequest",
        "POST",
        "/runs",
        headers={"Idempotency-Key": f"w13base-{tag}-extrarun", **json_headers},
        body=json.dumps({"version_uid": version_uid, "priority": "high"}).encode("utf-8"),
        tokens=t,
    )
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    correlation(extra_run, t)
    content_length(extra_run, t)

    t = Tokens()
    extra_decision = record(
        "25-appendDecision.refusal.additionalProperties",
        "appendDecision",
        "the same rule on AppendDecisionRequest",
        "POST",
        f"/findings/{finding_uid}/decisions",
        headers={"Idempotency-Key": f"w13base-{tag}-extradecision", **json_headers},
        body=json.dumps(
            {
                "event_type": "accept",
                "finding_observation_id": observation_id,
                "reviewer": "someone",
            }
        ).encode("utf-8"),
        tokens=t,
    )
    t.add("finding_uid", finding_uid, "the identity case 08 read")
    correlation(extra_decision, t)
    content_length(extra_decision, t)

    t = Tokens()
    extra_part = record(
        "26-uploadDocument.refusal.additionalProperties",
        "uploadDocument",
        "the same rule on the one multipart body: an undeclared part is refused rather "
        "than ignored",
        "POST",
        f"/projects/{project_uid}/documents",
        headers={
            "Idempotency-Key": f"w13base-{tag}-extrapart",
            "Content-Type": f"multipart/form-data; boundary={MULTIPART_BOUNDARY}",
        },
        body=multipart(pdf, extra_part=("reviewer", "someone")),
        body_note="the declared file and display_title parts plus one the schema "
        "does not declare",
        tokens=t,
    )
    assert json_of(extra_part)["details"]["constraint"] == "additionalProperties"
    t.add("project_uid", project_uid, "the identity case 01 allocated")
    correlation(extra_part, t)
    content_length(extra_part, t)

    # --- header and routing refusals the rewrite is most likely to move -------------
    t = Tokens()
    no_key = record(
        "27-createProject.refusal.idempotency_key_required",
        "createProject",
        "a write with no Idempotency-Key: validation_failed with field and constraint, "
        "not a framework's own 422 body",
        "POST",
        "/projects",
        headers=json_headers,
        body=b'{"name": "W13 response baseline"}',
        tokens=t,
    )
    correlation(no_key, t)
    content_length(no_key, t)

    t = Tokens()
    unknown = record(
        "28-dispatch.no_route",
        None,
        "a path the document does not declare: not_found, with the envelope and the "
        "correlation header",
        "GET",
        "/there-is-no-such-operation",
        tokens=t,
    )
    correlation(unknown, t)
    content_length(unknown, t)

    t = Tokens()
    wrong_method = record(
        "29-dispatch.method_not_allowed",
        None,
        "a declared path under an undeclared method. **404, not 405** -- the surface "
        "declares twelve operations and no other method on any of their paths, so this "
        "is simply not a resource here. A framework's default 405 would be a difference",
        "DELETE",
        "/projects",
        tokens=t,
    )
    correlation(wrong_method, t)
    content_length(wrong_method, t)

    t = Tokens()
    missing = record(
        "30-getRunStatus.not_found",
        "getRunStatus",
        "a malformed identity answers not_found, never validation_failed: a well-formed "
        "identity that does not exist and a malformed one must be indistinguishable",
        "GET",
        "/runs/run_NOT_A_REAL_IDENTITY",
        tokens=t,
    )
    correlation(missing, t)
    content_length(missing, t)

    # --- the one path allowed to change --------------------------------------------
    t = Tokens()
    storage = record(
        "31-streamDocumentVersionContent.storage_permission_denied",
        "streamDocumentVersionContent",
        "**THE D-7 EXCEPTION.** The application's own storage credential is refused by "
        "the store, and StoragePermissionDeniedError emits `permission_denied` -- the "
        "catalog code whose summary describes an *authenticated subject*. There is no "
        "subject in this scenario at all. R-3 settles it at the reseal by giving the "
        "storage case a code of its own, so this record's bytes change on purpose",
        "GET",
        f"/versions/{version_uid}/content",
        caller=denied,
        tokens=t,
        exception=EXCEPTION_D7,
    )
    assert storage.status == 403, storage.status
    assert json_of(storage)["error_code"] == "permission_denied", json_of(storage)
    t.add("version_uid", version_uid, "the identity case 02 allocated")
    correlation(storage, t)
    content_length(storage, t)

    return out


def _first_value(node: Any, name: str) -> str:
    for found, value in _walk_named(node, (name,)):
        if isinstance(value, str):
            return value
    raise AssertionError(f"no {name} in {node!r}")


def _decode_cursor(raw: str) -> Any:
    import base64

    padded = raw + "=" * (-len(raw) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))


# --- the record on disk ------------------------------------------------------------


def record_path(case: str) -> Path:
    return RECORDS / f"{case}.json"


def _encode_body(exchange: Exchange) -> dict[str, Any]:
    import base64

    substituted = exchange.tokens.apply(exchange.body)
    if exchange.body_kind == "fixture-bytes":
        return {
            "kind": "fixture-bytes",
            "path": "fixtures/synthetic/ar/ar_baseline.pdf",
            "sha256": BASELINE_SHA256,
            "length": BASELINE_BYTE_SIZE,
            "note": exchange.body_note,
        }
    if exchange.body_kind == "base64":
        return {
            "kind": "base64",
            "length": len(exchange.body),
            "base64": base64.b64encode(substituted).decode("ascii"),
            "note": exchange.body_note,
        }
    return {
        "kind": "text",
        "length": len(exchange.body),
        "text": substituted.decode("utf-8"),
        "note": exchange.body_note,
    }


def _sub(exchange: Exchange, text: str) -> str:
    return exchange.tokens.apply(text.encode("utf-8")).decode("utf-8")


def to_record(exchange: Exchange) -> dict[str, Any]:
    """The committed form of one exchange: everything, with the tokens named."""
    return {
        "case": exchange.case,
        "operation": exchange.operation,
        "purpose": exchange.purpose,
        "captured_through": (
            "auditmanager.api.routers.Request.build + dispatch, over "
            "auditmanager.api.app.create_app()"
        ),
        "pre_authorization": (
            "Captured before the T-6 reseal. Every request here is unauthenticated and "
            "is answered. This is not a post-auth expectation."
        ),
        "exception": exchange.exception,
        "request": {
            "method": exchange.method,
            "target": _sub(exchange, exchange.target),
            "headers": [
                [name, _sub(exchange, value)] for name, value in exchange.request_headers
            ],
            "body_length": len(exchange.request_body),
            "body_note": exchange.request_body_note,
        },
        "response": {
            "status": exchange.status,
            "headers": [
                [name, exchange.tokens.apply(value.encode("utf-8")).decode("utf-8")]
                for name, value in exchange.headers
            ],
            "body": _encode_body(exchange),
        },
        "tokens": exchange.tokens.as_dict(),
    }


def write_records(exchanges: Sequence[Exchange]) -> list[Path]:
    RECORDS.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for exchange in exchanges:
        path = record_path(exchange.case)
        path.write_text(
            json.dumps(to_record(exchange), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def differences(exchange: Exchange, expected: Mapping[str, Any]) -> list[str]:
    """Every way this exchange fails to reproduce the recorded one."""
    import base64

    found: list[str] = []
    response = expected["response"]

    if exchange.status != response["status"]:
        found.append(f"status: expected {response['status']}, got {exchange.status}")

    observed_headers = [
        [name, exchange.tokens.apply(value.encode("utf-8")).decode("utf-8")]
        for name, value in exchange.headers
    ]
    if observed_headers != response["headers"]:
        found.append(
            f"headers: expected {response['headers']!r}, got {observed_headers!r}"
        )

    declared = dict(exchange.headers).get("Content-Length")
    if declared is not None and declared != str(len(exchange.body)):
        found.append(
            f"Content-Length {declared!r} does not describe the {len(exchange.body)} "
            "bytes of the body"
        )

    body = response["body"]
    substituted = exchange.tokens.apply(exchange.body)
    if body["kind"] == "fixture-bytes":
        fixture = (REPOSITORY_ROOT / body["path"]).read_bytes()
        if hashlib.sha256(fixture).hexdigest() != body["sha256"]:
            found.append(f"{body['path']} is no longer the file this baseline recorded")
        elif exchange.body != fixture:
            found.append(
                f"body: expected the {body['length']} bytes of {body['path']}, got "
                f"{len(exchange.body)} bytes"
            )
    elif body["kind"] == "base64":
        want = base64.b64decode(body["base64"])
        if substituted != want:
            found.append(_byte_difference(want, substituted))
    else:
        want = body["text"].encode("utf-8")
        if substituted != want:
            found.append(_byte_difference(want, substituted))
    return found


def _byte_difference(want: bytes, got: bytes) -> str:
    for index, (a, b) in enumerate(zip(want, got)):
        if a != b:
            return (
                f"body: first difference at byte {index}\n"
                f"  expected ...{want[max(0, index - 60):index + 60]!r}...\n"
                f"  got      ...{got[max(0, index - 60):index + 60]!r}..."
            )
    return (
        f"body: identical for {min(len(want), len(got))} bytes, then the lengths differ "
        f"(expected {len(want)}, got {len(got)})\n"
        f"  expected tail {want[min(len(want), len(got)):][:120]!r}\n"
        f"  got tail      {got[min(len(want), len(got)):][:120]!r}"
    )
