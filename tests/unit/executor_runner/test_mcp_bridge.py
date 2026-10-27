"""The stdio MCP bridge, driven over its stdio against a fake runner API."""

from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]


def _claim(session, wait=3):
    return session.call("claim_task", {"wait_seconds": wait})


def test_initialize_handshake_matches_the_spec_fields():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        reply = mcp.request(
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "claude-code", "version": "9"}},
        )
        result = reply["result"]
        assert reply["jsonrpc"] == "2.0" and reply["id"] == 1
        assert result["protocolVersion"] == "2025-06-18"  # a supported version is echoed
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "pdf-analysis-runner"
        assert "resultType" not in result  # legacy era
        mcp.notify("notifications/initialized")
        assert mcp.request("ping")["result"] == {}  # the notification produced no reply of its own
        # an unknown version is answered with the latest the server supports (spec: version negotiation)
        other = mcp.request("initialize", {"protocolVersion": "1999-01-01", "capabilities": {}, "clientInfo": {}})
        assert other["result"]["protocolVersion"] == "2025-11-25"


def test_modern_discover_and_unsupported_version():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientInfo": {"name": "c", "version": "1"}, "io.modelcontextprotocol/clientCapabilities": {}}
        discover = mcp.request("server/discover", {"_meta": meta})["result"]
        assert discover["resultType"] == "complete"
        assert discover["supportedVersions"] == ["2026-07-28"]
        assert "tools" in discover["capabilities"]
        assert discover["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "pdf-analysis-runner"
        listed = mcp.request("tools/list", {"_meta": meta})["result"]
        assert listed["resultType"] == "complete" and len(listed["tools"]) == 3
        bad = mcp.request("tools/list", {"_meta": {"io.modelcontextprotocol/protocolVersion": "1900-01-01"}})
        assert bad["error"]["code"] == -32022
        assert bad["error"]["data"] == {"supported": ["2026-07-28"], "requested": "1900-01-01"}


def test_tools_list_names_and_input_schemas():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        tools = mcp.request("tools/list")["result"]["tools"]
        assert [t["name"] for t in tools] == ["claim_task", "submit_answer", "report_failure"]
        by_name = {t["name"]: t for t in tools}
        for tool in tools:
            assert tool["inputSchema"]["type"] == "object" and tool["description"]
        assert by_name["submit_answer"]["inputSchema"]["required"] == ["task_id", "output_text", "model"]
        assert by_name["report_failure"]["inputSchema"]["required"] == ["task_id", "reason"]
        assert mcp.request("nope/method")["error"]["code"] == -32601
        assert mcp.request("tools/call", {"name": "bash", "arguments": {}})["error"]["code"] == -32602


def test_claim_then_answer_round_trip():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task())
        result = _claim(mcp)
        assert result["isError"] is False
        task = mcp.payload(result)
        assert task["status"] == "task" and task["task_id"] == "ext_TASK1" and task["model"] == "claude-opus-5"
        assert task["user_text"].startswith("Document text") and task["output_schema"]["required"] == ["findings"]
        assert task["notice"]
        claim_request = runner.of_kind("claim")[0]
        assert claim_request["authorization"] == "Bearer " + S.TOKEN
        assert claim_request["body"]["wait_seconds"] == 3 and claim_request["path"] == "/api/v1/runner/tasks/claim"

        answer = mcp.call(
            "submit_answer",
            {"task_id": "ext_TASK1", "output_text": '{"findings": []}', "model": "claude-opus-5", "input_tokens": 10, "output_tokens": 4},
        )
        assert answer["isError"] is False and mcp.payload(answer)["status"] == "accepted"
        sent = runner.of_kind("answer")[0]
        assert sent["path"] == "/api/v1/runner/tasks/ext_TASK1/answer"
        assert sent["body"] == {"output_text": '{"findings": []}', "model": "claude-opus-5", "input_tokens": 10, "output_tokens": 4}
        assert sent["content_type"].startswith("application/json")


