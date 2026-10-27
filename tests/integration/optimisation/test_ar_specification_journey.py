"""`SPEC-TABLE-RECORDING-01`: an AR bundle with a Form-7 table reaches a cheaper-analog proposal.

The journey the live-journey lane drives against a stand, here on the lane's own PostgreSQL and
MinIO through the composed ASGI application with the **recorded** provider and a real expert
credential, over the committed synthetic fixtures and nothing else:

1. upload ``fixtures/synthetic/ar_specification/ar_specification.zip`` (a portal bundle whose PDF
   carries a seven-position specification over two sheets);
2. classify the version (stage ``П``, section ``AR``);
3. a published run of the version: the recorded answer
   ``fixtures/recorded/sections/ar_specification/<key>.json`` is found by the key of the request
   over the PDF's text layer, and the run publishes. Since `PROD-11-AR-V1-V2-REMOVAL-01` the served
   ``startRun`` refuses an АР version (``section_profile_unavailable``), so this step is driven
   in-process through the executor with the v1 machinery's reference profile
   (``tests/support/published_run.py``): the run, its saved text layer and everything the
   specification and optimisation reads do with them are what they were. Where an АР version gets its
   published run in production (the v3 group, `PROD-11a`) is not exercised here;
4. upload ``ar_specification_prices.csv`` as the project's price list;
5. set the project's AR vendor list;
6. start an optimisation pass.

What is held: before the price list the specification read says so (``price_list_missing``);
after it the extractor has read exactly the oracle's seven rows (one table continued onto the
second sheet without a repeated header, a name wrapped above its anchor line, a manufacturer with
its legal form), the matcher prices exactly the oracle's four rows and counts the other three by
their reasons, the totals are the oracle's, and the pass holds exactly the oracle's four
``cheaper_analog`` proposals -- each priced from a matched position and a proposed position in the
same unit and currency, the saving ``(current - proposed) x quantity`` and absent (never ``0``)
where the printed quantity is a dash. ``expected_specification.json`` is computed by
``tools/fixtures/build_ar_specification.py`` from the authored numbers, never read from the
product, so this test compares the product with an independent figure.

The lane database persists between runs, so every run works in a project of its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE
from tests.support.published_run import publish_reference_run

DEPLOYMENT_SECRET = "spec-table-recording-token"
EXPERT = "spec-table-recording-expert"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar_specification"
RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections" / "ar_specification"
ORACLE = json.loads((FIXTURES / "expected_specification.json").read_text(encoding="utf-8"))


def _load_dotenv() -> None:
    """Fill the names the composed application reads from the repository ``.env`` (data only)."""
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.removeprefix("export ").partition("=")
        name, value = name.strip(), value.strip()
        if separator and name and not os.environ.get(name):
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ[name] = value


_load_dotenv()


def _key(tag: str) -> dict[str, str]:
    return {IDEMPOTENCY_HEADER: f"spec-table-{tag}-{secrets.token_hex(6)}"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def expert() -> dict[str, str]:
    from am_test_accounts import provisioned_credential

    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, EXPERT)}"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _upload_bundle(client: TestClient, headers: dict[str, str], project: str) -> dict[str, Any]:
    boundary = "specTableBoundary"
    bundle = (FIXTURES / "ar_specification.zip").read_bytes()
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_specification.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    answer = client.post(
        f"/projects/{project}/documents",
        headers=headers | _key("upload") | {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + bundle + f"\r\n--{boundary}--\r\n".encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


@pytest.fixture(scope="module")
def journey(client: TestClient, expert: dict[str, str]) -> dict[str, Any]:
    """Steps 1-6, in order; the facts each step returned are kept for the tests."""
    tag = uuid.uuid4().hex[:10]
    created = client.post("/projects", json={"name": f"Спецификация и цены {tag}"},
                          headers=expert | _key("project"))
    assert created.status_code == 201, created.content
    project = created.json()["project_uid"]

    uploaded = _upload_bundle(client, expert, project)
    document, version = uploaded["document_uid"], uploaded["version_uid"]

    classified = client.put(
        f"/projects/{project}/documents/{document}/versions/{version}/classification",
        headers=expert,
        json=ORACLE["journey"]["classification"],
    )
    assert classified.status_code == 200, classified.content

    refused = client.post("/runs", headers=expert | _key("run"), json={"version_uid": version})
    assert refused.status_code == 422, refused.content
    assert refused.json()["error_code"] == "section_profile_unavailable", refused.content
    run_id = publish_reference_run(version, tag="spec-table")
    run = client.get(f"/runs/{run_id}", headers=expert)
    assert run.status_code == 200, run.content

    prices_url = f"/projects/{project}/documents/{document}/specification-prices"
    before_prices = client.get(prices_url, headers=expert)
    assert before_prices.status_code == 200, before_prices.content

    price_list = client.post(
        f"/projects/{project}/price-lists",
        files={"file": ("ar_specification_prices.csv",
                        (FIXTURES / "ar_specification_prices.csv").read_bytes(), "text/csv")},
        data={"default_currency": ORACLE["journey"]["price_list_default_currency"]},
        headers=expert | _key("prices"),
    )
    assert price_list.status_code == 201, price_list.content
    price_list_id = price_list.json()["price_list_id"]

    vendors = client.put(
        f"/projects/{project}/vendor-lists/AR",
        json={"mode": "list", "entries": ORACLE["journey"]["project_vendor_list"]},
        headers=expert,
    )
    assert vendors.status_code == 200, vendors.content

    ready = client.get(prices_url, params={"limit": 200}, headers=expert)
    assert ready.status_code == 200, ready.content

    started_pass = client.post(
        f"/projects/{project}/documents/{document}/optimisation-passes",
        headers=expert | _key("pass"),
    )
    assert started_pass.status_code == 201, started_pass.content
    pass_id = started_pass.json()["optimisation_pass_id"]
    proposals = client.get(
        f"/optimisation-passes/{pass_id}/proposals", params={"limit": 200}, headers=expert
    )
    assert proposals.status_code == 200, proposals.content
    positions = client.get(
        f"/price-lists/{price_list_id}/positions", params={"limit": 500}, headers=expert
    )
    assert positions.status_code == 200, positions.content
    return {
        "project": project, "document": document, "version": version, "run_id": run_id,
        "run": run.json(), "before_prices": before_prices.json(), "ready": ready.json(),
        "price_list_id": price_list_id, "vendors": vendors.json(), "pass": started_pass.json(),
        "proposals": proposals.json(), "positions": positions.json()["items"],
    }


# -- the fixtures are what the oracle says they are ---------------------------------------------


def test_the_oracle_names_the_committed_files_by_digest() -> None:
    for entry in ORACLE["files"].values():
        path = REPOSITORY_ROOT / entry["path"]
        assert _sha256(path) == entry["sha256"], entry["path"]
        assert path.stat().st_size == entry["bytes"]
    sums = dict(
        reversed(line.split("  ", 1))
        for line in (FIXTURES / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    )
    assert set(sums) == {
        "ar_specification.pdf", "ar_specification.zip", "ar_specification_prices.csv",
        "expected_specification.json",
    }
    assert all(_sha256(FIXTURES / name) == digest for name, digest in sums.items())


def test_the_recorded_answer_is_synthetic_and_filed_under_the_request_it_answers() -> None:
    (path,) = sorted(RECORDINGS.glob("*.json"))
    document = json.loads(path.read_text(encoding="utf-8"))
    assert path.stem == document["request_sha256"]
    assert document["origin"]["kind"] == "synthetic"
    assert "No model produced this reply" in document["origin"]["statement"]
    assert not {"provider_mode", "mode"} & (set(document) | set(document["origin"]))
    observations = json.loads(document["output_text"])["observations"]
    assert all(item["finding_text"].startswith("Синтетический ответ") for item in observations)


def test_the_served_adapter_answers_the_request_over_the_committed_pdf() -> None:
    """Container-free: the key of the request the run will send is the recording's key."""
    from auditmanager.analysis.stages.extraction import extract_document
    from auditmanager.analysis.text.adapter import build_request
    from auditmanager.analysis.text.recorded import RecordedAdapter
    from auditmanager.analysis.text.textlayer import load_text_layer
    from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

    pages, cursor = [], 0
    for page in extract_document((FIXTURES / "ar_specification.pdf").read_bytes()).pages:
        pages.append({"page_number": page.page_number, "char_start": cursor,
                      "char_end": cursor + len(page.text), "text": page.text})
        cursor += len(page.text)
    layer = load_text_layer({
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": "ver_01M25P3TH0X4C5ZR8G4M2Q7WJH",
        "extractor": {"name": "pdfplumber", "version": "0.11.10", "options_sha256": ""},
        "normalization": {"id": "nfc_v1", "description": "Unicode NFC."},
        "total_char_count": cursor, "pages": pages,
    })
    request = build_request(
        model_id="claude-opus-5", bundle=V1_REFERENCE_PROFILE.prompt_bundle, text_layer=layer
    )
    (path,) = sorted(RECORDINGS.glob("*.json"))
    assert request.request_sha256 == path.stem
    served = RecordedAdapter()
    assert RECORDINGS in served.recording_dirs
    response = served.complete(request)
    assert response.stop_reason == "end_turn"
    assert json.loads(response.output_text)["observations"][0]["category"] == "explicit_placeholder"
    # The canonical directory alone does not hold it: this answer lives in its own directory.
    assert RecordedAdapter(served.recording_dir).recording_dirs == (served.recording_dir,)


