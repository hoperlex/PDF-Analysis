"""Prove `D-44`'s guard can fail -- against the REAL numbers, without writing the tree.

    python tests/e2e/prove_the_headroom_guard_can_fail.py

`tests/e2e/pc01/journey/prove_the_guard_can_fail.py` mutates `manifest.json` in place and
restores it, which is fine: that file belongs to the journey. The files `D-44`'s guard reads
do not. `web/src/entities/document-version/model/upload-envelope.ts` is the application,
`src/auditmanager/api/routers/multipart.py` is the transport and
`infra/deploy/proxy/{nginx,tls-server}.conf` are the deployment, **and this session was told
to read them and never edit them** -- with another lane deploying from the same checkout
while this runs.

So this builds a throwaway tree instead: a temporary directory holding a copy of
`tests/e2e/test_upload_limit_headroom.py` at the same depth, the real files it reads with
ONE thing changed, and a copy of `tools/fixtures` (the guard generates its sparse oversize
stand-in with it). The guard resolves its repository root from its own `__file__`, so it reads
the copy and nothing else. Then `pytest` is run there and the exit status is the verdict.

That makes these real mutations of the real test, not assertions about what it would do,
and the repository is byte-identical before and after -- `git status` is the proof.

`W55B-INGEST-01` added the envelope's own bound (``MAX_BYTES`` in
``src/auditmanager/ingest/envelope.py``) as the fourth term -- ``pre-check <= MAX_BYTES <
UPLOAD_MAX_BODY`` -- so two mutations move it, and the tree the guard reads holds a copy of that
file as well.

`W55B-STREAM-01` moved the chain from two numbers to three (the pre-check, the application's
upload cap and nginx's cap in the two upload locations, with nginx's server-wide default
beside them), so the mutations below move each of them, and each of the two nginx files, in
both directions. The old first mutation -- the pre-check to 32 MiB with nginx untouched -- is
gone because it is no longer a violation: the application takes 251 MiB.
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
MULTIPART = Path("src/auditmanager/api/routers/multipart.py")
ENVELOPE_PY = Path("src/auditmanager/ingest/envelope.py")
NGINX = Path("infra/deploy/proxy/nginx.conf")
TLS = Path("infra/deploy/proxy/tls-server.conf")
FIXTURE_TOOLS = Path("tools/fixtures")
GENERATED = FIXTURE_TOOLS / "portal_bundle" / "generated.py"

REAL_PRECHECK = "maxBytes: 25 * 1024 * 1024"
REAL_API_UPLOAD = "UPLOAD_MAX_BODY: Final[int] = 251 * 1024 * 1024"
REAL_API_OTHER = "MAX_BODY: Final[int] = 26 * 1024 * 1024"
REAL_ENVELOPE = "MAX_BYTES: Final[int] = 250 * 1024 * 1024"
REAL_UPLOAD_CAP = "client_max_body_size 260m;"
REAL_DEFAULT_CAP = "client_max_body_size 32m;"
REAL_TRUNCATE = "handle.truncate(size)"

FILES = (ENVELOPE, MULTIPART, ENVELOPE_PY, NGINX, TLS, GENERATED)


def build(overrides: dict[Path, str]) -> Path:
    """A tree the guard will resolve as its repository root, holding only what it reads."""
    tree = Path(tempfile.mkdtemp(prefix="w55b-headroom-"))
    (tree / GUARD.parent).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / GUARD, tree / GUARD)
    shutil.copytree(
        ROOT / FIXTURE_TOOLS, tree / FIXTURE_TOOLS, ignore=shutil.ignore_patterns("__pycache__")
    )
    for relative in (ENVELOPE, MULTIPART, ENVELOPE_PY, NGINX, TLS):
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(overrides.get(relative, (ROOT / relative).read_text(encoding="utf-8")),
                          encoding="utf-8")
    if GENERATED in overrides:
        (tree / GENERATED).write_text(overrides[GENERATED], encoding="utf-8")
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


def first_only(text: str, old: str, new: str) -> str:
    """Change the first occurrence, so one of two upload locations moves and not the other."""
    assert old in text, f"{old!r} is no longer in the file this prover mutates"
    return text.replace(old, new, 1)


def last_only(text: str, old: str, new: str) -> str:
    """Change the first occurrence inside the /bff upload location, whatever follows it.

    It used to be the last occurrence in the file. `HARDEN-AUTH-EDGE-01` added two internal
    credential locations AFTER the upload ones, each with a cap of its own, so "last" would
    now mutate the wrong block and report a red for the wrong reason.
    """
    marker = "location ~ ^/bff/v1/projects/"
    head, found, tail = text.partition(marker)
    assert found and old in tail, f"{old!r} is no longer in the /bff upload location this prover mutates"
    return head + found + tail.replace(old, new, 1)


def credential_cap(text: str, location: str, new: str) -> str:
    """Change the cap of one internal credential location: the line after its `internal;`."""
    anchor = f"    location = /_edge/credential/{location} {{\n        internal;\n        {REAL_UPLOAD_CAP}\n"
    assert anchor in text, f"the {location} credential location no longer reads as this prover expects"
    return text.replace(anchor, anchor.replace(REAL_UPLOAD_CAP + "\n", new), 1)


def main() -> int:
    texts = {path: (ROOT / path).read_text(encoding="utf-8") for path in FILES}
    assert REAL_PRECHECK in texts[ENVELOPE], f"{ENVELOPE} no longer reads {REAL_PRECHECK!r}"
    assert REAL_API_UPLOAD in texts[MULTIPART], f"{MULTIPART} no longer reads {REAL_API_UPLOAD!r}"
    assert REAL_API_OTHER in texts[MULTIPART], f"{MULTIPART} no longer reads {REAL_API_OTHER!r}"
    assert REAL_ENVELOPE in texts[ENVELOPE_PY], f"{ENVELOPE_PY} no longer reads {REAL_ENVELOPE!r}"
    assert REAL_TRUNCATE in texts[GENERATED], f"{GENERATED} no longer reads {REAL_TRUNCATE!r}"
    for path in (NGINX, TLS):
        assert texts[path].count(REAL_UPLOAD_CAP) == 2, f"{path} no longer has two upload caps"
        assert REAL_DEFAULT_CAP in texts[path], f"{path} no longer reads {REAL_DEFAULT_CAP!r}"

    def mutated(path: Path, text: str) -> dict[Path, str]:
        return {path: text}

    mutations: list[tuple[str, dict[Path, str]]] = [
        (
            "raise the pre-check to the application's cap (251 MiB)",
            mutated(ENVELOPE, texts[ENVELOPE].replace(REAL_PRECHECK, "maxBytes: 251 * 1024 * 1024")),
        ),
        (
            "raise the pre-check past the application's cap",
            mutated(ENVELOPE, texts[ENVELOPE].replace(REAL_PRECHECK, "maxBytes: 300 * 1024 * 1024")),
        ),
        (
            "raise the application's upload cap to nginx's 260 MiB",
            mutated(MULTIPART, texts[MULTIPART].replace(REAL_API_UPLOAD, "UPLOAD_MAX_BODY: Final[int] = 260 * 1024 * 1024")),
        ),
        (
            "raise the application's upload cap past nginx's",
            mutated(MULTIPART, texts[MULTIPART].replace(REAL_API_UPLOAD, "UPLOAD_MAX_BODY: Final[int] = 512 * 1024 * 1024")),
        ),
        (
            "lower the application's upload cap under the pre-check",
            mutated(MULTIPART, texts[MULTIPART].replace(REAL_API_UPLOAD, "UPLOAD_MAX_BODY: Final[int] = 20 * 1024 * 1024")),
        ),
        (
            "raise every other route's cap above nginx's server default",
            mutated(MULTIPART, texts[MULTIPART].replace(REAL_API_OTHER, "MAX_BODY: Final[int] = 40 * 1024 * 1024")),
        ),
        (
            "raise the envelope's bound to the application's cap (251 MiB)",
            mutated(ENVELOPE_PY, texts[ENVELOPE_PY].replace(REAL_ENVELOPE, "MAX_BYTES: Final[int] = 251 * 1024 * 1024")),
        ),
        (
            "lower the envelope's bound under the pre-check (20 MiB)",
            mutated(ENVELOPE_PY, texts[ENVELOPE_PY].replace(REAL_ENVELOPE, "MAX_BYTES: Final[int] = 20 * 1024 * 1024")),
        ),
        (
            "move the envelope's bound behind a name the guard cannot read",
            mutated(ENVELOPE_PY, texts[ENVELOPE_PY].replace(REAL_ENVELOPE, "MAX_BYTES: Final[int] = ENVELOPE_MIB * 1024 * 1024")),
        ),
        (
            "lower nginx.conf's /api upload location to 200m",
            mutated(NGINX, first_only(texts[NGINX], REAL_UPLOAD_CAP, "client_max_body_size 200m;")),
        ),
        (
            "lower tls-server.conf's /api upload location to 251m (equal to the application)",
            mutated(TLS, first_only(texts[TLS], REAL_UPLOAD_CAP, "client_max_body_size 251m;")),
        ),
        (
            "lower only the /bff upload location of nginx.conf",
            mutated(NGINX, last_only(texts[NGINX], REAL_UPLOAD_CAP, "client_max_body_size 100m;")),
        ),
        (
            "delete the cap of nginx.conf's /bff upload location (it takes the 32m default)",
            mutated(NGINX, last_only(texts[NGINX], f"        {REAL_UPLOAD_CAP}\n", "")),
        ),
        (
            "lower nginx.conf's api credential location to the server default (32m)",
            mutated(NGINX, credential_cap(texts[NGINX], "api", "client_max_body_size 32m;\n")),
        ),
        (
            "delete tls-server.conf's web credential location cap (it takes the 32m default)",
            mutated(TLS, credential_cap(texts[TLS], "web", "")),
        ),
        (
            "raise nginx's server-wide default instead of the two locations",
            mutated(NGINX, texts[NGINX].replace(REAL_DEFAULT_CAP, "client_max_body_size 260m;")),
        ),
        (
            "comment out tls-server.conf's server-wide default",
            mutated(TLS, texts[TLS].replace(REAL_DEFAULT_CAP, f"# {REAL_DEFAULT_CAP}")),
        ),
        (
            "a stray cap in another location of tls-server.conf",
            mutated(
                TLS,
                texts[TLS].replace(
                    "    location / {\n        proxy_pass http://web:3000;",
                    "    location / {\n        client_max_body_size 1m;\n        proxy_pass http://web:3000;",
                ),
            ),
        ),
        (
            "move the pre-check limit behind a name the guard cannot read",
            mutated(ENVELOPE, texts[ENVELOPE].replace(REAL_PRECHECK, "maxBytes: MAX_UPLOAD_BYTES")),
        ),
        (
            "move the application's cap behind a name the guard cannot read",
            mutated(MULTIPART, texts[MULTIPART].replace(REAL_API_UPLOAD, "UPLOAD_MAX_BODY: Final[int] = UPLOAD_MIB * 1024 * 1024")),
        ),
        (
            "leave the label at 25 MiB while the limit moves to 30",
            mutated(ENVELOPE, texts[ENVELOPE].replace(REAL_PRECHECK, "maxBytes: 30 * 1024 * 1024")),
        ),
        (
            "the stand-in generator returns a file shorter than it was asked for",
            mutated(GENERATED, texts[GENERATED].replace(REAL_TRUNCATE, "handle.truncate(size // 2)")),
        ),
    ]

    ok = True
    for label, overrides in mutations:
        tree = build(overrides)
        try:
            code, summary = run(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        if code == 0:
            ok = False
            print(f"{'GREEN -- THE CHECK IS VACUOUS':34} {label}  [{summary}]")
        else:
            print(f"{'RED (control works)':34} {label}  [{summary}]")

    tree = build({})
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