def test_text_only_bridge_refuses_image_task_without_exposing_it():
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": "a" * 64, "size_bytes": 8, "media_type": "image/png"}
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task(images=[image]))
        result = _claim(mcp)
        assert mcp.payload(result)["status"] == "unsupported_image_task"
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == []
        assert image["sha256"] not in mcp.text(result)


def test_image_capable_bridge_returns_verified_mcp_image_content():
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL7WQAAAABJRU5ErkJggg=="
    )
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
             "media_type": "image/png"}
    with S.FakeRunner() as runner, S.McpSession(runner.origin, extra_args=("--accept-images",)) as mcp:
        mcp.initialize()
        runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_MCPIMG", images=[image]))
        result = _claim(mcp)
        assert mcp.payload(result)["status"] == "task"
        assert mcp.payload(result)["image_portal_block_id"] == image["portal_block_id"]
        assert base64.b64decode(result["content"][1]["data"]) == raw
        assert result["content"][1]["mimeType"] == "image/png"
        assert len(runner.of_kind("image")) == 1
        assert mcp.payload(mcp.call("submit_answer", {
            "task_id": "ext_MCPIMG", "model": "claude-opus-5", "output_text": '{"findings": []}',
        }))["status"] == "accepted"


def test_image_capable_bridge_fails_corrupted_bytes_without_exposing_an_image():
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": "a" * 64, "size_bytes": 8, "media_type": "image/png"}
    with S.FakeRunner() as runner, S.McpSession(runner.origin, extra_args=("--accept-images",)) as mcp:
        mcp.initialize()
        runner.add_image(image["blob_id"], b"bad-data")
        runner.add_task(S.make_task("ext_MCPBAD", images=[image]))
        result = _claim(mcp)
        assert mcp.payload(result)["status"] == "image_delivery_failed"
        assert len(result["content"]) == 1
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_delivery_failed"
        assert not runner.of_kind("answer")


def test_idle_204_returns_idle_after_the_wait():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        started = time.monotonic()
        result = _claim(mcp, wait=2)
        elapsed = time.monotonic() - started
        assert result["isError"] is False and mcp.payload(result)["status"] == "idle"
        assert 1.5 <= elapsed < 6
        zero = mcp.call("claim_task", {"wait_seconds": 0})
        assert mcp.payload(zero)["status"] == "idle"
        assert mcp.call("claim_task", {"wait_seconds": 601})["isError"] is True


def test_401_is_surfaced_as_a_tool_error_and_the_bridge_survives():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.revoked = True
        result = _claim(mcp, wait=0)
        assert result["isError"] is True
        text = mcp.text(result)
        assert "401" in text and "token" in text and "Do not retry" in text
        assert mcp.request("ping")["result"] == {}
        assert len(runner.of_kind("claim")) == 1  # never retried


def test_409_on_answer_is_surfaced_and_drops_the_task():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task())
        _claim(mcp)
        runner.override("answer", S.Reply(409, S.envelope("conflict", "Another answer was already accepted.")))
        result = mcp.call("submit_answer", {"task_id": "ext_TASK1", "output_text": "{}", "model": "claude-opus-5"})
        assert result["isError"] is True
        assert "409" in mcp.text(result) and "no longer yours" in mcp.text(result) and "Another answer" in mcp.text(result)
        assert len(runner.of_kind("answer")) == 1


def test_422_schema_refusal_is_surfaced_and_the_claim_is_kept():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task())
        _claim(mcp)
        runner.override("answer", S.Reply(422, S.envelope("validation_failed", "output_text: 'findings' is a required property.")))
        refused = mcp.call("submit_answer", {"task_id": "ext_TASK1", "output_text": "{}", "model": "claude-opus-5"})
        assert refused["isError"] is True
        text = mcp.text(refused)
        assert "422" in text and "validation_failed" in text and "'findings' is a required property" in text and "claim is kept" in text
        fixed = mcp.call("submit_answer", {"task_id": "ext_TASK1", "output_text": '{"findings": []}', "model": "claude-opus-5"})
        assert fixed["isError"] is False and mcp.payload(fixed)["status"] == "accepted"
        assert len(runner.of_kind("answer")) == 2


