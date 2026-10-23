"""The subscription Codex command's fixed boundary, with a fake CLI (no model call)."""

from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "tools/executor-runner/codex_answer.py"
SPEC = importlib.util.spec_from_file_location("pdfa_codex_answer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
codex_answer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = codex_answer
SPEC.loader.exec_module(codex_answer)


TASK = {
    "model": "gpt-6-sol", "system": "Return JSON.", "user_text": "A page of data.",
    "output_schema": {"type": "object", "properties": {"ok": {"type": "boolean"}},
                      "required": ["ok"], "additionalProperties": False},
}


def fake_codex(tmp_path: Path, case: str = "ok") -> str:
    path = tmp_path / "codex"
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "assert args[0] == 'exec'\n"
        "assert all(x in args for x in ('--ignore-user-config', '--skip-git-repo-check', "
        "'--ephemeral', '--json', '--output-schema', '--output-last-message'))\n"
        "assert args[args.index('--sandbox') + 1] == 'read-only'\n"
        "assert args[args.index('--model') + 1] == 'gpt-6-sol'\n"
        "assert 'features.shell_tool=false' in args\n"
        "assert 'web_search=\\\"disabled\\\"' in args\n"
        "if '--image' in args:\n"
        " image = pathlib.Path(args[args.index('--image') + 1])\n"
        " assert image.read_bytes().startswith(b'\\x89PNG\\r\\n\\x1a\\n')\n"
        "assert os.getenv('OPENAI_API_KEY') is None\n"
        "assert os.getenv('PDF_ANALYSIS_RUNNER_TOKEN') is None\n"
        "schema = json.loads(pathlib.Path(args[args.index('--output-schema') + 1]).read_text())\n"
        "assert schema['required'] == ['ok']\n"
        "prompt = sys.stdin.read()\n"
        "assert 'Return JSON.' in prompt and 'A page of data.' in prompt\n"
        "path = pathlib.Path(args[args.index('--output-last-message') + 1])\n"
        f"case = {case!r}\n"
        "path.write_text('not json' if case == 'bad_json' else '{\"ok\":true}')\n"
        "print(json.dumps({'type':'thread.started','thread_id':'local'}))\n"
        "print(json.dumps({'type':'turn.started'}))\n"
        "if case == 'tool':\n"
        " print(json.dumps({'type':'item.started','item':{'type':'command_execution'}}))\n"
        "if case == 'reroute':\n"
        " print(json.dumps({'type':'model.rerouted'}))\n"
        "if case == 'failed':\n"
        " print(json.dumps({'type':'turn.failed'}))\n"
        "elif case != 'incomplete':\n"
        " print(json.dumps({'type':'turn.completed','usage':{'input_tokens':12,"
        "'output_tokens':3}}))\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return str(path)


def test_pinned_subscription_task_returns_only_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-codex")
    monkeypatch.setenv("PDF_ANALYSIS_RUNNER_TOKEN", "must-not-reach-codex")
    task = codex_answer.read_task(json.dumps(TASK).encode())
    assert codex_answer.answer(task, codex=fake_codex(tmp_path)) == '{"ok":true}'


@pytest.mark.parametrize("case,reason", [
    ("tool", "codex_tool_event"),
    ("reroute", "codex_turn_failed"),
    ("failed", "codex_turn_failed"),
    ("incomplete", "codex_turn_incomplete"),
    ("bad_json", "codex_answer_not_json"),
])
def test_unusable_codex_turn_fails_closed(tmp_path: Path, case: str, reason: str) -> None:
    with pytest.raises(codex_answer.TaskError, match=f"^{reason}$"):
        codex_answer.answer(TASK, codex=fake_codex(tmp_path, case))


def test_wrong_model_and_missing_schema_never_start_codex() -> None:
    with pytest.raises(codex_answer.TaskError, match="model_mismatch"):
        codex_answer.read_task(json.dumps({**TASK, "model": "claude-opus-5"}).encode())
    with pytest.raises(codex_answer.TaskError, match="missing_object_schema"):
        codex_answer.read_task(json.dumps({**TASK, "output_schema": None}).encode())
    with pytest.raises(codex_answer.TaskError, match="task_too_large"):
        codex_answer.read_task(b"x" * (codex_answer.MAX_TASK_BYTES + 1))


def test_verified_png_reaches_codex_as_an_image_and_a_changed_file_is_refused(tmp_path: Path) -> None:
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL7WQAAAABJRU5ErkJggg=="
    )
    path = tmp_path / "crop.png"
    path.write_bytes(raw)
    image = {
        "blob_id": "blob_01M2545JSD15ETSNNV904X991F",
        "portal_block_id": "blk_" + "a" * 32,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "media_type": "image/png",
    }
    task = codex_answer.read_task(json.dumps({
        **TASK, "images": [image], "local_images": [{**image, "path": str(path)}],
    }).encode())
    assert codex_answer.answer(task, codex=fake_codex(tmp_path)) == '{"ok":true}'
    path.write_bytes(raw + b"changed")
    with pytest.raises(codex_answer.TaskError, match="^image_input_invalid$"):
        codex_answer.answer(task, codex=fake_codex(tmp_path))
