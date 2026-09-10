"""Prove the local foundation services are genuinely usable.

P1-INF-01 / Gate A session A2. This is the implementation `make check-services`
forwards to::

    PYTHONPATH=src .venv/bin/python infra/local/check_services.py

SCOPE - what this proves
------------------------
1. PostgreSQL accepts an authenticated TCP connection as the configured role, against
   the configured database, and serves both a read and a write.
2. MinIO answers its own health endpoint.
3. The bucket named by the frozen ``S3_BUCKET`` exists.
4. Authenticated service access works: an object round-trips byte-for-byte.
5. Re-running bucket initialization is a benign no-op that destroys nothing.
6. The bucket is PRIVATE. Anonymous list, read and write are each attempted for real,
   against a key that demonstrably exists, and each must be denied.

SCOPE - what this deliberately does NOT prove
---------------------------------------------
It makes **no claim about the application migration head** - that is ``make check-db``
and belongs to the migration lane - and **no claim about the BlobStore port or its S3
adapter** - that is ``make check-storage`` and belongs to the storage lane. Nothing here
imports ``auditmanager``, reads ``alembic_version``, or inspects an application table.
A green ``check-services`` says the services are up, reachable and private. It says
nothing about the schema inside them or the code that will use them.

Every failure is explicit and non-zero. There is no partial pass: the success sentinel
is printed only after every check above has passed, and nothing is printed after it.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

import boto3
import psycopg
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

SENTINEL = "FOUNDATION-CHECK OK check-services"

# Only the frozen FF-01 section 3 names. This checker invents no configuration of its own.
REQUIRED_ENV = (
    "DATABASE_URL",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "S3_ENDPOINT_URL",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
)


class CheckFailed(Exception):
    """A foundation service is not in the state check-services requires."""

    def __init__(self, *lines: str) -> None:
        super().__init__("\n".join(lines))
        self.lines = lines


def report(label: str, detail: str) -> None:
    print(f"  ok  {label}: {detail}")


def load_env() -> dict[str, str]:
    """`make` exports the frozen names before invoking this. Absence is a hard failure."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise CheckFailed(
            "check-services: required frozen environment names are unset or empty.",
            *(f"  - {name}" for name in missing),
            "`make check-services` loads them from .env before running this checker.",
            "Running the checker directly without that environment is not supported.",
        )
    return {name: os.environ[name] for name in REQUIRED_ENV}


# --- PostgreSQL ---------------------------------------------------------------------


def check_postgres(env: dict[str, str]) -> None:
    """Authenticated connectivity plus a real read and a real write.

    The host comes from DATABASE_URL because that is where the published port is
    reachable; the credentials and database come from the POSTGRES_* service names.
    `make` has already proved the two sides agree before calling this.

    A temporary table is used on purpose: it exercises write access without creating a
    single persistent object, so this checker can never be mistaken for - or interfere
    with - the migration lane's schema.
    """
    host = urllib.parse.urlparse(env["DATABASE_URL"]).hostname
    if not host:
        raise CheckFailed("check-services: DATABASE_URL carries no host.")

    try:
        conn = psycopg.connect(
            host=host,
            port=int(env["POSTGRES_PORT"]),
            user=env["POSTGRES_USER"],
            password=env["POSTGRES_PASSWORD"],
            dbname=env["POSTGRES_DB"],
            connect_timeout=15,
        )
    except psycopg.Error as exc:
        raise CheckFailed(
            "check-services: PostgreSQL refused an authenticated connection.",
            f"  endpoint : {host}:{env['POSTGRES_PORT']}",
            f"  database : {env['POSTGRES_DB']}",
            f"  role     : {env['POSTGRES_USER']}",
            f"  error    : {exc}",
            "Run `make up` first, then `docker compose ... logs postgres` if it persists.",
        ) from exc

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
            if row != (1,):
                raise CheckFailed(
                    "check-services: PostgreSQL did not answer SELECT 1 with 1.",
                    f"  got: {row!r}",
                )

            cur.execute("SELECT current_database(), current_user, version()")
            database, role, version = cur.fetchone()
            if database != env["POSTGRES_DB"]:
                raise CheckFailed(
                    "check-services: connected to the wrong database.",
                    f"  expected : {env['POSTGRES_DB']}",
                    f"  connected: {database}",
                    "Another lane's instance may be bound to this port (FF-01 section 5).",
                )

            probe = f"foundation_check_{uuid.uuid4().hex}"
            cur.execute(f'CREATE TEMPORARY TABLE "{probe}" (value integer NOT NULL)')
            cur.execute(f'INSERT INTO "{probe}" (value) VALUES (42)')
            cur.execute(f'SELECT value FROM "{probe}"')
            if cur.fetchone() != (42,):
                raise CheckFailed(
                    "check-services: PostgreSQL accepted a write but did not read it back."
                )
            cur.execute(f'DROP TABLE "{probe}"')
        conn.rollback()
    conn.close()

    report("postgres reachable", f"{host}:{env['POSTGRES_PORT']} as {role}")
    report("postgres serving", f"database {database}, {version.split(' on ')[0]}")
    report("postgres read/write", "temporary table written and read back")