def test_model_declaration_that_differs_from_the_task_is_refused_locally():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task(model="claude-opus-5"))
        _claim(mcp)
        result = mcp.call("submit_answer", {"task_id": "ext_TASK1", "output_text": "{}", "model": "claude-sonnet-5"})
        assert result["isError"] is True and "claude-opus-5" in mcp.text(result) and "model_mismatch" in mcp.text(result)
        assert runner.of_kind("answer") == []


def test_claim_is_extended_while_held_and_a_lost_claim_blocks_the_submit():
    with S.FakeRunner(lease=3) as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task(lease=3))
        _claim(mcp)
        runner.wait_for("extend", 2, timeout=6)  # kept alive in the background without the session doing anything
        assert all(r["task_id"] == "ext_TASK1" and r["path"].endswith("/ext_TASK1/extend") for r in runner.of_kind("extend"))
        runner.override("extend", S.Reply(409, S.envelope("state_transition_not_allowed", "The claim is lost.")))
        runner.wait_for("extend", 3, timeout=6)  # the third extension is the one that is refused
        time.sleep(0.5)
        result = mcp.call("submit_answer", {"task_id": "ext_TASK1", "output_text": "{}", "model": "claude-opus-5"})
        text = mcp.text(result)
        assert result["isError"] is True and "claim on ext_TASK1 is lost" in text
        assert runner.of_kind("answer") == []  # nothing was sent for a lost claim


def test_429_is_honoured_before_the_next_claim():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.override("claim", S.Reply(429, S.envelope("rate_limited", "Slow down.", True), {"Retry-After": "1"}))
        runner.add_task(S.make_task())
        result = _claim(mcp, wait=6)
        assert mcp.payload(result)["status"] == "task"
        first, second = runner.of_kind("claim")[:2]
        assert second["t"] - first["t"] >= 1.0


def test_unreachable_stand_is_reported_not_swallowed():
    with S.FakeRunner() as runner:
        origin = runner.origin
    with S.McpSession(origin) as mcp:  # the server is gone: connection refused
        mcp.initialize()
        result = _claim(mcp, wait=0)
        assert result["isError"] is True and mcp.payload(result)["status"] == "stand_unavailable"


def test_the_token_never_appears_in_results_stdout_or_stderr():
    token = "amr_SENTINEL_s3cr3t_value_0042"
    with S.FakeRunner(token=token) as runner, S.McpSession(runner.origin, token=token) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task())
        _claim(mcp)
        # a hostile or buggy server that echoes the credential back in its error message
        runner.override("answer", S.Reply(422, S.envelope("validation_failed", f"bad header Authorization: Bearer {token}")))
        refused = mcp.call("submit_answer", {"task_id": "ext_TASK1", "output_text": "{}", "model": "claude-opus-5"})
        assert token not in mcp.text(refused) and "***" in mcp.text(refused)
        runner.override("fail", S.Reply(500, S.envelope("internal_error", f"token={token}")))
        failed = mcp.call("report_failure", {"task_id": "ext_TASK1", "reason": "cannot_answer"}, timeout=5)
        assert failed["isError"] is True and token not in mcp.text(failed) and "***" in mcp.text(failed)
        runner.revoked = True
        mcp.call("claim_task", {"wait_seconds": 0})
        code = mcp.close()
        assert code == 0
        assert token not in b"".join(mcp.raw_stdout).decode("utf-8")
        assert token not in mcp.stderr
        assert "claimed ext_TASK1" in mcp.stderr  # the bridge does log, and logs without the token


def test_redirects_are_not_followed_so_the_token_stays_put():
    with S.FakeRunner() as elsewhere, S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.override("claim", S.Reply(302, None, {"Location": elsewhere.origin + "/api/v1/runner/tasks/claim"}))
        result = _claim(mcp, wait=0)
        assert result["isError"] is True and "redirect refused" in mcp.text(result)
        assert elsewhere.requests == []