def test_both_builders_report_no_drift() -> None:
    import subprocess
    import sys

    for script in ("tools/fixtures/build_ar_specification.py",
                   "fixtures/recorded/sections/ar_specification/build_fixtures.py"):
        completed = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / script), "--check"],
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT / "src")},
            capture_output=True, text=True, timeout=240, check=False,
        )
        assert completed.returncode == 0, (script, completed.stderr)


# -- the journey ---------------------------------------------------------------------------------


def test_the_recorded_run_publishes_with_the_seeded_placeholder(journey, client, expert) -> None:
    assert journey["run"]["state"] == "published", journey["run"]
    findings = client.get(f"/runs/{journey['run_id']}/findings", headers=expert)
    assert findings.status_code == 200, findings.content
    items = findings.json()["items"]
    assert [item["category"] for item in items] == [ORACLE["seeded_observation"]["category"]]


def test_before_a_price_list_the_specification_is_not_priced(journey) -> None:
    body = journey["before_prices"]
    assert body["state"] == "price_list_missing"
    assert (body["section_code"], body["project_stage"]) == ("AR", "P")
    assert body["rows"] is None


def test_the_extractor_reads_the_oracle_rows_across_both_sheets(journey) -> None:
    body = journey["ready"]
    assert body["state"] == "ready"
    expected = ORACLE["specification"]
    extraction = body["extraction"]
    assert extraction["algorithm"] == expected["algorithm"]
    assert (extraction["table_count"], extraction["row_count"]) == (
        expected["table_count"], expected["row_count"],
    )
    # One table: the second sheet adds rows to it, it does not open a second one.
    (table,) = extraction["tables"]
    assert table["row_count"] == expected["row_count"]
    assert table["page_number"] == min(expected["pages"])

    items = body["rows"]["items"]
    assert [row["position"] for row in items] == [row["position"] for row in expected["rows"]]
    for got, want in zip(items, expected["rows"], strict=True):
        assert (got["page_number"], got["sheet_label"]) == (want["page"], want["sheet_label"])
        assert got["name"] == want["name"]
        assert got["unit"] == want["unit"]
        assert got["quantity_text"] == want["quantity_text"]
        assert (got["quantity"] is None) == (want["quantity"] is None)
        if want["quantity"] is not None:
            assert Decimal(got["quantity"]) == Decimal(want["quantity"])
        assert got["table_ordinal"] == 1