# --- MinIO health -------------------------------------------------------------------


def check_s3_health(env: dict[str, str]) -> None:
    url = env["S3_ENDPOINT_URL"].rstrip("/") + "/minio/health/live"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310 - local http
            status = response.status
    except (urllib.error.URLError, OSError) as exc:
        raise CheckFailed(
            "check-services: MinIO did not answer its health endpoint.",
            f"  url   : {url}",
            f"  error : {exc}",
            "Run `make up` first; `--wait` should already have gated on this.",
        ) from exc
    if status != 200:
        raise CheckFailed(
            "check-services: MinIO health endpoint returned an unhealthy status.",
            f"  url    : {url}",
            f"  status : {status}",
        )
    report("s3 healthy", f"{url} -> 200")


# --- S3 clients ---------------------------------------------------------------------


def _s3_config(**overrides: object) -> Config:
    # Path addressing: a virtual-host bucket name is not resolvable against 127.0.0.1.
    return Config(
        s3={"addressing_style": "path"},
        connect_timeout=15,
        read_timeout=30,
        retries={"max_attempts": 3, "mode": "standard"},
        **overrides,  # type: ignore[arg-type]
    )


def authenticated_client(env: dict[str, str]):
    return boto3.client(
        "s3",
        endpoint_url=env["S3_ENDPOINT_URL"],
        region_name=env["S3_REGION"],
        aws_access_key_id=env["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=env["S3_SECRET_ACCESS_KEY"],
        config=_s3_config(signature_version="s3v4"),
    )


def anonymous_client(env: dict[str, str]):
    """A client that signs nothing at all - no key is even loaded.

    UNSIGNED is the point: the denial has to be proved by a caller that genuinely has no
    credentials, not by reading a policy document back from the server and believing it.
    """
    return boto3.client(
        "s3",
        endpoint_url=env["S3_ENDPOINT_URL"],
        region_name=env["S3_REGION"],
        config=_s3_config(signature_version=UNSIGNED),
    )


def _error_of(exc: ClientError) -> tuple[int, str]:
    response = exc.response or {}
    status = int(response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
    code = str(response.get("Error", {}).get("Code", "<none>"))
    return status, code


# --- bucket -------------------------------------------------------------------------


def check_bucket_exists(client, env: dict[str, str]) -> None:
    bucket = env["S3_BUCKET"]
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        status, code = _error_of(exc)
        raise CheckFailed(
            "check-services: the frozen bucket is not present.",
            f"  bucket : {bucket}",
            f"  status : {status} ({code})",
            "`make up` runs infra/local/bucket-init.sh, which creates it. If the bucket",
            "is missing after a successful `make up`, inspect the s3-init service logs.",
        ) from exc
    except BotoCoreError as exc:
        raise CheckFailed(
            "check-services: could not reach the S3 endpoint with service credentials.",
            f"  endpoint : {env['S3_ENDPOINT_URL']}",
            f"  error    : {exc}",
        ) from exc
    report("bucket present", bucket)


def check_authenticated_access(client, env: dict[str, str], key: str, body: bytes) -> None:
    bucket = env["S3_BUCKET"]
    try:
        client.put_object(Bucket=bucket, Key=key, Body=body)
        fetched = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except (ClientError, BotoCoreError) as exc:
        raise CheckFailed(
            "check-services: authenticated service access to the bucket failed.",
            f"  bucket : {bucket}",
            f"  key    : {key}",
            f"  error  : {exc}",
            "S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY must authenticate against this MinIO.",
        ) from exc
    if fetched != body:
        raise CheckFailed(
            "check-services: the object did not round-trip byte-for-byte.",
            f"  wrote {len(body)} bytes, read back {len(fetched)}",
        )
    report("authenticated access", f"{len(body)}-byte object round-tripped as {key}")


def check_reinitialization_is_a_noop(client, env: dict[str, str], key: str, body: bytes) -> None:
    """A second initialization attempt must change nothing and must not be an error.

    `create_bucket` on a bucket the caller already owns is the API-level form of the
    second `bucket-init.sh` run. MinIO answers `BucketAlreadyOwnedByYou`; S3 in
    us-east-1 answers 200. Both are benign. What is NOT acceptable is any other error,
    or a bucket whose contents changed - so the object written just above is re-read
    afterwards and must still be byte-identical.
    """
    bucket = env["S3_BUCKET"]
    outcome = "created nothing (200)"
    try:
        client.create_bucket(Bucket=bucket)
    except ClientError as exc:
        status, code = _error_of(exc)
        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise CheckFailed(
                "check-services: re-initializing the bucket raised an unexpected error.",
                f"  bucket : {bucket}",
                f"  status : {status} ({code})",
                "Bucket initialization must be idempotent: a second run is a no-op.",
            ) from exc
        outcome = f"refused benignly ({code})"

    surviving = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    if surviving != body:
        raise CheckFailed(
            "check-services: re-initialization did not leave existing content intact.",
            f"  bucket : {bucket}",
            f"  key    : {key}",
            "Initialization must never destroy data.",
        )
    report("re-initialization no-op", f"{outcome}; existing object intact")


# --- privacy ------------------------------------------------------------------------


def _expect_denied(operation: str, call) -> str:
    """Run an anonymous operation that must fail, and return how it failed.

    A success here is the security failure this check exists to catch, so it raises.
    """
    try:
        call()
    except ClientError as exc:
        status, code = _error_of(exc)
        if status not in (401, 403):
            raise CheckFailed(
                f"check-services: anonymous {operation} failed, but not by being denied.",
                f"  status : {status} ({code})",
                "Denial must be an authorization refusal, not an incidental error.",
            ) from exc
        return f"HTTP {status} {code}"
    except BotoCoreError as exc:
        raise CheckFailed(
            f"check-services: anonymous {operation} could not be attempted.",
            f"  error : {exc}",
            "The privacy check is only evidence if the attempt actually reached MinIO.",
        ) from exc
    raise CheckFailed(
        f"check-services: THE BUCKET IS PUBLIC - anonymous {operation} SUCCEEDED.",
        "An unauthenticated caller must be denied list, read and write.",
        "infra/local/bucket-init.sh sets the anonymous policy to `none` on every `make up`;",
        "something has granted a bucket policy since. Do not use this instance until it is",
        "closed: `mc anonymous set none <alias>/<bucket>`.",
    )


def check_anonymous_denied(client, env: dict[str, str], existing_key: str) -> None:
    bucket = env["S3_BUCKET"]
    anon = anonymous_client(env)

    listed = _expect_denied(
        "list", lambda: anon.list_objects_v2(Bucket=bucket, MaxKeys=1)
    )
    report("anonymous list denied", listed)

    # Read is attempted against a key that provably exists, written moments ago by the
    # authenticated client. A 404 on a missing key would not be evidence of anything.
    read = _expect_denied(
        "read", lambda: anon.get_object(Bucket=bucket, Key=existing_key)["Body"].read()
    )
    report("anonymous read denied", f"{read} on an existing key")

    write_key = f"foundation-check/anonymous-write-probe-{uuid.uuid4().hex}"
    written = _expect_denied(
        "write",
        lambda: anon.put_object(Bucket=bucket, Key=write_key, Body=b"anonymous"),
    )

    # Denial is not enough on its own: prove the object was not created anyway.
    try:
        client.head_object(Bucket=bucket, Key=write_key)
    except ClientError as exc:
        status, _ = _error_of(exc)
        if status != 404:
            raise CheckFailed(
                "check-services: could not confirm the anonymous write left nothing.",
                f"  status : {status}",
            ) from exc
    else:
        raise CheckFailed(
            "check-services: the anonymous write was refused but the object exists.",
            f"  bucket : {bucket}",
            f"  key    : {write_key}",
        )
    report("anonymous write denied", f"{written}; no object created")


def check_anonymous_http_denied(env: dict[str, str], existing_key: str) -> None:
    """The same denial without boto3 in the way.

    A raw unauthenticated GET is what a browser or a scanner would send. Proving it here
    as well means the privacy result does not depend on how one SDK signs requests.
    """
    base = env["S3_ENDPOINT_URL"].rstrip("/")
    bucket = urllib.parse.quote(env["S3_BUCKET"])
    targets = {
        "bucket listing": f"{base}/{bucket}/",
        "object read": f"{base}/{bucket}/{urllib.parse.quote(existing_key)}",
    }
    for label, url in targets.items():
        try:
            with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310
                status = response.status
        except urllib.error.HTTPError as exc:
            if exc.code not in (401, 403):
                raise CheckFailed(
                    f"check-services: anonymous HTTP {label} failed with {exc.code},",
                    "which is not an authorization denial.",
                    f"  url : {url}",
                ) from exc
            report(f"anonymous HTTP {label} denied", f"GET -> {exc.code} {exc.reason}")
            continue
        except (urllib.error.URLError, OSError) as exc:
            raise CheckFailed(
                f"check-services: anonymous HTTP {label} could not be attempted.",
                f"  url   : {url}",
                f"  error : {exc}",
            ) from exc
        raise CheckFailed(
            f"check-services: THE BUCKET IS PUBLIC over plain HTTP - {label} returned"
            f" {status}.",
            f"  url : {url}",
        )


def cleanup(client, env: dict[str, str], key: str) -> None:
    """Leave the bucket exactly as it was found."""
    bucket = env["S3_BUCKET"]
    try:
        client.delete_object(Bucket=bucket, Key=key)
        client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        status, _ = _error_of(exc)
        if status != 404:
            raise CheckFailed(
                "check-services: could not remove the probe object.",
                f"  bucket : {bucket}",
                f"  key    : {key}",
                f"  status : {status}",
            ) from exc
    else:
        raise CheckFailed(
            "check-services: the probe object survived its own deletion.",
            f"  key : {key}",
        )
    report("probe removed", "bucket left as found")


def main() -> int:
    try:
        env = load_env()
        print(f"check-services: instance bucket {env['S3_BUCKET']} at {env['S3_ENDPOINT_URL']}")

        check_postgres(env)
        check_s3_health(env)

        client = authenticated_client(env)
        check_bucket_exists(client, env)

        key = f"foundation-check/probe-{uuid.uuid4().hex}"
        body = uuid.uuid4().bytes * 4
        check_authenticated_access(client, env, key, body)
        check_reinitialization_is_a_noop(client, env, key, body)
        check_anonymous_denied(client, env, key)
        check_anonymous_http_denied(env, key)
        cleanup(client, env, key)

        print(
            "check-services: scope - service health, bucket presence, privacy and "
            "authenticated access only."
        )
        print(
            "check-services: no claim is made about the migration head (make check-db) "
            "or the BlobStore adapter (make check-storage)."
        )
    except CheckFailed as exc:
        for line in exc.lines:
            print(line, file=sys.stderr)
        return 1

    # Nothing may be printed after this line: `make` refuses a result whose sentinel is
    # not the last output, because output after a success claim means work continued
    # past it.
    print(SENTINEL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