def test_a_cancelled_claim_gets_no_reply():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        mcp.send({"jsonrpc": "2.0", "id": 77, "method": "tools/call", "params": {"name": "claim_task", "arguments": {"wait_seconds": 1}}})
        runner.wait_for("claim", 1)
        mcp.notify("notifications/cancelled", {"requestId": 77, "reason": "user"})
        assert mcp.request("ping")["result"] == {}
        time.sleep(2.0)  # past the end of the 1 s poll
        while not mcp.lines.empty():
            assert mcp.read().get("id") != 77


def test_report_failure_posts_the_reason_and_tolerates_a_terminal_task():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        runner.add_task(S.make_task())
        _claim(mcp)
        ok = mcp.call("report_failure", {"task_id": "ext_TASK1", "reason": "model_mismatch: running claude-sonnet-5"})
        assert ok["isError"] is False and mcp.payload(ok)["status"] == "failed"
        assert runner.of_kind("fail")[0]["body"] == {"reason": "model_mismatch: running claude-sonnet-5"}
        runner.override("fail", S.Reply(409, S.envelope("state_transition_not_allowed", "Already terminal.")))
        again = mcp.call("report_failure", {"task_id": "ext_TASK1", "reason": "again"})
        assert again["isError"] is False and mcp.payload(again)["status"] == "not_failed"
        assert mcp.call("report_failure", {"task_id": "ext_TASK1"})["isError"] is True  # reason missing


def test_a_hostile_task_id_cannot_steer_the_request_path():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        result = mcp.call("submit_answer", {"task_id": "../../claim?x=1", "output_text": "{}", "model": "claude-opus-5"})
        assert result["isError"] is True
        assert runner.requests == []


def _run_bridge(*args, token="tok"):
    env = S.clean_env()
    if token is not None:
        env["PDF_ANALYSIS_RUNNER_TOKEN"] = token
    return subprocess.run([sys.executable, str(S.BRIDGE), *args], capture_output=True, text=True, env=env, input="", timeout=20)


def test_startup_refuses_a_missing_token_a_bad_origin_and_clear_text_http():
    missing = _run_bridge("--origin", "https://stand.example.org", token=None)
    assert missing.returncode == 2 and "PDF_ANALYSIS_RUNNER_TOKEN is not set" in missing.stderr
    insecure = _run_bridge("--origin", "http://stand.example.org")
    assert insecure.returncode == 2 and "refusing http://" in insecure.stderr
    with_path = _run_bridge("--origin", "https://stand.example.org/api")
    assert with_path.returncode == 2 and "no path" in with_path.stderr
    allowed = _run_bridge("--origin", "http://stand.example.org", "--allow-insecure-http")
    assert allowed.returncode == 0  # explicit opt-in; stdin is empty so it exits at once
    loopback = _run_bridge("--origin", "http://127.0.0.1:9", token="amr_SENTINEL_77")
    assert loopback.returncode == 0
    assert "amr_SENTINEL_77" not in loopback.stderr + loopback.stdout


def test_stdout_carries_only_json_rpc_lines():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        mcp.request("tools/list")
        mcp.send({"jsonrpc": "2.0", "id": 5, "method": "ping"})
        mcp.read()
        mcp.proc.stdin.write(b"this is not json\n")
        mcp.proc.stdin.flush()
        error = mcp.read()
        assert error["error"]["code"] == -32700 and error["id"] is None
        mcp.close()
        for line in mcp.raw_stdout:
            assert json.loads(line)["jsonrpc"] == "2.0"
            assert line.endswith(b"\n") and line.count(b"\n") == 1


# -- several images, `CMP-EXEC-IMAGES-01` --------------------------------------------------------


