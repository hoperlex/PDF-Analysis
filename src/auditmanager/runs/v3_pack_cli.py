"""Seal and verify the AR v3 beta reviewed-pack manifest from the host::

    PYTHONPATH=src .venv/bin/python -m auditmanager.runs.v3_pack_cli verify --manifest PATH
    PYTHONPATH=src .venv/bin/python -m auditmanager.runs.v3_pack_cli seal \\
        --scopes SCOPES.json --reviewer NAME --capacity expert --reviewed-at 2026-10-26 \\
        --decision-ref REF --scope-statement TEXT --out PATH [--database-url URL] [--force]

``verify`` is offline: it runs the loader the server runs at start (``v3_pack_manifest``) and
nothing else. ``seal`` reads a scopes file (the profile pair and six scope identities, without
set ids), asks the database in one read-only transaction which verified retrieval set each
identity selects, refuses if any identity has none, and writes the manifest atomically with
mode 0600. It never creates a set, never reviews anything, and records the reviewer's
attestation exactly as given: the person who ran the review passes it in, the CLI invents none.

Exit status
-----------
``0`` when the manifest verified or was sealed, ``2`` for any refusal or failure, with the
typed reason on stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager, suppress
from typing import IO, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.norms.public import (
    PromotionRefused,
    SetIdentity,
    VerifiedSetReference,
    select_verified_retrieval_set,
)
from auditmanager.runs.v3_group import SCOPES, ReviewedScope, TrustedPack
from auditmanager.runs.v3_pack_manifest import (
    PackManifestRefused,
    ParsedPackManifest,
    ReviewAttestation,
    load_manifest,
    read_regular_file,
    seal_manifest,
)
from auditmanager.shared.db.config import DATABASE_URL_VAR, DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

__all__ = ["build_parser", "main", "open_database_selector", "run_seal", "run_verify"]

#: ``select(identity, chunking_profile)`` returns the one verified set or raises ``PromotionRefused``.
SetSelector = Callable[[SetIdentity, str], VerifiedSetReference]
SelectorFactory = Callable[[str], AbstractContextManager[SetSelector]]

_SPEC_ROOT_KEYS = frozenset({"analysis_profile_id", "prompt_bundle_id", "scopes"})
_SPEC_SCOPE_KEYS = frozenset({
    "scope_id", "map_sha256", "snapshot_id", "reviewed_content_key", "embedding_build",
    "builder_version", "chunking_profile",
})
_SHA256 = re.compile(r"[0-9a-f]{64}")


@contextmanager
def open_database_selector(database_url: str) -> Iterator[SetSelector]:
    """One read-only transaction over the real database; closed whatever happens."""
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(database_url)))
    try:
        with Session(engine) as session, session.begin():
            session.execute(text("SET TRANSACTION READ ONLY"))

            def select(identity: SetIdentity, chunking_profile: str) -> VerifiedSetReference:
                return select_verified_retrieval_set(
                    session, identity=identity, chunking_profile=chunking_profile,
                )

            yield select
    finally:
        engine.dispose()


def _nonempty(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackManifestRefused("spec_value", f"{where} must be a non-empty string")
    return value


def _strings(raw: Any, keys: frozenset[str], where: str) -> dict[str, str]:
    if not isinstance(raw, dict) or set(raw) != keys:
        raise PackManifestRefused("spec_keys", f"{where} must have exactly {sorted(keys)}")
    return {name: _nonempty(raw[name], f"{where}.{name}") for name in keys}


def _read_spec(path: str) -> tuple[str, str, list[dict[str, str]]]:
    try:
        data = read_regular_file(path)
    except PackManifestRefused as exc:
        raise PackManifestRefused("scopes_file_unreadable", exc.reason) from None
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise PackManifestRefused("spec_not_json", "scopes file is not UTF-8 JSON") from None
    if not isinstance(document, dict) or set(document) != _SPEC_ROOT_KEYS:
        raise PackManifestRefused("spec_keys", f"scopes file must have exactly {sorted(_SPEC_ROOT_KEYS)}")
    profile_id = _nonempty(document["analysis_profile_id"], "analysis_profile_id")
    bundle_id = _nonempty(document["prompt_bundle_id"], "prompt_bundle_id")
    items = document["scopes"]
    if not isinstance(items, list) or len(items) != len(SCOPES):
        raise PackManifestRefused("spec_scopes", f"scopes must hold exactly {len(SCOPES)}")
    scopes = [_strings(item, _SPEC_SCOPE_KEYS, f"scopes[{index}]") for index, item in enumerate(items)]
    if tuple(scope["scope_id"] for scope in scopes) != SCOPES:
        raise PackManifestRefused("spec_scopes", f"scopes must be ordered {','.join(SCOPES)}")
    if any(_SHA256.fullmatch(scope["map_sha256"]) is None for scope in scopes):
        raise PackManifestRefused("spec_value", "every map_sha256 must be a lowercase SHA-256")
    if len({scope["map_sha256"] for scope in scopes}) != len(SCOPES):
        raise PackManifestRefused("spec_scopes", "the six map SHA-256 values must be distinct")
    return profile_id, bundle_id, scopes


def _select_scope(select: SetSelector, raw: dict[str, str]) -> ReviewedScope:
    identity = SetIdentity(
        map_sha256=raw["map_sha256"], snapshot_id=raw["snapshot_id"],
        reviewed_content_key=raw["reviewed_content_key"],
        embedding_build=raw["embedding_build"], builder_version=raw["builder_version"],
    )
    try:
        reference = select(identity, raw["chunking_profile"])
    except (PromotionRefused, ValueError):
        raise PackManifestRefused(
            "scope_unverified", f"{raw['scope_id']} selects no single verified retrieval set",
        ) from None
    if (reference.map_sha256 != identity.map_sha256
            or reference.snapshot_id != identity.snapshot_id):
        raise PackManifestRefused(
            "scope_unverified", f"{raw['scope_id']} was answered with a different identity",
        )
    return ReviewedScope(
        scope_id=raw["scope_id"], identity=identity, chunking_profile=raw["chunking_profile"],
        set_id=reference.set_id, set_sha256=reference.set_sha256,
    )


def _publish(data: bytes, out: str, *, force: bool) -> None:
    """Write beside the target, accept what is on disk, then publish by one atomic step.

    Without ``force`` the publish is ``link`` -- it fails if the target exists, with no window
    between a check and the write; with it, ``replace``.
    """
    directory, name = os.path.split(os.path.abspath(out))
    temporary = os.path.join(directory, f".{name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        load_manifest(temporary)
        if force:
            os.replace(temporary, out)
        else:
            try:
                os.link(temporary, out)
            except FileExistsError:
                raise PackManifestRefused(
                    "out_exists", "the target appeared meanwhile; nothing written",
                ) from None
            os.unlink(temporary)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def _summary(parsed: ParsedPackManifest) -> str:
    return (
        f"pack_sha256={parsed.pack.sha256} "
        f"scopes={','.join(scope.scope_id for scope in parsed.pack.scopes)} "
        f"maps={','.join(scope.identity.map_sha256[:12] for scope in parsed.pack.scopes)} "
        f"reviewer={json.dumps(parsed.review.reviewer, ensure_ascii=False)}"
    )


def run_verify(manifest: str, *, out: IO[str]) -> int:
    parsed = load_manifest(manifest)
    print(f"v3-pack OK {_summary(parsed)}", file=out, flush=True)
    return 0


def run_seal(
    *, scopes_path: str, review: ReviewAttestation, out_path: str, force: bool,
    database_url: str | None, open_selector: SelectorFactory, out: IO[str],
) -> int:
    profile_id, bundle_id, raw_scopes = _read_spec(scopes_path)
    if not force and os.path.lexists(out_path):
        raise PackManifestRefused("out_exists", "the target exists; pass --force to replace it")
    if not database_url or not database_url.strip():
        raise PackManifestRefused("database_url_missing", f"pass --database-url or set {DATABASE_URL_VAR}")
    with open_selector(database_url) as select:
        scopes = tuple(_select_scope(select, raw) for raw in raw_scopes)
    data = seal_manifest(TrustedPack(profile_id, bundle_id, scopes), review)
    try:
        _publish(data, out_path, force=force)
    except OSError as exc:
        raise PackManifestRefused("write_failed", type(exc).__name__) from None
    print(f"v3-pack SEALED {_summary(load_manifest(out_path))}", file=out, flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.runs.v3_pack_cli",
        description="Seal or verify the AR v3 beta reviewed-pack manifest the server installs.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="offline: run the server's loader on a manifest")
    verify.add_argument("--manifest", required=True, help="the sealed manifest file")
    seal = commands.add_parser("seal", help="seal a manifest from six verified retrieval sets")
    seal.add_argument("--scopes", required=True, help="scopes spec JSON, without set ids")
    seal.add_argument("--reviewer", required=True)
    seal.add_argument("--capacity", required=True, help="e.g. expert or owner-delegate")
    seal.add_argument("--reviewed-at", required=True, help="YYYY-MM-DD")
    seal.add_argument("--decision-ref", required=True, help="ruling or ticket recording the review")
    seal.add_argument("--scope-statement", required=True)
    seal.add_argument("--out", required=True, help="manifest file to write (mode 0600)")
    seal.add_argument("--database-url", default=None, help=f"default: ${DATABASE_URL_VAR}")
    seal.add_argument("--force", action="store_true", help="replace an existing --out")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    open_selector: SelectorFactory = open_database_selector,
    environ: Mapping[str, str] | None = None,
    out: IO[str] | None = None,
    err: IO[str] | None = None,
) -> int:
    stdout = sys.stdout if out is None else out
    stderr = sys.stderr if err is None else err
    env = os.environ if environ is None else environ
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    try:
        if arguments.command == "verify":
            return run_verify(arguments.manifest, out=stdout)
        return run_seal(
            scopes_path=arguments.scopes, out_path=arguments.out, force=arguments.force,
            review=ReviewAttestation(
                reviewer=arguments.reviewer, capacity=arguments.capacity,
                reviewed_at=arguments.reviewed_at, decision_ref=arguments.decision_ref,
                scope_statement=arguments.scope_statement,
            ),
            database_url=arguments.database_url or env.get(DATABASE_URL_VAR),
            open_selector=open_selector, out=stdout,
        )
    except PackManifestRefused as exc:
        print(f"v3-pack REFUSED {exc}", file=stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        # The class only: a database error can carry the connection target.
        print(f"v3-pack FAILED {type(exc).__name__}", file=stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
