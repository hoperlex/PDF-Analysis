# P1-INT-00 owns this file: it is the complete root command surface for the P01
# PostgreSQL/S3 foundation. FF-01 freezes these nine literal targets:
#
#   bootstrap up down check-services migrate check-db check-storage
#   test-foundation foundation
#
# Provider lanes (P1-INF-01, P1-DB-01, P1-STO-01, P1-QA-00) fill only their reserved
# paths and invoke these targets. They must not edit this file, add a target or create
# a private command alias (FF-01 sections 3 and 6). A target whose implementation has
# not arrived yet is a stable forwarder: it fails explicitly and names the owning task.
# No target in this file has a substitute implementation or a fallback path.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.NOTPARALLEL:
.DEFAULT_GOAL := bootstrap
.SUFFIXES:

# --- toolchain pins (machine-readable copy: docs/program/FOUNDATION_LOCK.json) ------
# Host interpreter, used only to build the two virtual environments. It must be a base
# interpreter, never an active virtualenv, and its version must equal .python-version
# exactly. Override where python3.12 is not on PATH:
#   make bootstrap FOUNDATION_PYTHON=/opt/python/3.12.3/bin/python3.12
FOUNDATION_PYTHON ?= python3.12

UV_VERSION := 0.12.11
# sha256 of every uv 0.12.11 WHEEL Astral publishes (18 platforms). pip accepts any
# match and rejects an artifact whose hash is absent, so an unpinned uv can never be
# installed. The sdist hash is deliberately NOT listed: building uv from source needs a
# Rust toolchain that is not a documented host prerequisite, so a platform without a
# published wheel fails immediately and loudly instead of starting a surprise build.
UV_HASHES := \
  --hash=sha256:038c5080948e4e16285448b806bebaea8d22d1bed9c2239188e3ee334ac0e45d \
  --hash=sha256:103900d5310e0d6979568b695c4782fb4cb0721db7bec70ddce70596acbf85fd \
  --hash=sha256:4d3337366d55b0fa44f559dad77039ba78699f3d964e597aedd7afa79da0630d \
  --hash=sha256:c6ff21a984039f3e5c78a432c9c5ecf28dd6282db6d46336d077188e0eed53e3 \
  --hash=sha256:187229b5723bb773a057610ad37392b7325e9342d4f7a7585cda5c492501be86 \
  --hash=sha256:93320d225a48b8a98e6ab4ad56c00626e9bd26ff7f7f773fe4cf3058876e46bb \
  --hash=sha256:54b62b4ea2274d2a95992d9ee2d39c13794c8098cfdcd835743bc827f9a6d9a5 \
  --hash=sha256:c0f399a8ec2146dc47df217f5fe86f1068bf62387a7430921de71c441efc5d9e \
  --hash=sha256:799923e6f12bf02079fb2ce3fd65201be78d6ec618ffc080f24655491d875fe9 \
  --hash=sha256:2c0d529c347eccaebaeec1be0e2a7a0a7d814128595b2549649060d2f75d0df6 \
  --hash=sha256:8aa7ce99b5e853c12c62c3e0a1e286a447bed81f0a7c28b3882354a17bf056bb \
  --hash=sha256:7d480eb64697dbe8c1a32fdce69824a2eca42c3a66b6066912948d82fed54c2d \
  --hash=sha256:fc44bf138117b241e1a38dbddc9c28822ecb95a0f3c94d77cee896965d2f6345 \
  --hash=sha256:2726ca41c365b40e511ac9ac2496d3d30da76f88ce6a3877fd8f9bdd038907a4 \
  --hash=sha256:b19f9ffa46d9726e495fc636d19bad99f497d438bc07be858aef0dc37a150abe \
  --hash=sha256:427c29a2a4bf28ed7bf529296e4224f8252b8ca52175241ba4c6f29b7b3a035e \
  --hash=sha256:498820071e52b52e7548004459f08180a78c1946c273b9ac6a892ab9f2c4d7d1 \
  --hash=sha256:7651a6288761b202feddd40545aab4b2cfe7af7a07992f85e7d07616cc95ae83

