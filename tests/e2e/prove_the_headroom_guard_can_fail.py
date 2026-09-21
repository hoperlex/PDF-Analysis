"""Prove `D-44`'s guard can fail -- against the REAL numbers, without writing the tree.

    python tests/e2e/prove_the_headroom_guard_can_fail.py

`tests/e2e/pc01/journey/prove_the_guard_can_fail.py` mutates `manifest.json` in place and
restores it, which is fine: that file belongs to the journey. The two files `D-44`'s guard
reads do not. `web/src/entities/document-version/model/upload-envelope.ts` is the
application and `infra/deploy/proxy/nginx.conf` is the deployment, **and this session was
told to read the second and never edit it** -- with another lane deploying from the same
checkout while this runs.

So this builds a throwaway tree instead: a temporary directory holding a copy of
`tests/e2e/test_upload_limit_headroom.py` at the same depth, the two real files it reads
with ONE number changed, and a sparse stand-in for `oversize.pdf` of the true size. The
guard resolves its repository root from its own `__file__`, so it reads the copy and
nothing else. Then `pytest` is run there and the exit status is the verdict.

That makes these real mutations of the real test, not assertions about what it would do,
and the repository is byte-identical before and after -- `git status` is the proof.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"
GUARD = Path("tests/e2e/test_upload_limit_headroom.py")
ENVELOPE = Path("web/src/entities/document-version/model/upload-envelope.ts")
NGINX = Path("infra/deploy/proxy/nginx.conf")
OVERSIZE = Path("fixtures/synthetic/ar/negative/oversize.pdf")

REAL_PRECHECK = "maxBytes: 25 * 1024 * 1024"
REAL_NGINX = "client_max_body_size 32m;"


def build(envelope: str, nginx: str, oversize_bytes: int) -> Path:
    """A tree the guard will resolve as its repository root, holding only what it reads."""
    tree = Path(tempfile.mkdtemp(prefix="w28-headroom-"))
    (tree / GUARD.parent).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / GUARD, tree / GUARD)
    for relative, text in ((ENVELOPE, envelope), (NGINX, nginx)):
        (tree / relative).parent.mkdir(parents=True, exist_ok=True)
        (tree / relative).write_text(text, encoding="utf-8")
    (tree / OVERSIZE).parent.mkdir(parents=True, exist_ok=True)
    with (tree / OVERSIZE).open("wb") as handle:  # sparse: no bytes are actually written
        handle.truncate(oversize_bytes)
    return tree


def run(tree: Path) -> tuple[int, str]:
    result = subprocess.run(
        [str(PYTHON), "-m", "pytest", str(GUARD), "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(tree),
        capture_output=True,
        text=True,
    )
    tail = (result.stdout or "").strip().splitlines()
    return result.returncode, (tail[-1] if tail else "(no output)")


def main() -> int:
    envelope = (ROOT / ENVELOPE).read_text(encoding="utf-8")
    nginx = (ROOT / NGINX).read_text(encoding="utf-8")
    size = (ROOT / OVERSIZE).stat().st_size
    assert REAL_PRECHECK in envelope, f"{ENVELOPE} no longer reads {REAL_PRECHECK!r}"
    assert REAL_NGINX in nginx, f"{NGINX} no longer reads {REAL_NGINX!r}"

    mutations = [
        (
            "raise the pre-check to 32 MiB, nginx untouched  <- D-44's own sentence",
            envelope.replace(REAL_PRECHECK, "maxBytes: 32 * 1024 * 1024"),
            nginx,
            size,
        ),
        (
            "raise the pre-check to 64 MiB",
            envelope.replace(REAL_PRECHECK, "maxBytes: 64 * 1024 * 1024"),
            nginx,
            size,
        ),
        (
            "lower nginx to 16m and leave the pre-check alone",
            envelope,
            nginx.replace(REAL_NGINX, "client_max_body_size 16m;"),
            size,
        ),
        (
            "make nginx exactly equal to the pre-check",
            envelope,
            nginx.replace(REAL_NGINX, "client_max_body_size 26214400;"),
            size,
        ),
        (
            "comment out client_max_body_size entirely",
            envelope,
            nginx.replace(REAL_NGINX, f"# {REAL_NGINX}"),
            size,
        ),
        (
            "move the pre-check limit behind a name the guard cannot read",
            envelope.replace(REAL_PRECHECK, "maxBytes: MAX_UPLOAD_BYTES"),
            nginx,
            size,
        ),
        (
            "leave the label at 25 MiB while the limit moves to 30",
            envelope.replace(REAL_PRECHECK, "maxBytes: 30 * 1024 * 1024"),
            nginx,
            size,
        ),
        (
            "shrink oversize.pdf under the pre-check limit",
            envelope,
            nginx,
            1024,
        ),
    ]

    ok = True
    for label, envelope_text, nginx_text, oversize_bytes in mutations:
        tree = build(envelope_text, nginx_text, oversize_bytes)
        try:
            code, summary = run(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        if code == 0:
            ok = False
            print(f"{'GREEN -- THE CHECK IS VACUOUS':34} {label}  [{summary}]")
        else:
            print(f"{'RED (control works)':34} {label}  [{summary}]")

    tree = build(envelope, nginx, size)
    try:
        code, summary = run(tree)
    finally:
        shutil.rmtree(tree, ignore_errors=True)
    print(f"\nthe tree's own numbers, unmutated: {summary}")
    if code != 0:
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
