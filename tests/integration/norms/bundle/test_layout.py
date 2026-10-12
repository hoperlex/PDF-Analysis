"""`W54-BUNDLE-01`: the bundle's name, ``SHA256SUMS`` and tree rule, as both ends apply them.

Container-free. The Python patterns are compared with ``lib/forced-command.sh``'s EREs by
running both over the same strings, and a bundle this module accepts is also accepted by
the shell's ``fc_check_bundle_tree`` (and a damaged one refused by both).
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest

from auditmanager.norms.bundle.errors import BundleRefused
from auditmanager.norms.bundle.layout import (
    CONTENT_KEY_PATTERN,
    PATH_PATTERN,
    bundle_name,
    object_path,
    parse_sums,
    render_sums,
    split_bundle_name,
    verify_bundle,
)
from tests.integration.norms.bundle.support import bash_lib

KEYS = [
    "2026-07-23..2026-08-20+17d.4b74348debf7",
    "2026-07-23..2026-08-20+17d+121r.4b74348debf7",
    "2026-07-23..2026-08-20+17d+121r+3u.4b74348debf7",
    "2026-07-23..2026-08-20+17d+0r+121u.4b74348debf7",
    "undated+0d.0123456789ab",
    "undated+2d.0123456789ab+seg-markdown-v2",
    "2026-07-23..2026-08-20+17d+0r.4b74348debf7",
    "2026-07-23..2026-08-20+017d.4b74348debf7",
    "2026-07-23..2026-08-20+17d.4B74348DEBF7",
    "2026-07-23..2026-08-20+17d.4b74348debf",
    "2026-07-23+17d.4b74348debf7",
    "undated+1d.0123456789ab+seg-",
    "undated+1d.0123456789ab+seg-Markdown",
    "undated+1d+1u.0123456789ab",
]
PATHS = [
    "manifest.json", "rows/documents.jsonl", "objects/ab/" + "ab" * 32 + ".pdf", "build/chunks-00000.jsonl",
    ".hidden", "a/../b", "a//b", "кириллица.pdf", "a b", "/abs", "a/" * 8 + "x", "a/" * 7 + "x", "x" * 129,
]


def _shell_matches(ere_variable: str, values: list[str]) -> list[bool]:
    ran = bash_lib(
        f'for value in "$@"; do if [[ $value =~ ^(${{{ere_variable}}})$ ]]; then echo 1; else echo 0; fi; done',
        *values,
    )
    assert ran.returncode == 0, ran.stderr
    return [line == "1" for line in ran.stdout.splitlines()]


def test_the_content_key_pattern_is_the_inbound_keys_grammar() -> None:
    python = [bool(CONTENT_KEY_PATTERN.fullmatch(key)) for key in KEYS]
    assert python == _shell_matches("FC_CONTENT_KEY_ERE", KEYS)
    assert python.count(True) == 6, python


def test_the_bundle_path_pattern_is_the_inbound_keys_grammar() -> None:
    python = [bool(PATH_PATTERN.fullmatch(path)) for path in PATHS]
    assert python == _shell_matches("FC_BUNDLE_PATH_ERE", PATHS)
    assert python[:4] == [True] * 4 and python[4:7] == [False] * 3


def test_the_bundle_name_is_the_key_and_the_sums_digest() -> None:
    sums = render_sums({"manifest.json": "0" * 64})
    name = bundle_name(KEYS[2], sums)
    assert name == f"{KEYS[2]}+{hashlib.sha256(sums).hexdigest()}"
    assert split_bundle_name(name) == (KEYS[2], hashlib.sha256(sums).hexdigest())
    assert _shell_matches("FC_BUNDLE_KEY_ERE", [name, name[:-1]]) == [True, False]
    with pytest.raises(BundleRefused, match="content_key_grammar"):
        bundle_name(KEYS[6], sums)


def test_sums_render_in_byte_order_and_parse_back_strictly() -> None:
    entries = {"rows/b.jsonl": "1" * 64, "manifest.json": "2" * 64, "objects/aa/x.pdf": "3" * 64}
    data = render_sums(entries)
    assert data.decode().splitlines() == [
        f"{'2' * 64}  manifest.json", f"{'3' * 64}  objects/aa/x.pdf", f"{'1' * 64}  rows/b.jsonl",
    ]
    assert parse_sums(data) == entries
    for broken in (
        b"",
        data[:-1],
        data + data.splitlines(keepends=True)[0],
        f"{'1' * 64}  SHA256SUMS\n".encode(),
        f"{'1' * 64} *rows/a\n".encode(),
        f"{'1' * 63}  rows/a\n".encode(),
        f"{'1' * 64}  ../a\n".encode(),
    ):
        with pytest.raises(BundleRefused, match="sums_malformed"):
            parse_sums(broken)


def _bundle(where: Path, files: dict[str, bytes], *, key: str = KEYS[0]) -> Path:
    sums = render_sums({name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
    directory = where / bundle_name(key, sums)
    for name, data in files.items():
        (directory / name).parent.mkdir(parents=True, exist_ok=True)
        (directory / name).write_bytes(data)
    (directory / "SHA256SUMS").write_bytes(sums)
    return directory


FILES = {
    "manifest.json": b"{}\n",
    "rows/documents.jsonl": b"{}\n",
    object_path(hashlib.sha256(b"pdf one").hexdigest()): b"pdf one",
    object_path(hashlib.sha256(b"pdf two").hexdigest()): b"pdf two",
}


def _shell_accepts(directory: Path) -> bool:
    ran = bash_lib('fc_check_bundle_tree "$1" "$2" >/dev/null 2>&1 && echo ok || echo refused',
                   str(directory), directory.name)
    return ran.stdout.strip() == "ok"


def test_a_well_formed_bundle_is_verified_here_and_by_the_shell(tmp_path: Path) -> None:
    directory = _bundle(tmp_path, FILES)
    verified = verify_bundle(directory)
    assert verified.content_key == KEYS[0] and not verified.objects_discarded
    assert set(verified.sizes) == set(FILES)
    assert _shell_accepts(directory)


@pytest.mark.parametrize(
    "damage, reason",
    [
        ("tamper", "bundle_bytes"),
        ("extra", "bundle_tree"),
        ("missing", "bundle_tree"),
        ("symlink", "bundle_tree"),
        ("rename", "sums_digest"),
        ("one-object-gone", "bundle_tree"),
    ],
)
def test_a_damaged_bundle_is_refused_here_and_by_the_shell(tmp_path: Path, damage: str, reason: str) -> None:
    directory = _bundle(tmp_path, FILES)
    objects = sorted(path for path in FILES if path.startswith("objects/"))
    if damage == "tamper":
        (directory / "rows/documents.jsonl").write_bytes(b"[]\n")
    elif damage == "extra":
        (directory / "rows/extra.jsonl").write_bytes(b"x")
    elif damage == "missing":
        (directory / "rows/documents.jsonl").unlink()
    elif damage == "symlink":
        os.symlink("/etc/hostname", directory / "rows/link")
    elif damage == "rename":
        directory = directory.rename(directory.with_name(f"{KEYS[0]}+{'0' * 64}"))
    elif damage == "one-object-gone":
        (directory / objects[0]).unlink()
    with pytest.raises(BundleRefused, match=reason):
        verify_bundle(directory, allow_discarded_objects=True)
    assert not _shell_accepts(directory)


def test_objects_discarded_as_a_whole_are_accepted_only_when_allowed(tmp_path: Path) -> None:
    directory = _bundle(tmp_path, FILES)
    shutil.rmtree(directory / "objects")
    with pytest.raises(BundleRefused, match="bundle_tree"):
        verify_bundle(directory)
    verified = verify_bundle(directory, allow_discarded_objects=True)
    assert verified.objects_discarded
    assert set(verified.sizes) == {"manifest.json", "rows/documents.jsonl"}
    assert len(verified.object_paths) == 2


def test_only_re_hashes_the_named_files_but_keeps_the_tree_rule(tmp_path: Path) -> None:
    directory = _bundle(tmp_path, FILES)
    (directory / "rows/documents.jsonl").write_bytes(b"[]\n")
    assert set(verify_bundle(directory, only=["manifest.json"]).sizes) == {"manifest.json"}
    (directory / "rows/stray").write_bytes(b"x")
    with pytest.raises(BundleRefused, match="bundle_tree"):
        verify_bundle(directory, only=["manifest.json"])


def test_a_discard_is_objects_absent_as_a_whole_and_nothing_else(tmp_path: Path) -> None:
    emptied = _bundle(tmp_path / "emptied", FILES)
    for path in (emptied / "objects").rglob("*.pdf"):
        path.unlink()
    with pytest.raises(BundleRefused, match="bundle_tree"):
        verify_bundle(emptied, allow_discarded_objects=True)
    more = _bundle(tmp_path / "more", FILES)
    shutil.rmtree(more / "objects")
    (more / "rows/documents.jsonl").unlink()
    with pytest.raises(BundleRefused, match="bundle_tree"):
        verify_bundle(more, allow_discarded_objects=True)