# Container images are pinned by exact tag AND multi-arch index digest. No floating
# tag and no `latest` reference exists in the foundation (FF-01 section 2 item 9).
# They are exported so the P1-INF-01 compose file consumes these pins instead of
# declaring a second, competing source of truth for image identity.
export FOUNDATION_POSTGRES_IMAGE := postgres:17.11-trixie@sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675
export FOUNDATION_S3_IMAGE := minio/minio:RELEASE.2025-09-07T16-13-09Z@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e
export FOUNDATION_S3_MC_IMAGE := minio/mc:RELEASE.2025-08-13T08-35-41Z@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727

# --- owned environment layout ------------------------------------------------------
# Every environment below is git-ignored and is reproduced only from a committed lock.
VENV_RUNTIME := .venv
VENV_BOOTSTRAP := .venv/bootstrap
UV_HOME := .local/uv
RUNTIME_PY := $(VENV_RUNTIME)/bin/python
BOOTSTRAP_PY := $(VENV_BOOTSTRAP)/bin/python
UV := $(UV_HOME)/bin/uv
VALIDATION_LOCK := requirements/validation.lock
RUNTIME_LOCK := uv.lock

# --- reserved provider paths (FF-01 section 3) --------------------------------------
# P1-INT-00 reserves these paths and writes none of them.
INF_COMPOSE := infra/local/docker-compose.yml
INF_CHECK := infra/local/check_services.py
DB_ALEMBIC_INI := db/migrations/alembic.ini
DB_CHECK := src/auditmanager/shared/db/check.py
STO_CHECK := src/auditmanager/storage/check.py
QA_SUITE := tests/integration/foundation

.PHONY: bootstrap up down check-services migrate check-db check-storage test-foundation foundation

# --- shared guards -----------------------------------------------------------------
# Expanded verbatim into each recipe that needs them. No guard has a success path that
# substitutes a missing implementation or invents an unset value.
define GUARDS
fail() { printf '%s\n' "$$@" >&2; exit 1; }

require_runtime_env() {
  [ -x "$(RUNTIME_PY)" ] || fail \
    "P1-INT-00: the foundation runtime environment $(RUNTIME_PY) is missing." \
    "Run: make bootstrap"
}

require_provider() {
  # $$1 reserved path, $$2 owning task, $$3 expected deliverable
  [ -e "$$1" ] || fail \
    "P1-INT-00: a foundation provider implementation is not present yet." \
    "  reserved path : $$1" \
    "  owning task   : $$2" \
    "  must deliver  : $$3" \
    "This target is a forwarder with no substitute implementation: it fails instead" \
    "of falling back. Dispatch $$2; see docs/program/FOUNDATION_LOCK.json."
  if [ -f "$$1" ] && [ ! -s "$$1" ]; then
    fail "P1-INT-00: the reserved path $$1 exists but is empty." \
      "  owning task   : $$2" \
      "  must deliver  : $$3" \
      "A zero-byte placeholder is not an implementation and is not a pass."
  fi
}

# An exit code is not evidence. A checker must print its success sentinel last, after its
# assertions pass, or this refuses the result. Without it a stubbed or empty checker module
# exits 0 and `make foundation` would report success having proved nothing.
run_checked() {
  local label="$$1"; shift
  local out status
  set +e
  out="$$("$$@" 2>&1)"
  status=$$?
  set -e
  [ -n "$$out" ] && printf '%s\n' "$$out"
  if [ "$$status" -ne 0 ]; then
    fail "P1-INT-00: $$label failed with exit status $$status."
  fi
  printf '%s\n' "$$out" | grep -qx "FOUNDATION-CHECK OK $$label" || fail \
    "P1-INT-00: $$label exited 0 but never printed its success sentinel." \
    "  expected line : FOUNDATION-CHECK OK $$label" \
    "The owning task must print that line last, after its checks pass. Until it does, a" \
    "zero exit status proves nothing and is not accepted as evidence."
}

load_env() {
  [ -f .env ] || fail \
    "P1-INT-00: .env is missing and no default is assumed." \
    "Run: cp .env.example .env" \
    "Then give this lane a unique FOUNDATION_INSTANCE, POSTGRES_PORT, S3_API_PORT," \
    "S3_CONSOLE_PORT, POSTGRES_DB and S3_BUCKET. Two lanes sharing one instance is" \
    "forbidden by FF-01 section 5."
  set -a
  . ./.env
  set +a
  for name in FOUNDATION_INSTANCE POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD \
       POSTGRES_PORT DATABASE_URL MINIO_ROOT_USER MINIO_ROOT_PASSWORD \
       S3_ENDPOINT_URL S3_API_PORT S3_CONSOLE_PORT S3_REGION \
       S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY S3_BUCKET; do
    [ -n "$${!name:-}" ] || fail \
      "P1-INT-00: required environment name $$name is unset or empty in .env." \
      "FF-01 section 3 freezes the full name set; .env.example lists every one."
  done
}

