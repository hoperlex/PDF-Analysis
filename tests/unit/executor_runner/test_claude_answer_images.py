"""Actual ordered PNG content reaches a fake CLI's stream-json stdin; no model/network."""
from __future__ import annotations

import base64
import json
import struct
import sys
import zlib
from pathlib import Path

import pytest

from tests.unit.executor_runner.test_claude_answer import claude_answer, TASK


def chunk(kind: bytes, value: bytes) -> bytes:
    return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value) & 0xffffffff)


def png(colour=0) -> bytes:
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes((0, colour)))) + chunk(b"IEND", b""))


def image(raw: bytes) -> dict:
    return {"media_type": "image/png", "data": base64.b64encode(raw).decode("ascii")}


def cli(tmp_path: Path, expected: list[bytes]) -> str:
    path = tmp_path / "claude-images"
    path.write_text(
        f"#!{sys.executable}\n"
        "import base64,json,sys\n"
        "args=sys.argv[1:]\n"
        "assert args[args.index('--tools')+1] == ''\n"
        "assert args[args.index('--model')+1] == 'claude-opus-5'\n"
        "assert '--strict-mcp-config' in args and '--no-session-persistence' in args\n"
        "raw=sys.stdin.buffer.read()\n"
        f"expected={expected!r}\n"
        "if expected:\n"
        " assert args[args.index('--input-format')+1]=='stream-json'\n"
        " assert raw.endswith(b'\\n') and raw.count(b'\\n') == 1\n"
        " envelope=json.loads(raw)\n"
        " assert envelope['type']=='user' and envelope['parent_tool_use_id'] is None\n"
        " assert envelope['message']['role']=='user'\n"
        " content=envelope['message']['content']\n"
        " assert len(content)==len(expected)+1 and content[-1]['type']=='text'\n"
        " for block,data in zip(content[:-1],expected):\n"
        "  assert block['type']=='image' and block['source']['type']=='base64'\n"
        "  assert block['source']['media_type']=='image/png'\n"
        "  assert base64.b64decode(block['source']['data'],validate=True)==data\n"
        " text=content[-1]['text']\n"
        "else:\n"
        " assert '--input-format' not in args\n"
        f" assert raw=={json.dumps({'system': TASK['system'], 'user_text': TASK['user_text']}, ensure_ascii=False).encode()!r}\n"
        " text=raw.decode()\n"
        f"assert json.loads(text)=={ {'system': TASK['system'], 'user_text': TASK['user_text']}!r}\n"
        "assert 'A page of data.' not in ' '.join(args)\n"
        "print(json.dumps({'type':'result','subtype':'success','is_error':False,\n"
        " 'permission_denials':[],'structured_output':{'ok':True},\n"
        " 'modelUsage':{'claude-opus-5':{'inputTokens':2,'outputTokens':3}}}),flush=True)\n"
    )
    path.chmod(0o700)
    return str(path)


@pytest.mark.parametrize("count", [0, 1, 2, 8])
def test_cli_receives_actual_ordered_png_content_and_text_stays_unchanged(tmp_path, count):
    raws = [png(index) for index in range(count)]
    task = dict(TASK)
    if count:
        task["image"] = image(raws[0]) if count == 1 else list(map(image, raws))
    accepted = claude_answer.read_task(json.dumps(task).encode(), ssh=True)
    reply = json.loads(claude_answer.ssh_reply(accepted, claude=cli(tmp_path, raws)))
    assert reply["output_text"] == '{"ok":true}'