def test_a_bridge_that_declared_three_images_returns_all_three_in_order_with_their_references():
    made = [S.make_image(label) for label in ("left", "right", "detail")]
    with S.FakeRunner() as runner, S.McpSession(
            runner.origin, extra_args=("--accept-images", "--max-images", "3")) as mcp:
        mcp.initialize()
        for image, raw in made:
            runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_MCP3", images=[image for image, _ in made]))
        result = _claim(mcp)
        payload = mcp.payload(result)
        assert payload["status"] == "task" and "image_portal_block_id" not in payload
        assert payload["image_references"] == [
            {"index": 1, "crop_id": "crop-left"}, {"index": 2, "crop_id": "crop-right"},
            {"index": 3, "crop_id": "crop-detail"}]
        assert "all 3" in payload["image_notice"] and "image_input_unsupported" in payload["image_notice"]
        assert [block["type"] for block in result["content"]] == ["text", "image", "image", "image"]
        assert [base64.b64decode(block["data"]) for block in result["content"][1:]] == [raw for _, raw in made]
        assert runner.of_kind("claim")[0]["body"]["max_images"] == 3
        assert len(runner.of_kind("image")) == 3 and not runner.of_kind("fail")


def test_a_bridge_with_the_default_count_refuses_a_task_of_two_images_whole():
    made = [S.make_image(label) for label in ("a", "b")]
    with S.FakeRunner() as runner, S.McpSession(runner.origin, extra_args=("--accept-images",)) as mcp:
        mcp.initialize()
        for image, raw in made:
            runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_MCP2", images=[image for image, _ in made]))
        result = _claim(mcp)
        assert mcp.payload(result)["status"] == "unsupported_image_task"
        assert len(result["content"]) == 1, "no image is shown to the session"
        assert "max_images" not in runner.of_kind("claim")[0]["body"], "the default declares one, as ever"
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == [] and not runner.of_kind("answer")


def test_a_bridge_fails_the_whole_task_when_one_of_its_images_cannot_be_delivered():
    made = [S.make_image(label) for label in ("a", "b", "c")]
    with S.FakeRunner() as runner, S.McpSession(
            runner.origin, extra_args=("--accept-images", "--max-images", "3")) as mcp:
        mcp.initialize()
        runner.add_image(made[0][0]["blob_id"], made[0][1])
        runner.add_image(made[1][0]["blob_id"], b"\x89PNG\r\n\x1a\nchanged")
        runner.add_image(made[2][0]["blob_id"], made[2][1])
        runner.add_task(S.make_task("ext_MCPB3", images=[image for image, _ in made]))
        result = _claim(mcp)
        assert mcp.payload(result)["status"] == "image_delivery_failed"
        assert len(result["content"]) == 1
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_delivery_failed"


def test_the_one_portal_block_image_result_is_what_it_was():
    image, raw = S.make_image("block", crop=False)
    with S.FakeRunner() as runner, S.McpSession(runner.origin, extra_args=("--accept-images",)) as mcp:
        mcp.initialize()
        runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_MCP1", images=[image]))
        result = _claim(mcp)
        payload = mcp.payload(result)
        assert payload["image_portal_block_id"] == image["portal_block_id"]
        assert "image_references" not in payload and "image_notice" not in payload
        assert "max_images" not in runner.of_kind("claim")[0]["body"], "the old claim wire"
        assert [block["type"] for block in result["content"]] == ["text", "image"]


def test_one_crop_image_is_listed_by_its_opaque_reference():
    image, raw = S.make_image("one")
    with S.FakeRunner() as runner, S.McpSession(runner.origin, extra_args=("--accept-images",)) as mcp:
        mcp.initialize()
        runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_MCPC", images=[image]))
        payload = mcp.payload(_claim(mcp))
        assert payload["image_references"] == [{"index": 1, "crop_id": "crop-one"}]
        assert "image_portal_block_id" not in payload


import pytest  # noqa: E402


@pytest.mark.parametrize("args", [("--max-images", "3"), ("--accept-images", "--max-images", "9"),
                                  ("--accept-images", "--max-images", "0")])
def test_max_images_needs_the_image_switch_and_a_count_from_one_to_eight(args):
    import subprocess
    import sys

    result = subprocess.run([sys.executable, str(S.BRIDGE), "--origin", "http://127.0.0.1:1", *args],
                            env=S.clean_env(PDF_ANALYSIS_RUNNER_TOKEN=S.TOKEN), capture_output=True,
                            text=True, timeout=20)
    assert result.returncode == 2, result.stderr