# Needs the runtime interpreter, so only targets that actually reach a service call it.
# `down` deliberately does not: stopping containers must keep working after .venv is gone.
require_env_coherence() {
  "$(RUNTIME_PY)" -c "$$COHERENCE_PROBE"
}

compose() {
  command -v docker >/dev/null 2>&1 || fail \
    "P1-INT-00: docker is not on PATH. It is a documented host prerequisite."
  docker compose --project-name "$$FOUNDATION_INSTANCE" --file "$(INF_COMPOSE)" "$$@"
}

probe_bootstrap_env() {
  local want
  want="$$(sed -n 's/^jsonschema==\([^ ]*\).*/\1/p' "$(VALIDATION_LOCK)")"
  [ -n "$$want" ] || fail "P1-INT-00: cannot read the jsonschema pin from $(VALIDATION_LOCK)."
  "$(BOOTSTRAP_PY)" -c "$$BOOTSTRAP_PROBE" "$$want"
}

probe_runtime_env() {
  "$(RUNTIME_PY)" -c "$$RUNTIME_PROBE"
}
endef

# --- probe programs ----------------------------------------------------------------
# Exported so recipes pass them to python as a single argument. Each probe asserts that
# an environment satisfies its own committed lock; neither prints a pass it did not
# verify.
define BOOTSTRAP_PROBE
import importlib.metadata as md, sys
want = sys.argv[1]
have = md.version("jsonschema")
print(f"    bootstrap: python {sys.version.split()[0]}, jsonschema {have}")
if have != want:
    raise SystemExit(f"P1-INT-00: jsonschema {have} does not match the locked {want}")
endef
export BOOTSTRAP_PROBE

define RUNTIME_PROBE
import importlib.metadata as md, re, sys, tomllib
with open("pyproject.toml", "rb") as fh:
    spec = tomllib.load(fh)
wanted = list(spec["project"]["dependencies"]) + list(spec["dependency-groups"]["test"])
print(f"    runtime:   python {sys.version.split()[0]}")
drift = []
for req in wanted:
    name = re.split(r"[\[=<>;!~ ]", req, maxsplit=1)[0]
    want = req.split("==", 1)[1].strip()
    try:
        have = md.version(name)
    except md.PackageNotFoundError:
        drift.append(f"{name}: pinned {want}, not installed")
        continue
    print(f"    runtime:   {name} {have}")
    if have != want:
        drift.append(f"{name}: pinned {want}, installed {have}")
for mod in ("alembic", "boto3", "psycopg", "pytest", "sqlalchemy"):
    try:
        __import__(mod)
    except ImportError as exc:
        drift.append(f"{mod}: pinned but not importable ({exc})")
if sys.version_info[:2] != (3, 12):
    drift.append(f"interpreter is {sys.version.split()[0]}, not the pinned 3.12 line")
if drift:
    print("P1-INT-00: the runtime environment does not match its pins:", file=sys.stderr)
    for line in drift:
        print(f"  - {line}", file=sys.stderr)
    raise SystemExit(1)
endef
export RUNTIME_PROBE

define COHERENCE_PROBE
import os, sys, urllib.parse as up
e = os.environ
bad = []
u = up.urlparse(e["DATABASE_URL"])
if u.scheme != "postgresql+psycopg":
    bad.append(f'DATABASE_URL scheme is {u.scheme!r}; the locked driver needs "postgresql+psycopg"')
for label, got, want in (
    ("user", up.unquote(u.username or ""), e["POSTGRES_USER"]),
    ("password", up.unquote(u.password or ""), e["POSTGRES_PASSWORD"]),
    ("database", (u.path or "/").lstrip("/"), e["POSTGRES_DB"]),
    ("port", str(u.port or ""), e["POSTGRES_PORT"]),
):
    if got != want:
        bad.append(f"DATABASE_URL {label} is {got!r} but POSTGRES_* says {want!r}")
if not u.hostname:
    bad.append("DATABASE_URL has no host")
