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


# -- several images, `CMP-EXEC-IMAGES-01` --------------------------------------------------------

_SUPPORT = "executor_runner_support"
if _SUPPORT not in sys.modules:
    _support_spec = importlib.util.spec_from_file_location(_SUPPORT, Path(__file__).with_name("_support.py"))
    _support = importlib.util.module_from_spec(_support_spec)
    sys.modules[_SUPPORT] = _support
    _support_spec.loader.exec_module(_support)
S = sys.modules[_SUPPORT]


def recording_codex(tmp_path: Path) -> tuple[str, Path]:
    """A fake Codex that records its argument list, the prompt and the bytes of every image."""
    record = tmp_path / "codex-record.json"
    path = tmp_path / "codex-recording"
    path.write_text(
        f"#!{sys.executable}\n"
        "import base64, json, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "images = [pathlib.Path(args[i + 1]).read_bytes() for i, a in enumerate(args) if a == '--image']\n"
        f"pathlib.Path({str(record)!r}).write_text(json.dumps({{'args': args, 'prompt': sys.stdin.read(),\n"
        "  'images': [base64.b64encode(raw).decode() for raw in images]}))\n"
        "answer = pathlib.Path(args[args.index('--output-last-message') + 1])\n"
        "answer.write_text('{\"ok\":true}')\n"
        "print(json.dumps({'type':'thread.started','thread_id':'x'}))\n"
        "print(json.dumps({'type':'turn.started'}))\n"
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}))\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return str(path), record


def _task_with(tmp_path: Path, made: list[tuple[dict, bytes]]) -> dict:
    local = []
    for index, (image, raw) in enumerate(made):
        file = tmp_path / f"local-{index}.png"
        file.write_bytes(raw)
        local.append({**image, "path": str(file)})
    return {**TASK, "images": [image for image, _ in made], "local_images": local}


def test_every_image_reaches_codex_in_order_and_is_named_in_the_prompt(tmp_path: Path) -> None:
    made = [S.make_image(label) for label in ("left", "right", "detail")]
    task = codex_answer.read_task(json.dumps(_task_with(tmp_path, made)).encode())
    codex, record = recording_codex(tmp_path)
    assert codex_answer.answer(task, codex=codex) == '{"ok":true}'
    seen = json.loads(record.read_text())
    args = seen["args"]
    positions = [index for index, arg in enumerate(args) if arg == "--image"]
    assert len(positions) == 3 and args.index("-") < positions[0], \
        "the prompt marker is before the image flags, which would take it for a file"
    assert [base64.b64decode(item) for item in seen["images"]] == [raw for _, raw in made]
    assert ("The 3 attached images are, in the order attached: 1 = crop crop-left; 2 = crop crop-right; "
            "3 = crop crop-detail.") in seen["prompt"]
    assert "do not answer from some of them" in seen["prompt"]


def test_a_single_portal_block_crop_keeps_its_sentence_and_one_image_flag(tmp_path: Path) -> None:
    image, raw = S.make_image("block", crop=False)
    task = codex_answer.read_task(json.dumps(_task_with(tmp_path, [(image, raw)])).encode())
    codex, record = recording_codex(tmp_path)
    codex_answer.answer(task, codex=codex)
    seen = json.loads(record.read_text())
    assert seen["args"].count("--image") == 1
    assert seen["prompt"].endswith("\n\nThe attached image is the crop for portal block " + image["portal_block_id"] + ".")


def test_a_single_opaque_crop_is_named_by_its_reference(tmp_path: Path) -> None:
    image, raw = S.make_image("only")
    task = codex_answer.read_task(json.dumps(_task_with(tmp_path, [(image, raw)])).encode())
    codex, record = recording_codex(tmp_path)
    codex_answer.answer(task, codex=codex)
    assert "1 = crop crop-only" in json.loads(record.read_text())["prompt"]


def _refused(tmp_path: Path, mutate) -> None:
    made = [S.make_image(label) for label in ("a", "b")]
    task = _task_with(tmp_path, made)
    mutate(task)
    with pytest.raises(codex_answer.TaskError, match="^image_input_invalid$"):
        codex_answer.read_task(json.dumps(task).encode())


def test_a_list_codex_cannot_be_trusted_with_is_refused_before_it_starts(tmp_path: Path) -> None:
    nine = [S.make_image(str(index)) for index in range(9)]
    with pytest.raises(codex_answer.TaskError, match="^image_input_invalid$"):
        codex_answer.read_task(json.dumps(_task_with(tmp_path, nine)).encode())
    eight = [S.make_image(str(index)) for index in range(8)]
    assert codex_answer.read_task(json.dumps(_task_with(tmp_path, eight)).encode())
    _refused(tmp_path, lambda t: t["images"][0].update(portal_block_id="blk_" + "a" * 32))  # two identities
    _refused(tmp_path, lambda t: t["images"][0].pop("crop_id"))                              # none
    _refused(tmp_path, lambda t: t["local_images"][1].update(crop_id="crop-other"))          # a copy of another
    _refused(tmp_path, lambda t: t["local_images"].pop())                                    # a copy missing
    _refused(tmp_path, lambda t: t["images"][0].update(crop_id="bad id"))
    _refused(tmp_path, lambda t: t["images"][1].update(crop_id="-lead"))


def _sized(tmp_path: Path, count: int, size: int) -> dict:
    """A task of ``count`` crops that each claim ``size`` bytes (read_task never opens the files)."""
    made = [S.make_image(f"s{index}") for index in range(count)]
    task = _task_with(tmp_path, made)
    for image, copied in zip(task["images"], task["local_images"]):
        image["size_bytes"] = copied["size_bytes"] = size
    return task


def test_the_images_of_one_task_may_not_exceed_32_mib_together(tmp_path: Path) -> None:
    assert codex_answer.read_task(json.dumps(_sized(tmp_path, 2, 12 << 20)).encode()), "24 MiB is inside"
    assert codex_answer.read_task(json.dumps(_sized(tmp_path, 4, 8 << 20)).encode()), "exactly 32 MiB is inside"
    for count, size in ((3, 12 << 20), (5, 8 << 20), (1, (16 << 20) + 1)):
        with pytest.raises(codex_answer.TaskError, match="^image_input_invalid$"):
            codex_answer.read_task(json.dumps(_sized(tmp_path, count, size)).encode())


def test_one_changed_file_among_several_stops_codex_from_starting(tmp_path: Path) -> None:
    made = [S.make_image(label) for label in ("a", "b", "c")]
    task = codex_answer.read_task(json.dumps(_task_with(tmp_path, made)).encode())
    (tmp_path / "local-1.png").write_bytes(made[1][1] + b"changed")
    codex, record = recording_codex(tmp_path)
    with pytest.raises(codex_answer.TaskError, match="^image_input_invalid$"):
        codex_answer.answer(task, codex=codex)
    assert not record.exists(), "no model was started with part of the images"