def test_the_matcher_prices_the_oracle_rows_and_counts_the_rest_by_reason(journey) -> None:
    body = journey["ready"]
    expected = ORACLE["matching"]
    matching = body["matching"]
    assert matching["algorithm"] == expected["algorithm"]
    assert matching["counts"] == expected["counts"]
    assert matching["excluded"] == expected["excluded"]
    (total,) = matching["totals"]
    want = expected["totals"][0]
    assert (total["currency"], total["row_count"]) == (want["currency"], want["row_count"])
    assert Decimal(total["amount"]) == Decimal(want["amount"])

    for got, row in zip(body["rows"]["items"], ORACLE["specification"]["rows"], strict=True):
        assert got["status"] == row["status"], row["position"]
        assert got["reason"] == row["reason"], row["position"]
        assert got["basis"] == row["basis"], row["position"]
        if row["amount"] is None:
            assert got["amount"] is None, row["position"]
            assert got["excluded_reason"] == row["excluded_reason"], row["position"]
        else:
            assert Decimal(got["amount"]) == Decimal(row["amount"]), row["position"]
            assert got["excluded_reason"] is None


def test_the_pass_pins_its_inputs_and_holds_the_oracle_proposals(journey) -> None:
    expected = ORACLE["proposals"]
    started = journey["pass"]
    assert started["generator_version"] == expected["generator"]
    assert started["vendor_list_source"] == "project"
    assert started["price_list_id"] == journey["price_list_id"]
    assert started["run_id"] == journey["run_id"]
    assert (started["specification_row_count"], started["matched_row_count"],
            started["proposed_row_count"], started["proposal_count"]) == (
        ORACLE["specification"]["row_count"], ORACLE["matching"]["counts"]["matched"],
        len({item["row_position"] for item in expected["items"]}), expected["count"],
    )

    items = journey["proposals"]["items"]
    assert len(items) == expected["count"] >= 1
    positions = {position["price_list_position_id"]: position for position in journey["positions"]}
    for got, want in zip(items, expected["items"], strict=True):
        assert got["proposal_type"] == want["proposal_type"] == "cheaper_analog"
        assert got["ordinal"] == want["ordinal"]
        assert got["row_position"] == want["row_position"]
        assert got["analog_basis"] == want["analog_basis"]
        assert got["proposed_vendor"] == want["proposed_vendor"]
        assert (got["unit"], got["currency"]) == (want["unit"], want["currency"])
        assert Decimal(got["current_unit_price"]) == Decimal(want["current_unit_price"])
        assert Decimal(got["proposed_unit_price"]) == Decimal(want["proposed_unit_price"])
        if want["saving"] is None:
            assert got["saving"] is None and got["quantity"] is None, want["row_position"]
        else:
            assert Decimal(got["saving"]) == Decimal(want["saving"]), want["row_position"]

        # Every price in a proposal is a price-list position's, in one unit and one currency.
        matched = positions[got["matched_position"]["price_list_position_id"]]
        proposed = positions[got["proposed_position"]["price_list_position_id"]]
        assert matched["price_list_position_id"] != proposed["price_list_position_id"]
        assert matched["unit"] == proposed["unit"]
        assert matched["currency"] == proposed["currency"] == got["currency"]
        assert Decimal(matched["unit_price"]) == Decimal(got["current_unit_price"])
        assert Decimal(proposed["unit_price"]) == Decimal(got["proposed_unit_price"])
        assert Decimal(proposed["unit_price"]) < Decimal(matched["unit_price"])
        if got["quantity"] is not None:
            assert Decimal(got["saving"]) == (
                Decimal(matched["unit_price"]) - Decimal(proposed["unit_price"])
            ) * Decimal(got["quantity"])


def test_the_total_saving_is_the_sum_of_the_computable_savings(journey) -> None:
    savings = [Decimal(item["saving"]) for item in journey["proposals"]["items"]
               if item["saving"] is not None]
    assert sum(savings) == Decimal(ORACLE["proposals"]["total_saving"]["amount"])
    assert any(item["saving"] is None for item in journey["proposals"]["items"])


def test_rows_that_are_not_priced_never_become_proposals(journey) -> None:
    proposed = {item["row_position"] for item in journey["proposals"]["items"]}
    unpriced = {row["position"] for row in ORACLE["specification"]["rows"]
                if row["status"] == "unmatched"}
    assert unpriced == {"4", "5"}
    assert not proposed & unpriced