s3 = up.urlparse(e["S3_ENDPOINT_URL"])
if s3.scheme not in ("http", "https"):
    bad.append(f"S3_ENDPOINT_URL scheme is {s3.scheme!r}; expected http or https")
if str(s3.port or "") != e["S3_API_PORT"]:
    bad.append(f'S3_ENDPOINT_URL port is {s3.port!r} but S3_API_PORT is {e["S3_API_PORT"]!r}')
if e["S3_API_PORT"] == e["S3_CONSOLE_PORT"]:
    bad.append("S3_API_PORT and S3_CONSOLE_PORT are identical")
if len(e["MINIO_ROOT_PASSWORD"]) < 8:
    bad.append("MINIO_ROOT_PASSWORD is shorter than the 8 characters MinIO requires")
if len(e["S3_SECRET_ACCESS_KEY"]) < 8:
    bad.append("S3_SECRET_ACCESS_KEY is shorter than the 8 characters MinIO requires")
if bad:
    print("P1-INT-00: the service side and the application side of .env disagree.", file=sys.stderr)
    for line in bad:
        print(f"  - {line}", file=sys.stderr)
    print("FF-01 section 3 requires the two sides to stay coherent.", file=sys.stderr)
    raise SystemExit(1)
endef
export COHERENCE_PROBE

# --- 1/9 ---------------------------------------------------------------------------
# Reproduce both git-ignored locked environments. Never regenerates or edits a lock.
bootstrap:
	@$(GUARDS)
	want="$$(cat .python-version)"
	command -v "$(FOUNDATION_PYTHON)" >/dev/null 2>&1 || fail \
	  "P1-INT-00: host interpreter $(FOUNDATION_PYTHON) was not found on PATH." \
	  "The foundation requires CPython $$want. Re-run with an explicit path:" \
	  "  make bootstrap FOUNDATION_PYTHON=/path/to/python3.12"
	"$(FOUNDATION_PYTHON)" -c 'import sys; raise SystemExit(0 if sys.prefix == sys.base_prefix else 1)' || fail \
	  "P1-INT-00: $(FOUNDATION_PYTHON) is an active virtualenv interpreter." \
	  "The foundation is never built from an ambient environment. Pass the base" \
	  "interpreter: make bootstrap FOUNDATION_PYTHON=/path/to/python3.12"
	have="$$("$(FOUNDATION_PYTHON)" -c 'import platform; print(platform.python_version())')"
	[ "$$have" = "$$want" ] || fail \
	  "P1-INT-00: Python version mismatch." \
	  "  .python-version      : $$want" \
	  "  $(FOUNDATION_PYTHON) : $$have" \
	  "The pin is exact. Install $$want, or pass FOUNDATION_PYTHON=<path to $$want>."
	[ -f "$(RUNTIME_LOCK)" ] || fail \
	  "P1-INT-00: $(RUNTIME_LOCK) is missing, and bootstrap does not create it." \
	  "A lock is produced only by its owner, deliberately:" \
	  "  $(UV) lock" \
	  "and is then reviewed and committed as a P1-INT-00 change."
	[ -f "$(VALIDATION_LOCK)" ] || fail \
	  "P1-INT-00: $(VALIDATION_LOCK) is missing, and bootstrap does not create it."
	if [ ! -x "$(UV)" ] || [ "$$("$(UV)" --version 2>/dev/null | awk '{print $$2}')" != "$(UV_VERSION)" ]; then
	  [ "$(UV_HOME)" = ".local/uv" ] || fail \
	    "P1-INT-00: UV_HOME is overridden to '$(UV_HOME)'." \
	    "This recipe removes that path. It only ever removes its own .local/uv."
	  echo "==> installing pinned uv $(UV_VERSION) into $(UV_HOME)"
	  rm -rf "$(UV_HOME)"
	  "$(FOUNDATION_PYTHON)" -m venv "$(UV_HOME)"
	  printf '%s\n' 'uv==$(UV_VERSION) $(UV_HASHES)' > "$(UV_HOME)/uv-requirements.txt"
	  env -u PIP_TARGET -u PIP_PREFIX -u PIP_USER -u PIP_ROOT -u PYTHONUSERBASE \
	    "$(UV_HOME)/bin/python" -m pip install --quiet --disable-pip-version-check \
	    --require-hashes --no-cache-dir --requirement "$(UV_HOME)/uv-requirements.txt"
	fi
	uv_have="$$("$(UV)" --version | awk '{print $$2}')"
	[ "$$uv_have" = "$(UV_VERSION)" ] || fail \
	  "P1-INT-00: uv resolved to $$uv_have, not the pinned $(UV_VERSION)."
	echo "==> syncing $(VENV_RUNTIME) from $(RUNTIME_LOCK) (frozen, no resolution)"
	UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT="$(VENV_RUNTIME)" \
	  "$(UV)" sync --frozen --group test --python "$(FOUNDATION_PYTHON)"
	echo "==> building $(VENV_BOOTSTRAP) from $(VALIDATION_LOCK) (hash-checked)"
	[ -x "$(BOOTSTRAP_PY)" ] || "$(FOUNDATION_PYTHON)" -m venv "$(VENV_BOOTSTRAP)"
	env -u PIP_TARGET -u PIP_PREFIX -u PIP_USER -u PIP_ROOT -u PYTHONUSERBASE \
	  "$(BOOTSTRAP_PY)" -m pip install --quiet --disable-pip-version-check \
	  --require-hashes --requirement "$(VALIDATION_LOCK)"
	echo "==> probing both environments against their locks"
	probe_bootstrap_env
	probe_runtime_env
	echo "bootstrap OK"

