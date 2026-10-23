from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "tools/executor-runner/ssh-forced-command.sh"


@pytest.mark.parametrize("with_image,reported,structured", [(False, "claude-opus-5", False),
                                                             (True, "claude-opus-5", False),
                                                             (True, "other-model", False),
                                                             (True, "claude-opus-5", True)])
def test_forced_command_sends_image_block_and_reports_exact_model(
    tmp_path: Path, with_image: bool, reported: str, structured: bool,
) -> None:
    home = tmp_path / "home"
    binary = home / ".local/bin/claude"
    binary.parent.mkdir(parents=True)
    capture = tmp_path / "stdin"
    argv_capture = tmp_path / "argv"
    binary.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "open(os.environ['TEST_CAPTURE'], 'wb').write(sys.stdin.buffer.read())\n"
        "open(os.environ['TEST_ARGV'], 'w').write(json.dumps(sys.argv))\n"
        "doc = {'type':'result','subtype':'success','result':'ok',"
        "'modelUsage':{os.environ['TEST_MODEL']:{'inputTokens':3,'outputTokens':1}},"
        "'total_cost_usd':0.01}\n"
        "if os.environ.get('TEST_STRUCTURED') == '1': doc['structured_output'] = {'observations': []}\n"
        "print(json.dumps(doc))\n"
    )
    binary.chmod(0o700)
    config = home / ".config/pdf-analysis"
    config.mkdir(parents=True)
    credential = config / "claude.env"
    credential.write_text("ANTHROPIC_API_KEY=test-key\n")
    credential.chmod(0o600)
    task = {"model": "claude-opus-5", "system": "system", "user_text": "describe"}
    if with_image:
        import base64
        task["image"] = {"media_type": "image/png", "data": base64.b64encode(
            b"\x89PNG\r\n\x1a\nimage").decode()}
    if structured:
        task["output_schema"] = {"type": "object", "properties": {"observations": {"type": "array"}}}
    environment = {**os.environ, "HOME": str(home), "TEST_CAPTURE": str(capture),
                   "TEST_MODEL": reported, "TEST_ARGV": str(argv_capture),
                   "TEST_STRUCTURED": "1" if structured else "0",
                   "PDF_ANALYSIS_CLAUDE_ENV_FILE": str(credential)}
    result = subprocess.run(
        ["bash", str(SCRIPT)], input=json.dumps(task).encode(), env=environment,
        capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    reply = json.loads(result.stdout)
    assert reply["model"] == reported
    if structured:
        assert json.loads(reply["output_text"]) == {"observations": []}
        assert "--json-schema" in json.loads(argv_capture.read_text())
    else:
        assert reply["output_text"] == "ok"
    assert reply["input_tokens"] == 3 and reply["output_tokens"] == 1
    passed = capture.read_text()
    if with_image:
        event = json.loads(passed)
        assert event["message"]["content"][1]["type"] == "image"
        assert event["message"]["content"][1]["source"]["media_type"] == "image/png"
    else:
        assert passed == "describe"
