"""Drive the composed application over the PC-02 corpus, once per document.

Everything here goes through ``auditmanager.api.app.create_app()`` and the ``Router`` it
returns, dispatched by ``auditmanager.api.routers.dispatch``. No module of the product is
imported to make a step work: this file knows the twelve operations and nothing else.

One run per measurable document, in the pre-registered order of
``docs/program/validation/PC-02_PROTOCOL.md`` section 4. Each document's record is written
to its own file the moment the run reaches a terminal state, so a session killed part-way
through loses one document rather than all of them.

The four negative-envelope documents are attempted through the same upload operation and
their refusals recorded verbatim. They are excluded from every finding denominator.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[4]
CORPUS = ROOT / "fixtures" / "validation" / "PC-02"
MANIFEST = CORPUS / "corpus_manifest.json"
OUT = Path(__file__).resolve().parent / "runs"

#: Protocol section 4. Fixed in advance, not chosen here.
PRE_REGISTERED_ORDER = [
    "PC02-S01", "PC02-C01", "PC02-S02", "PC02-C02", "PC02-S03",
    "PC02-C03", "PC02-C04", "PC02-S04", "PC02-C05", "PC02-S05",
    "PC02-C06", "PC02-C07", "PC02-C08", "PC02-C09",
]

SESSION_TAG = os.environ.get("P4RUN_TAG") or uuid.uuid4().hex[:12]
TERMINAL_STATES = {"published", "partial", "failed", "cancelled"}

#: The two environment files the dispatch names. ``.env`` carries the fifteen FF-01
#: service names; ``.env.provider`` carries the provider selection, which is deliberately
#: not in ``.env``. Both are data, not code: parsed as NAME=VALUE, never sourced, so
#: nothing in either can execute. An exported value already in the environment wins.
ENV_FILES = (ROOT / ".env", ROOT / ".env.provider")


def load_env_files() -> list[str]:
    """Put both environment files into ``os.environ``. Missing is a hard failure.

    This run is not a test: ``tests/conftest.py`` strips every provider-selecting
    variable so no test pays by accident, and that stripping is exactly what must not
    happen here. Loading is explicit and the names loaded are printed, so what the run
    was configured with is visible in its own log.
    """
    loaded: list[str] = []
    for path in ENV_FILES:
        if not path.is_file():
            raise RuntimeError(
                f"{path} is missing. This run drives real services and a paid provider; "
                "it does not fall back to defaults."
            )
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if name not in os.environ:
                os.environ[name] = value
                loaded.append(name)
    return loaded


def answer(app: Any, method: str, target: str, *,
           headers: Mapping[str, str] = (), body: bytes = b"") -> tuple[int, bytes]:
    from auditmanager.api.routers import Request, dispatch

    response = dispatch(app.router, Request.build(method, target, headers=headers, body=body))
    return response.status, response.body


def as_json(body: bytes) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return {"_undecodable": body[:400].decode("utf-8", "replace")}


def multipart(content: bytes, *, filename: str, title: str) -> tuple[str, bytes]:
    boundary = "p4run01boundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'
    ).encode("utf-8")
    tail = (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; "
        f'name="display_title"\r\n\r\n{title}\r\n--{boundary}--\r\n'
    ).encode("utf-8")
    return f"multipart/form-data; boundary={boundary}", head + content + tail


def key(label: str) -> str:
    return f"p4run01-{SESSION_TAG}-{label}"


def collect_findings(app: Any, run_id: str) -> tuple[list[dict], list[dict]]:
    """Every published finding, following the cursor to exhaustion."""
    items: list[dict] = []
    pages: list[dict] = []
    target = f"/runs/{run_id}/findings?limit=200"
    while True:
        status, body = answer(app, "GET", target)
        payload = as_json(body)
        pages.append({"target": target, "status": status})
        if status >= 300:
            pages[-1]["error"] = payload
            break
        items.extend(payload.get("items", []))
        cursor = (payload.get("page") or {}).get("next_cursor")
        if not cursor:
            break
        target = f"/runs/{run_id}/findings?limit=200&cursor={cursor}"
    return items, pages


def run_one(app: Any, project_uid: str, record: dict) -> dict:
    label = record["label"]
    path = ROOT / record["path"]
    content = path.read_bytes()
    out: dict[str, Any] = {
        "label": label,
        "role": record["role"],
        "path": record["path"],
        "pages": record["pages"],
        "bytes": record["bytes"],
        "sha256": record["sha256"],
        "session_tag": SESSION_TAG,
    }

    t0 = time.monotonic()
    ctype, body = multipart(content, filename=f"{label}.pdf", title=record["title_ru"])
    status, raw = answer(
        app, "POST", f"/projects/{project_uid}/documents",
        headers={"Idempotency-Key": key(f"up-{label}"), "Content-Type": ctype}, body=body,
    )
    upload = as_json(raw)
    out["upload"] = {"status": status, "body": upload}
    out["upload_seconds"] = round(time.monotonic() - t0, 3)
    if status >= 300:
        out["state"] = None
        out["terminated"] = False
        out["failure"] = "upload refused"
        return out

    version_uid = upload["version_uid"]
    out["version_uid"] = version_uid
    out["page_count_reported"] = upload.get("page_count")

    t1 = time.monotonic()
    status, raw = answer(
        app, "POST", "/runs",
        headers={"Idempotency-Key": key(f"run-{label}"), "Content-Type": "application/json"},
        body=json.dumps({"version_uid": version_uid}).encode("utf-8"),
    )
    started = as_json(raw)
    out["start_run"] = {"status": status, "body": started}
    out["run_wall_seconds"] = round(time.monotonic() - t1, 3)
    if status >= 300:
        out["state"] = None
        out["terminated"] = False
        out["failure"] = "startRun refused"
        return out

    run_id = started["run_id"]
    out["run_id"] = run_id

    # startRun is synchronous, but the state is read back through getRunStatus rather
    # than trusted from the POST body: the terminal state reported is the one the
    # application will report to anybody else who asks.
    deadline = time.monotonic() + 900
    while True:
        status, raw = answer(app, "GET", f"/runs/{run_id}")
        state_body = as_json(raw)
        state = state_body.get("state")
        if state in TERMINAL_STATES or time.monotonic() > deadline:
            break
        time.sleep(2.0)

    out["status_read"] = {"status": status, "body": state_body}
    out["state"] = state_body.get("state")
    out["terminated"] = state_body.get("state") in TERMINAL_STATES
    out["stages"] = state_body.get("stages", [])
    out["degradation_set"] = state_body.get("degradation_set")
    out["terminal_reason"] = state_body.get("terminal_reason")
    out["published_finding_count"] = state_body.get("published_finding_count")
    out["diagnostic_observation_count"] = state_body.get("diagnostic_observation_count")

    findings, pages = collect_findings(app, run_id)
    out["findings"] = findings
    out["finding_pages"] = pages
    out["findings_returned"] = len(findings)
    return out


def run_negative(app: Any, project_uid: str, record: dict) -> dict:
    label = record["label"]
    path = ROOT / record["path"]
    content = path.read_bytes()
    ctype, body = multipart(content, filename=f"{label}.pdf", title=label)
    t0 = time.monotonic()
    status, raw = answer(
        app, "POST", f"/projects/{project_uid}/documents",
        headers={"Idempotency-Key": key(f"neg-{label}"), "Content-Type": ctype}, body=body,
    )
    payload = as_json(raw)
    return {
        "label": label,
        "path": record["path"],
        "bytes": record["bytes"],
        "violates_rule": record["violates_rule"],
        "rule_description": record["rule_description"],
        "upload_status": status,
        "refused": status >= 400,
        "response": payload,
        "seconds": round(time.monotonic() - t0, 3),
    }


def main(argv: Sequence[str]) -> int:
    only = set(argv[1:]) or None
    loaded = load_env_files()
    print(f"environment: loaded {len(loaded)} names from .env and .env.provider", flush=True)
    for name in ("AUDITMANAGER_PROVIDER_MODE", "PROXY_LLM_MODEL", "PROXY_LLM_BASE_URL",
                 "AUDITMANAGER_MODEL_ID", "AUDITMANAGER_RUN_COST_CEILING_USD",
                 "FOUNDATION_INSTANCE", "POSTGRES_DB", "S3_BUCKET"):
        print(f"  {name}={os.environ.get(name, '<unset, default applies>')}", flush=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_label = {d["label"]: d for d in manifest["documents"]}
    OUT.mkdir(parents=True, exist_ok=True)

    from auditmanager.api.app import create_app

    app = create_app(environ=dict(os.environ))
    print(f"composed: provider_mode={app.settings.provider_mode} "
          f"operations={len(app.router.routes)} tag={SESSION_TAG}", flush=True)

    status, raw = answer(
        app, "POST", "/projects",
        headers={"Idempotency-Key": key("project"), "Content-Type": "application/json"},
        body=json.dumps({"name": f"PC-02 baseline {SESSION_TAG}"}).encode("utf-8"),
    )
    if status >= 300:
        print(f"createProject refused: {status} {raw!r}", file=sys.stderr)
        return 2
    project_uid = as_json(raw)["project_uid"]
    print(f"project: {project_uid}", flush=True)
    (OUT.parent / "session.json").write_text(
        json.dumps({"session_tag": SESSION_TAG, "project_uid": project_uid,
                    "provider_mode": app.settings.provider_mode,
                    "model_id": getattr(app.settings, "model_id", None),
                    "cost_ceiling_usd": str(getattr(app.settings, "run_cost_ceiling_usd", "")),
                    "pre_registered_order": PRE_REGISTERED_ORDER},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for label in PRE_REGISTERED_ORDER:
        if only and label not in only:
            continue
        target = OUT / f"{label}.json"
        if target.exists():
            print(f"{label}: already recorded, skipping", flush=True)
            continue
        print(f"{label}: starting", flush=True)
        began = time.time()
        result = run_one(app, project_uid, by_label[label])
        result["began_epoch"] = began
        result["ended_epoch"] = time.time()
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"{label}: state={result.get('state')} "
              f"findings={result.get('findings_returned')} "
              f"seconds={result.get('run_wall_seconds')}", flush=True)

    for record in manifest["negative_envelope_documents"]:
        label = record["label"]
        if only and label not in only:
            continue
        target = OUT / f"{label}.json"
        if target.exists():
            print(f"{label}: already recorded, skipping", flush=True)
            continue
        print(f"{label}: attempting upload", flush=True)
        result = run_negative(app, project_uid, record)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"{label}: status={result['upload_status']} "
              f"code={result['response'].get('error_code')}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