# --- 2/9 ---------------------------------------------------------------------------
up:
	@$(GUARDS)
	require_runtime_env
	require_provider "$(INF_COMPOSE)" "P1-INF-01" \
	  "pinned PostgreSQL and MinIO services, namespaced volumes and health checks"
	load_env
	require_env_coherence
	compose up --detach --wait

# --- 3/9 ---------------------------------------------------------------------------
down:
	@$(GUARDS)
	require_provider "$(INF_COMPOSE)" "P1-INF-01" \
	  "pinned PostgreSQL and MinIO services, namespaced volumes and health checks"
	load_env
	compose down

# --- 4/9 ---------------------------------------------------------------------------
check-services:
	@$(GUARDS)
	require_runtime_env
	require_provider "$(INF_CHECK)" "P1-INF-01" \
	  "PostgreSQL/MinIO health proof and idempotent private-bucket initialization"
	load_env
	require_env_coherence
	run_checked check-services env PYTHONPATH=src "$(RUNTIME_PY)" "$(INF_CHECK)"

# --- 5/9 ---------------------------------------------------------------------------
migrate:
	@$(GUARDS)
	require_runtime_env
	require_provider "$(DB_ALEMBIC_INI)" "P1-DB-01" \
	  "the migration head and its runner configuration"
	load_env
	require_env_coherence
	PYTHONPATH=src "$(RUNTIME_PY)" -m alembic --config "$(DB_ALEMBIC_INI)" upgrade head

# --- 6/9 ---------------------------------------------------------------------------
check-db:
	@$(GUARDS)
	require_runtime_env
	require_provider "$(DB_CHECK)" "P1-DB-01" \
	  "application database connectivity and the current migration state"
	load_env
	require_env_coherence
	run_checked check-db env PYTHONPATH=src "$(RUNTIME_PY)" -m auditmanager.shared.db.check

# --- 7/9 ---------------------------------------------------------------------------
check-storage:
	@$(GUARDS)
	require_runtime_env
	require_provider "$(STO_CHECK)" "P1-STO-01" \
	  "BlobStore access to the private bucket through application credentials"
	load_env
	require_env_coherence
	run_checked check-storage env PYTHONPATH=src "$(RUNTIME_PY)" -m auditmanager.storage.check

# --- 8/9 ---------------------------------------------------------------------------
test-foundation:
	@$(GUARDS)
	require_runtime_env
	require_provider "$(QA_SUITE)" "P1-QA-00" \
	  "the cross-provider foundation suite (failure, persistence and privacy evidence)"
	if [ "$$(find "$(QA_SUITE)" -name 'test_*.py' | wc -l)" -eq 0 ]; then
	  fail "P1-INT-00: $(QA_SUITE) contains no test_*.py file." \
	    "An empty suite is not a pass. Owning task: P1-QA-00."
	fi
	load_env
	require_env_coherence
	PYTHONPATH=src "$(RUNTIME_PY)" -m pytest "$(QA_SUITE)"

# --- 9/9 ---------------------------------------------------------------------------
# The accepted foundation sequence, serial by .NOTPARALLEL.
foundation: up check-services migrate check-db check-storage test-foundation
	@echo "foundation sequence complete"