@pytest.mark.parametrize("bad,reason", [
    (None, "invalid_image_envelope"), ([], "invalid_image_envelope"),
    ([image(png())] * 9, "invalid_image_envelope"),
    ({"media_type": "image/jpeg", "data": "AA=="}, "invalid_image_envelope"),
    ({"media_type": "image/png", "data": "!notbase64!"}, "invalid_image_base64"),
    ({"media_type": "image/png", "data": "é"}, "invalid_image_base64"),
    (image(b"\x89PNG\r\n\x1a\n"), "invalid_png"),
    (image(png()[:-1]), "invalid_png"),
    (image(png() + b"trailing"), "invalid_png"),
    (image(png()[:33] + chunk(b"IDAT", b"broken") + chunk(b"IEND", b"")), "invalid_png"),
    (dict(image(png()), path="/tmp/image.png"), "invalid_image_envelope"),
])
def test_invalid_images_refuse_before_any_cli_start(bad, reason):
    with pytest.raises(claude_answer.TaskError, match=f"^{reason}$"):
        claude_answer.read_task(json.dumps(dict(TASK, image=bad)).encode(), ssh=True)


def test_crc_dimensions_decompression_and_all_image_budgets(monkeypatch):
    corrupt = bytearray(png()); corrupt[30] ^= 1
    bad_scanline = png()[:33] + chunk(b"IDAT", zlib.compress(b"\x05\x00")) + chunk(b"IEND", b"")
    bomb = png()[:33] + chunk(b"IDAT", zlib.compress(b"\0" * 10_000)) + chunk(b"IEND", b"")
    oversized = (png()[:8] + chunk(b"IHDR", struct.pack(">IIBBBBB", 1_000_000, 1_000_000, 8, 0, 0, 0, 0))
                 + png()[33:])
    for value, reason in ((corrupt, "invalid_png"), (bad_scanline, "invalid_png"), (bomb, "invalid_png"),
                          (oversized, "image_dimensions_too_large")):
        with pytest.raises(claude_answer.TaskError, match=f"^{reason}$"):
            claude_answer.read_task(json.dumps(dict(TASK, image=image(value))).encode(), ssh=True)
    monkeypatch.setattr(claude_answer, "MAX_TOTAL_IMAGE_BYTES", len(png()) * 2 - 1)
    with pytest.raises(claude_answer.TaskError, match="^images_too_large$"):
        claude_answer.read_task(json.dumps(dict(TASK, image=[image(png()), image(png())])).encode(), ssh=True)
    monkeypatch.setattr(claude_answer, "MAX_IMAGE_BYTES", len(png()) - 1)
    with pytest.raises(claude_answer.TaskError, match="^image_too_large$"):
        claude_answer.read_task(json.dumps(dict(TASK, image=image(png()))).encode(), ssh=True)


def test_valid_adam7_and_palette_pngs_are_accepted():
    adam = (png()[:8] + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 1))
            + png()[33:])
    palette = (png()[:8] + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 1, 3, 0, 0, 0))
               + chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff") + png()[33:])
    for value in (adam, palette):
        assert claude_answer.read_task(json.dumps(dict(TASK, image=image(value))).encode(), ssh=True)
    for invalid in (png()[:33] + chunk(b"PLTE", b"\0" * 3) + png()[33:],
                    palette[:33] + chunk(b"PLTE", b"\0" * 9) + png()[33:]):
        with pytest.raises(claude_answer.TaskError, match="^invalid_png$"):
            claude_answer.read_task(json.dumps(dict(TASK, image=image(invalid))).encode(), ssh=True)


def test_pull_image_refusal_remains_and_ssh_task_caps_match_stand(monkeypatch):
    with pytest.raises(claude_answer.TaskError, match="^image_input_unsupported$"):
        claude_answer.read_task(json.dumps(dict(TASK, image=image(png()))).encode())
    assert claude_answer.MAX_SSH_SINGLE_TASK_BYTES == 24 << 20
    assert claude_answer.MAX_SSH_TASK_BYTES == 48 << 20
    monkeypatch.setattr(claude_answer, "MAX_SSH_SINGLE_TASK_BYTES", 1)
    with pytest.raises(claude_answer.TaskError, match="^task_too_large$"):
        claude_answer.read_task(json.dumps(dict(TASK, image=image(png()))).encode(), ssh=True)
    assert claude_answer.read_task(json.dumps(dict(TASK, image=[image(png()), image(png())])).encode(), ssh=True)
