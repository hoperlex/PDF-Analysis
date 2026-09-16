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
# `.SHELLFLAGS` makes every recipe a NON-INTERACTIVE bash, and bash sources $BASH_ENV for
# exactly those. An ambient BASH_ENV pointing at a file containing `trap 'exit 0' EXIT`
# rewrites a failed recipe's status to 0 after the command has already reported failure.
# `unexport` stops make handing these to the recipe shell at all; .env cannot carry them
# either, because it is a strict allowlist of the 15 frozen names.
unexport BASH_ENV
unexport ENV
unexport SHELLOPTS
unexport BASHOPTS
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
# `override` is deliberate: it defeats a command-line assignment and `make -e`, so
# `make up FOUNDATION_POSTGRES_IMAGE=...` cannot swap the image. load_env additionally
# rejects these names in .env and re-asserts these literals from this file's bytes after
# parsing it. `.env` is never sourced. Image identity has exactly one owner and cannot be
# redirected from the call site.
override FOUNDATION_POSTGRES_IMAGE := postgres:17.11-trixie@sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675
override FOUNDATION_S3_IMAGE := minio/minio:RELEASE.2025-09-07T16-13-09Z@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e
override FOUNDATION_S3_MC_IMAGE := minio/mc:RELEASE.2025-08-13T08-35-41Z@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727
export FOUNDATION_POSTGRES_IMAGE
export FOUNDATION_S3_IMAGE
export FOUNDATION_S3_MC_IMAGE

# Names a lane may never set: they carry image identity, not lane configuration.
override RESERVED_IMAGE_NAMES := FOUNDATION_POSTGRES_IMAGE FOUNDATION_S3_IMAGE FOUNDATION_S3_MC_IMAGE

# --- owned environment layout ------------------------------------------------------
# Every environment below is git-ignored and is reproduced only from a committed lock.
# Every one of these is declared with `override` AND a literal value, for the same reason
# the image pins are: `override` defeats a command-line assignment and `make -e`, and the
# literal spelling is what lets a recipe re-read the value out of this file's own bytes
# (see frozen_value), which is the only form a target-scoped --eval, a MAKEFLAGS-injected
# --eval or a second -f makefile cannot shadow. A composed value like
# $(VENV_RUNTIME)/bin/python could not be read back that way, so nothing here is composed.
# The file this Makefile's own bytes live in, resolved at parse time. `lastword` is
# deliberate: when a wrapper makefile `include`s this one, MAKEFILE_LIST is
# "wrapper.mk thisfile" while this line is being read, so this resolves to THIS file and
# not to the wrapper. `abspath` is what closes the decoy-directory attack: awk over a
# bare `Makefile` reads ./Makefile, so `make -f /real/Makefile` launched from a directory
# holding an attacker's copy read the attacker's copy instead.
override MAKEFILE_SELF := $(abspath $(lastword $(MAKEFILE_LIST)))

# `-t` (touch) marks targets up to date without running them. It is never a legitimate
# way to invoke this surface, and unlike a recipe-level guard this fires at parse time,
# which is the only place a check can still run when make has decided not to execute
# recipes. `-n` (dry run) is deliberately NOT refused: `make -n` is a documented required
# check. A caller who sets MAKEFLAGS=-n gets no recipe output at all - no `bootstrap OK`,
# no pytest summary - so a dry run cannot be mistaken for evidence by anyone reading it.
# GNU make puts the single-letter options, with no leading dash, in the FIRST WORD of
# MAKEFLAGS - and only there, and only when such options exist. A long option like
# `--eval=x:=/tmp/y` becomes the first word instead, with a leading dash. Testing
# `findstring t` against the raw first word therefore fires on the `t` inside `/tmp`,
# rejecting a legitimate invocation; the cluster is only a cluster when it has no dash.
override MAKE_SHORT_FLAGS := $(filter-out -%,$(firstword $(MAKEFLAGS)))
ifneq (,$(findstring t,$(MAKE_SHORT_FLAGS)))
$(error P1-INT-00: make -t (touch mode) is refused. It would mark targets up to date \
without running a single check. Run the target for real.)
endif

override VENV_RUNTIME := .venv
override VENV_BOOTSTRAP := .venv/bootstrap
override UV_HOME := .local/uv
# Project-local, git-ignored uv cache. Pinned so a bare `make bootstrap` never writes
# to the user cache (~/.cache/uv) and needs no undocumented UV_CACHE_DIR override.
override UV_CACHE := .local/uv-cache
# Same reasoning for pip: the .venv/bootstrap install is hash-checked but still caches
# wheels, and a bare `make bootstrap` must not write into the user's home either.
override PIP_CACHE := .local/pip-cache
override RUNTIME_PY := .venv/bin/python
override BOOTSTRAP_PY := .venv/bootstrap/bin/python
override UV := .local/uv/bin/uv
export UV_CACHE_DIR := $(UV_CACHE)
export PIP_CACHE_DIR := $(PIP_CACHE)
override VALIDATION_LOCK := requirements/validation.lock
override RUNTIME_LOCK := uv.lock

# --- reserved provider paths (FF-01 section 3) --------------------------------------
# P1-INT-00 reserves these paths and writes none of them. The values are frozen: FF-01
# names them, so this task may harden how they are resolved but never change what they
# are. Each recipe resolves them through frozen_value, out of this file's bytes, so a
# forwarder always addresses the exact frozen path no matter what the call site says.
override INF_COMPOSE := infra/local/docker-compose.yml
override INF_CHECK := infra/local/check_services.py
override DB_ALEMBIC_INI := db/migrations/alembic.ini
override DB_CHECK := src/auditmanager/shared/db/check.py
override STO_CHECK := src/auditmanager/storage/check.py
override QA_SUITE := tests/integration/foundation

.PHONY: bootstrap up down check-services migrate check-db check-storage test-foundation gate mutation-copy foundation

# --- shared guards -----------------------------------------------------------------
# Expanded verbatim into each recipe that needs them. No guard has a success path that
# substitutes a missing implementation or invents an unset value.
define GUARDS
fail() { printf '%s\n' "$$@" >&2; exit 1; }

# The single de-shadowing primitive. It reads a value out of THIS FILE'S BYTES rather
# than taking a make expansion, because every make-level channel that can redirect a
# variable - a command-line assignment, `make -e`, a target-scoped `--eval` (including
# one smuggled in through MAKEFLAGS or GNUMAKEFLAGS with no visible command change), and
# a second `-f` makefile that re-`override`s it - changes only the expansion. None of
# them can change the bytes of the `override NAME := VALUE` line below.
frozen_value() {
  local name="$$1" value
  value="$$(awk -v n="$$name" '$$1=="override" && $$2==n && $$3==":=" {print $$4; exit}' "$(MAKEFILE_SELF)")"
  [ -n "$$value" ] || fail \
    "P1-INT-00: cannot read the frozen value of $$name out of the Makefile." \
    "The literal \`override $$name := <value>\` line is the single source of truth."
  printf '%s\n' "$$value"
}

# Re-asserts the six FF-01 reserved provider paths and the two interpreters from this
# file's bytes, into shell variables the recipes use instead of make expansions. A
# forwarder therefore always addresses the exact frozen path. `make up
# INF_COMPOSE=/tmp/evil.yml`, `make -e`, `--eval='up: INF_COMPOSE := ...'`, the same
# through MAKEFLAGS/GNUMAKEFLAGS, and a wrapper makefile all leave these unchanged.
freeze_paths() {
  local name
  for name in INF_COMPOSE INF_CHECK DB_ALEMBIC_INI DB_CHECK STO_CHECK QA_SUITE \
              RUNTIME_PY BOOTSTRAP_PY VALIDATION_LOCK RUNTIME_LOCK; do
    printf -v "$$name" '%s' "$$(frozen_value "$$name")"
  done
  # A redirected interpreter is the same class of defeat as a redirected suite path:
  # `make test-foundation RUNTIME_PY=/bin/true` would otherwise run `/bin/true -m pytest`
  # and exit 0 having executed no test at all.
  case "$$RUNTIME_PY" in .venv/bin/python) ;; *) fail \
    "P1-INT-00: the frozen runtime interpreter is not .venv/bin/python." ;; esac
}

require_runtime_env() {
  [ -x "$$RUNTIME_PY" ] || fail \
    "P1-INT-00: the foundation runtime environment $$RUNTIME_PY is missing." \
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
  # Leading NAME=VALUE assignments up to `--` are forwarded to the single scrubbed_run
  # below. They cannot be written into the argv as a nested `scrubbed_run ... --` call:
  # scrubbed_run ends in `exec "$$@"`, exec cannot run a shell function, and the nested
  # form therefore exits 127 before the checker is ever reached.
  local assigns=() a
  while [ "$$1" != "--" ]; do
    a="$$1"
    # Reject anything that is not NAME=VALUE. Without this a malformed call site is
    # silently exported as a bare variable name and the mistake survives into the next
    # session: the nested `scrubbed_run` form shipped exactly this way and left
    # check-services, check-db and check-storage unrunnable for a full cycle.
    case "$$a" in
      [A-Za-z_]*=*) ;;
      *) fail "P1-INT-00: run_checked expects NAME=VALUE before \`--\`, got: $$a" ;;
    esac
    assigns+=("$$a"); shift
  done
  shift
  local out status
  set +e
  # PYTHONUNBUFFERED makes stdout line-buffered even though command substitution hands the
  # checker a pipe. Without it the merged capture reflects BUFFERING order, not action
  # order: a checker that prints the sentinel and then logs to stderr would have that
  # stderr arrive first and its sentinel still look last.
  out="$$(scrubbed_run "$${assigns[@]}" PYTHONUNBUFFERED=1 -- "$$@" 2>&1)"
  status=$$?
  set -e
  [ -n "$$out" ] && printf '%s\n' "$$out"
  if [ "$$status" -ne 0 ]; then
    fail "P1-INT-00: $$label failed with exit status $$status."
  fi
  # The sentinel must be the LAST actual line, not merely present somewhere: output after
  # it means the checker kept working past its own success claim. ANSI colour, CR and
  # surrounding whitespace are normalised away first so a legitimately colourized or
  # indented sentinel is not refused; blank lines after it are ignored.
  local last
  last="$$(printf '%s\n' "$$out" \
    | sed -e 's/\x1b\[[0-9;?]*[a-zA-Z]//g' -e 's/\r//g' \
          -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' -e '/^$$/d' \
    | tail -n 1)"
  if [ "$$last" != "FOUNDATION-CHECK OK $$label" ]; then
    fail "P1-INT-00: $$label did not end with its success sentinel." \
      "  expected last line : FOUNDATION-CHECK OK $$label" \
      "  actual last line   : $${last:-<no output>}" \
      "The owning task must print the sentinel last, after its checks pass. A zero exit" \
      "status without it, or visible output after it, is not accepted as evidence."
  fi
}

# The 15 names FF-01 section 3 freezes. This is a strict ALLOWLIST, not a denylist: a
# name outside it is refused, so no ambient-behaviour variable can be smuggled in by
# thinking of one nobody blacklisted. All 15 are required and each may appear once.
FROZEN_ENV_NAMES="FOUNDATION_INSTANCE POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD \
POSTGRES_PORT DATABASE_URL MINIO_ROOT_USER MINIO_ROOT_PASSWORD S3_ENDPOINT_URL \
S3_API_PORT S3_CONSOLE_PORT S3_REGION S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY S3_BUCKET"

load_env() {
  [ -f .env ] || fail \
    "P1-INT-00: .env is missing and no default is assumed." \
    "Run: cp .env.example .env" \
    "Then give this lane a unique FOUNDATION_INSTANCE, POSTGRES_PORT, S3_API_PORT," \
    "S3_CONSOLE_PORT, POSTGRES_DB and S3_BUCKET. Two lanes sharing one instance is" \
    "forbidden by FF-01 section 5."
  local line name value lineno=0 seen="" known q body
  while IFS= read -r line || [ -n "$$line" ]; do
    lineno=$$((lineno + 1))
    line="$${line%%$$'\r'}"
    line="$${line#"$${line%%[![:space:]]*}"}"
    case "$$line" in ''|'#'*) continue ;; esac
    case "$$line" in
      export[[:space:]]*)
        line="$${line#export}"
        line="$${line#"$${line%%[![:space:]]*}"}"
        ;;
    esac
    case "$$line" in
      *=*) ;;
      *) fail "P1-INT-00: .env line $$lineno is not a NAME=VALUE assignment." \
           "  line: $$line" \
           ".env is parsed as data, never executed. Remove anything that is not an" \
           "assignment or a # comment." ;;
    esac
    name="$${line%%=*}"
    value="$${line#*=}"
    name="$${name%"$${name##*[![:space:]]}"}"
    if ! [[ "$$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$$ ]]; then
      fail "P1-INT-00: .env line $$lineno has an invalid variable name." \
        "  name: $$name" \
        "Only NAME=VALUE with a plain shell identifier is accepted."
    fi
    case "$$name" in
      FOUNDATION_POSTGRES_IMAGE|FOUNDATION_S3_IMAGE|FOUNDATION_S3_MC_IMAGE)
        fail "P1-INT-00: .env line $$lineno sets the reserved image variable $$name." \
          "Container image identity is owned by this Makefile and recorded in" \
          "docs/program/FOUNDATION_LOCK.json. A lane configures instance, ports, database" \
          "and bucket - never which image runs. Remove that line from .env." \
          "A different image is a pin request back to P1-INT-00." ;;
    esac
    # Strict allowlist. Anything not frozen by FF-01 section 3 is refused, whether or not
    # anyone thought to blacklist it: PYTEST_ADDOPTS, PYTHONNOUSERSITE, DOCKER_HOST,
    # AWS_*, SSL_CERT_FILE, a BASH_FUNC_* export and every other ambient-behaviour name
    # are all outside the list and therefore all rejected by one rule.
    known=no
    for q in $$FROZEN_ENV_NAMES; do
      [ "$$name" = "$$q" ] && { known=yes; break; }
    done
    [ "$$known" = yes ] || fail \
      "P1-INT-00: .env line $$lineno sets $$name, which is not a frozen environment name." \
      "FF-01 section 3 freezes exactly 15 names and .env may contain only those:" \
      "  $$FROZEN_ENV_NAMES" \
      ".env configures this lane's services. It does not carry tool options, credentials" \
      "for other systems, or anything that selects what code runs."
    case " $$seen " in
      *" $$name "*) fail \
        "P1-INT-00: .env line $$lineno assigns $$name a second time." \
        "A repeated name is ambiguous: the reader would silently take one of the two." \
        "Keep exactly one assignment per frozen name." ;;
    esac
    seen="$$seen $$name"
    # Quotes are allowed only as one matched wrapping pair. An unmatched or interior
    # quote is REFUSED rather than kept as an ambiguous literal, because `X="abc` would
    # otherwise export the six characters "abc - a value no operator intended and one
    # that later re-quoting could turn back into something else.
    case "$$value" in
      \"*|\'*)
        q="$${value%"$${value#?}"}"
        if [ "$${#value}" -lt 2 ] || [ "$${value#"$${value%?}"}" != "$$q" ]; then
          fail "P1-INT-00: .env line $$lineno opens a $$q quote it never closes." \
            "  name: $$name" \
            "A value either carries no quotes at all or is wrapped in one matching pair."
        fi
        body="$${value#?}"; body="$${body%?}"
        case "$$body" in
          *"$$q"*) fail \
            "P1-INT-00: .env line $$lineno has a $$q quote inside a $$q-quoted value." \
            "  name: $$name" \
            "There is no escaping in .env. Use the other quote character, or a value" \
            "that does not contain a quote." ;;
        esac
        value="$$body"
        ;;
      *\"*|*\'*)
        fail "P1-INT-00: .env line $$lineno has a quote that does not wrap the value." \
          "  name: $$name" \
          "Quotes are accepted only as one matching pair around the whole value." ;;
    esac
    export "$$name=$$value"
  done < .env
  assert_image_pins
  for name in $$FROZEN_ENV_NAMES; do
    [ -n "$${!name:-}" ] || fail \
      "P1-INT-00: required environment name $$name is unset or empty in .env." \
      "FF-01 section 3 freezes the full name set; .env.example lists every one."
  done
}

# Image identity is taken from THIS FILE'S BYTES, not from a make variable expansion.
# A make variable can be shadowed per target (`make up --eval='up: VAR := evil'`, or the
# same through MAKEFLAGS/GNUMAKEFLAGS with no visible command change), and a second `-f`
# makefile can re-`override` it; none of that can alter the bytes of the `override` lines
# below. The names are spelled literally here for the same reason.
assert_image_pins() {
  local name value
  for name in FOUNDATION_POSTGRES_IMAGE FOUNDATION_S3_IMAGE FOUNDATION_S3_MC_IMAGE; do
    value="$$(awk -v n="$$name" '$$1=="override" && $$2==n {print $$4; exit}' "$(MAKEFILE_SELF)")"
    [ -n "$$value" ] || fail \
      "P1-INT-00: cannot read the pinned $$name out of the Makefile." \
      "The `override $$name := <ref>` line is the single source of image identity."
    case "$$value" in
      *@sha256:*) ;;
      *) fail "P1-INT-00: the pinned $$name is not digest-pinned." \
           "  value: $$value" \
           "Every foundation image is pinned by tag AND digest (FF-01 section 2 item 9)." ;;
    esac
    export "$$name=$$value"
  done
}

# Needs the runtime interpreter, so only targets that actually reach a service call it.
# `down` deliberately does not: stopping containers must keep working after .venv is gone.
require_env_coherence() {
  "$$RUNTIME_PY" -c "$$COHERENCE_PROBE"
}

compose() {
  command -v docker >/dev/null 2>&1 || fail \
    "P1-INT-00: docker is not on PATH. It is a documented host prerequisite."
  docker compose --project-name "$$FOUNDATION_INSTANCE" --file "$$INF_COMPOSE" "$$@"
}

# pytest reads options and plugins out of the ambient environment, so a green run is not
# by itself evidence that the suite ran. PYTEST_ADDOPTS=--collect-only collects and exits
# 0 without executing a single test; PYTEST_PLUGINS loads an arbitrary module that can
# force outcomes; PYTEST_DISABLE_PLUGIN_AUTOLOAD changes which plugins participate. .env
# can no longer carry any of them (the allowlist refuses every name outside the frozen
# 15), but the ambient environment still can, so every PYTEST_* and the PYTHON* names
# that change interpretation are scrubbed here rather than trusted.
# Runs a command with the interpreter-behaviour environment scrubbed. It unsets in the
# CURRENT shell inside a subshell rather than calling `env`, because an exported bash
# function named `env` shadows the binary: `env(){ return 0; }; export -f env` would
# otherwise make every scrubbed command a silent success.
scrubbed_run() {
  local assigns=() name
  while [ "$$1" != "--" ]; do assigns+=("$$1"); shift; done
  shift
  (
    while IFS= read -r name; do
      unset "$$name" || true
    done < <(compgen -e | grep -E '^(PYTEST_|PYTHONWARNINGS$$|PYTHONSTARTUP$$|PYTHONHOME$$|PYTHONDONTWRITEBYTECODE$$|PYTHONOPTIMIZE$$|PYTHONINSPECT$$|PYTHONPROFILEIMPORTTIME$$|LD_AUDIT$$|LD_PRELOAD$$|LD_LIBRARY_PATH$$|OPENSSL_CONF$$|GLIBC_TUNABLES$$)' || true)
    export PYTHONNOUSERSITE=1
    for name in "$${assigns[@]}"; do export "$$name"; done
    exec "$$@"
  )
}

run_suite() {
  local suite="$$1" status
  set +e
  # `-c pyproject.toml` pins the config file. Without it pytest's locate_config walks up
  # from the suite directory, so a pytest.ini, tox.ini or setup.cfg dropped inside the QA
  # lane's own directory would become the configfile, move rootdir into that directory and
  # silently discard the root `pythonpath = ["src"]` and `--import-mode=importlib` - while
  # being free to add `addopts = --collect-only`.
  scrubbed_run PYTHONPATH=src PYTHONUNBUFFERED=1 -- \
    "$$RUNTIME_PY" -m pytest -c pyproject.toml --rootdir=. "$$suite"
  status=$$?
  set -e
  # pytest's own exit codes: 0 all passed, 1 failures, 2 interrupted, 3 internal error,
  # 4 usage error, 5 NO TESTS COLLECTED. 5 is the one that looks like nothing went wrong
  # and must never be read as a pass.
  if [ "$$status" -eq 5 ]; then
    fail "P1-INT-00: pytest collected no tests from $$suite." \
      "Exit status 5 means nothing ran. An empty or fully deselected run is not a pass." \
      "Owning task: P1-QA-00."
  fi
  [ "$$status" -eq 0 ] || fail \
    "P1-INT-00: the foundation suite failed with pytest exit status $$status."
}

probe_bootstrap_env() {
  "$$BOOTSTRAP_PY" -c "$$BOOTSTRAP_PROBE" "$$VALIDATION_LOCK"
}

probe_runtime_env() {
  "$$RUNTIME_PY" -c "$$RUNTIME_PROBE"
}
# --- the gate's own steps ----------------------------------------------------------
# `run_suite` above is the foundation suite's runner and carries that suite's failure
# messages. These are the other three things a wave must pass, and they lived only in
# `OPERATING_CONSTRAINTS.md` as prose until wave 7 -- which is to say they lived in
# whoever happened to remember them.

run_battery() {
  # OPERATING_CONSTRAINTS.md section 7. `tests/contract` and `tests/checkpoint` are CP-00
  # historical evidence, red before any wave starts and quarantined by
  # PROTOTYPE_PROFILE.md section 6.3, so they are excluded here rather than left to each
  # caller to remember -- the reason this target exists at all.
  local status
  set +e
  scrubbed_run PYTHONUNBUFFERED=1 -- \
    "$$RUNTIME_PY" -m pytest -c pyproject.toml --rootdir=. -q \
    tests --ignore=tests/contract --ignore=tests/checkpoint
  status=$$?
  set -e
  if [ "$$status" -eq 5 ]; then
    fail "GATE: pytest collected no tests from the canonical battery." \
      "Exit status 5 means nothing ran. An empty or fully deselected run is not a pass."
  fi
  [ "$$status" -eq 0 ] || fail \
    "GATE: the canonical battery failed with pytest exit status $$status."
}

run_frontend() {
  # The frontend is a delivered part of PC-01 and four waves passed without it being run
  # once, because no target named it. It fails rather than skips when the toolchain is
  # absent: a gate that quietly drops a component reports a pass it did not earn.
  command -v npm >/dev/null 2>&1 || fail \
    "GATE: npm is not on PATH, so the frontend suite cannot run." \
    "The gate does not skip a component it cannot check. Install the toolchain, or" \
    "run the backend halves individually and say in the wave record that web/ was not" \
    "covered."
  # No fallback to another checkout's modules, deliberately. A linked worktree is exactly
  # where package.json might differ from the one those modules were installed for, and
  # borrowing them would run the wrong dependency set while looking like a pass. The cost
  # of an install per worktree is the price of the suite meaning what it says.
  [ -d web/node_modules ] || fail \
    "GATE: web/node_modules is absent in this checkout." \
    "Run: npm --prefix web ci" \
    "A linked worktree does not inherit it -- node_modules is git-ignored -- and the gate" \
    "will not borrow another checkout's modules, because that would run a dependency set" \
    "this tree never declared."
  npm --prefix web test || fail "GATE: the frontend suite failed."
}

# --- the mutation copy -------------------------------------------------------------
# Every anti-vacuity proof in this programme runs against a copy of `src/` outside the
# worktree, so that no tracked file is ever edited to mutate. The recipe for building that
# copy has been carried as prose in dispatch briefs since wave 3, and in wave 10 it turned
# out to be **incomplete**: it named `contracts/`, `docs/` and `fixtures/` and omitted `db/`
# and `tools/`. A copy without `tools/` fails four `p02_journey` tests *unmutated*, so the
# recipe did not merely miss coverage -- it manufactured reds.
#
# Each entry below is derived from the tree, not from the brief:
#   contracts/ exports/policy.py, documents/models.py, shared/errors/catalog.py,
#              analysis/engine/registry.py -- all resolve it from parents[3] or [4]
#   docs/      analysis/text/lock.py -> docs/program/P02_LOCK.json
#   fixtures/  analysis/text/recorded.py -> fixtures/recorded/text_analysis
#   db/        shared/db/migrations.py -> db/migrations/alembic.ini
#   tools/     resolved test-side from `auditmanager.__file__` on purpose, so a mutation run
#              gets the copy's ledger tool rather than silently reading the pristine one
#
mutation_copy() {
  local dest="$$1"
  [ -n "$$dest" ] || fail "mutation_copy: no destination given."
  case "$$dest" in /root/*|/home/*) ;; *) fail \
    "mutation_copy: refusing to build under $$dest." \
    "Docker here is snap-confined and cannot see /tmp; use a path under /root/." ;; esac
  case "$$dest" in "$$PWD"|"$$PWD"/*) fail \
    "mutation_copy: $$dest is inside the worktree." \
    "The whole point is that no tracked file is ever edited to mutate." ;; esac
  rm -rf "$$dest"
  mkdir -p "$$dest"
  cp -a src "$$dest/src"
  local name
  for name in contracts docs fixtures db tools; do
    [ -e "$$name" ] || fail "mutation_copy: $$name is not in this checkout."
    ln -s "$$PWD/$$name" "$$dest/$$name"
  done
  printf '%s\n' "mutation copy at $$dest"
}

probe_mutation_copy() {
  # Proves the copy is the tree that will be imported, and that every root-resolved path
  # reaches it. A mutation result from a copy that was not imported proves nothing, and a
  # red from a copy missing a directory proves less than nothing.
  scrubbed_run PYTHONUNBUFFERED=1 -- "$$RUNTIME_PY" -c "$$MUTATION_COPY_PROBE" "$$1"
}

check_whitespace() {
  git diff --check || fail \
    "GATE: git diff --check reports whitespace errors in the working tree."
}
endef

# --- the mutation-copy probe -------------------------------------------------------
define MUTATION_COPY_PROBE
import sys, pathlib
dest = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(dest / "src"))
import auditmanager
here = pathlib.Path(auditmanager.__file__).resolve()
if dest not in here.parents:
    raise SystemExit("MUTATION-COPY FAIL: auditmanager imported from %s, not under %s" % (here, dest))
missing = [n for n in ("contracts", "docs", "fixtures", "db", "tools") if not (dest / n).exists()]
if missing:
    raise SystemExit("MUTATION-COPY FAIL: unreachable from the copy: %s" % missing)
from auditmanager.analysis.text import lock as _lock
from auditmanager.shared.errors import catalog as _catalog
print("MUTATION-COPY OK %s" % here)
endef
export MUTATION_COPY_PROBE

# --- probe programs ----------------------------------------------------------------
# Exported so recipes pass them to python as a single argument. Each probe asserts that
# an environment satisfies its own committed lock; neither prints a pass it did not
# verify.
define BOOTSTRAP_PROBE
# Proves the governance environment is EXACTLY the lock: every pinned distribution at
# its pinned version, and nothing else installed. `pip install --require-hashes` only
# adds and upgrades; it never removes, so without this an extra distribution - a
# hand-installed plugin, a leftover from an earlier lock - would sit in the validator
# environment unnoticed and could change what the validator does.
import importlib.metadata as md, re, sys
lock = sys.argv[1]
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
# venv seeds pip; it is not in the lock and is not an extra.
SEEDED = {"pip"}  # python3.12 venv seeds pip only; measured, not assumed
want = {}
for raw in open(lock, encoding="utf-8"):
    line = raw.split("#", 1)[0].strip().rstrip("\\").strip()
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)", line)
    if m:
        want[norm(m.group(1))] = m.group(2)
if not want:
    raise SystemExit(f"P1-INT-00: no pinned distribution found in {lock}")
have = {}
for dist in md.distributions():
    name = dist.metadata["Name"]
    if name:
        have[norm(name)] = dist.version
print(f"    bootstrap: python {sys.version.split()[0]}, {len(want)} locked distributions")
drift = []
for name, version in sorted(want.items()):
    if name not in have:
        drift.append(f"{name}: locked {version}, not installed")
    elif have[name] != version:
        drift.append(f"{name}: locked {version}, installed {have[name]}")
extra = sorted(set(have) - set(want) - SEEDED)
for name in extra:
    drift.append(f"{name} {have[name]}: installed but absent from {lock}")
if drift:
    print("P1-INT-00: the governance environment does not match its lock:", file=sys.stderr)
    for line in drift:
        print(f"  - {line}", file=sys.stderr)
    if extra:
        print("Remove the extra distribution, or re-create the environment:", file=sys.stderr)
        print("  rm -rf .venv/bootstrap && make bootstrap", file=sys.stderr)
    raise SystemExit(1)
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

define EXTRA_DISTS
# Prints the distributions installed in this environment that the lock does not name,
# one per line, so bootstrap can remove them. pip itself is seeded by venv and is never
# reported. Nothing is printed when the environment already matches the lock.
import importlib.metadata as md, re, sys
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
SEEDED = {"pip"}  # python3.12 venv seeds pip only; measured, not assumed
want = set()
for raw in open(sys.argv[1], encoding="utf-8"):
    line = raw.split("#", 1)[0].strip().rstrip("\\").strip()
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", line)
    if m:
        want.add(norm(m.group(1)))
for dist in md.distributions():
    name = dist.metadata["Name"]
    if name and norm(name) not in want and norm(name) not in SEEDED:
        print(name)
endef
export EXTRA_DISTS

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
	freeze_paths
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
	[ -f "$$RUNTIME_LOCK" ] || fail \
	  "P1-INT-00: $(RUNTIME_LOCK) is missing, and bootstrap does not create it." \
	  "A lock is produced only by its owner, deliberately:" \
	  "  $(UV) lock" \
	  "and is then reviewed and committed as a P1-INT-00 change."
	[ -f "$$VALIDATION_LOCK" ] || fail \
	  "P1-INT-00: $$VALIDATION_LOCK is missing, and bootstrap does not create it."
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
	# uv refuses a project environment directory that exists but holds no interpreter, and
	# it will not build one over the top. That is exactly the shape of a checkout whose
	# governance environment was created first: $(VENV_BOOTSTRAP) nests inside
	# $(VENV_RUNTIME), so `.venv` exists containing only `bootstrap/` and no `bin/python`,
	# and bootstrap fails with "not a valid Python environment". A fresh clone never shows
	# it, because there uv creates `.venv` before anything nests inside it - which is why
	# every authoring lane passed and only convergence on the main checkout hit it.
	# Seed the interpreter first, exactly as the bootstrap environment is seeded below:
	# `python -m venv` adds bin/, lib/ and pyvenv.cfg beside an existing subdirectory and
	# leaves $(VENV_BOOTSTRAP) untouched.
	[ -x "$(VENV_RUNTIME)/bin/python" ] || "$(FOUNDATION_PYTHON)" -m venv "$(VENV_RUNTIME)"
	env -u VIRTUAL_ENV UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT="$(VENV_RUNTIME)" \
	  "$(UV)" sync --frozen --group test --python "$(FOUNDATION_PYTHON)"
	echo "==> building $(VENV_BOOTSTRAP) from $(VALIDATION_LOCK) (hash-checked)"
	[ -x "$$BOOTSTRAP_PY" ] || "$(FOUNDATION_PYTHON)" -m venv "$$(dirname "$$(dirname "$$BOOTSTRAP_PY")")"
	env -u PIP_TARGET -u PIP_PREFIX -u PIP_USER -u PIP_ROOT -u PYTHONUSERBASE \
	  "$$BOOTSTRAP_PY" -m pip install --quiet --disable-pip-version-check \
	  --require-hashes --requirement "$$VALIDATION_LOCK"
	# `pip install` only adds and upgrades. Anything installed here that the lock does
	# not name is removed now, so a repeated bootstrap converges on exactly the lock
	# instead of accumulating whatever a previous state left behind.
	extra="$$("$$BOOTSTRAP_PY" -c "$$EXTRA_DISTS" "$$VALIDATION_LOCK")"
	if [ -n "$$extra" ]; then
	  echo "==> removing distributions absent from $$VALIDATION_LOCK: $$extra"
	  env -u PIP_TARGET -u PIP_PREFIX -u PIP_USER -u PIP_ROOT -u PYTHONUSERBASE \
	    "$$BOOTSTRAP_PY" -m pip uninstall --quiet --yes $$extra || true
	  # pip uninstall can exit 0 having removed nothing when a RECORD is incomplete, so
	  # the probe below is what decides; this line never reports success on its own.
	fi
	echo "==> probing both environments against their locks"
	probe_bootstrap_env
	probe_runtime_env
	echo "bootstrap OK"

# --- 2/9 ---------------------------------------------------------------------------
up:
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	require_provider "$$INF_COMPOSE" "P1-INF-01" \
	  "pinned PostgreSQL and MinIO services, namespaced volumes and health checks"
	load_env
	require_env_coherence
	compose up --detach --wait

# --- 3/9 ---------------------------------------------------------------------------
down:
	@$(GUARDS)
	freeze_paths
	require_provider "$$INF_COMPOSE" "P1-INF-01" \
	  "pinned PostgreSQL and MinIO services, namespaced volumes and health checks"
	load_env
	compose down

# --- 4/9 ---------------------------------------------------------------------------
check-services:
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	require_provider "$$INF_CHECK" "P1-INF-01" \
	  "PostgreSQL/MinIO health proof and idempotent private-bucket initialization"
	load_env
	require_env_coherence
	run_checked check-services PYTHONPATH=src -- "$$RUNTIME_PY" "$$INF_CHECK"

# --- 5/9 ---------------------------------------------------------------------------
migrate:
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	require_provider "$$DB_ALEMBIC_INI" "P1-DB-01" \
	  "the migration head and its runner configuration"
	load_env
	require_env_coherence
	PYTHONPATH=src "$$RUNTIME_PY" -m alembic --config "$$DB_ALEMBIC_INI" upgrade head

# --- 6/9 ---------------------------------------------------------------------------
check-db:
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	require_provider "$$DB_CHECK" "P1-DB-01" \
	  "application database connectivity and the current migration state"
	load_env
	require_env_coherence
	run_checked check-db PYTHONPATH=src -- "$$RUNTIME_PY" -m auditmanager.shared.db.check

# --- 7/9 ---------------------------------------------------------------------------
check-storage:
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	require_provider "$$STO_CHECK" "P1-STO-01" \
	  "BlobStore access to the private bucket through application credentials"
	load_env
	require_env_coherence
	run_checked check-storage PYTHONPATH=src -- "$$RUNTIME_PY" -m auditmanager.storage.check

# --- 8/9 ---------------------------------------------------------------------------
test-foundation:
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	require_provider "$$QA_SUITE" "P1-QA-00" \
	  "the cross-provider foundation suite (failure, persistence and privacy evidence)"
	if [ "$$(find "$$QA_SUITE" -name 'test_*.py' | wc -l)" -eq 0 ]; then
	  fail "P1-INT-00: $$QA_SUITE contains no test_*.py file." \
	    "An empty suite is not a pass. Owning task: P1-QA-00."
	fi
	load_env
	require_env_coherence
	run_suite "$$QA_SUITE"

# --- 9/9 ---------------------------------------------------------------------------
# The accepted foundation sequence, serial by .NOTPARALLEL.
foundation: up check-services migrate check-db check-storage test-foundation
	@echo "foundation sequence complete"

# --- the gate ----------------------------------------------------------------------
# Everything a wave must pass, as one command.
#
# Before wave 7 this was four things and only one of them was a target: `make
# foundation` was in the Makefile, while the canonical battery, the frontend suite and
# `git diff --check` existed as prose in OPERATING_CONSTRAINTS.md. Three quarters of the
# gate was a convention carried in somebody's head, and the frontend half of it had not
# been run since wave 2 because nothing required it.
#
# The composition is now reviewable in a diff instead of recalled from a closure, which
# is the same correction this programme has made to registers, to briefs and to its own
# schema assumptions.
# --- a proved mutation copy --------------------------------------------------------
# Usage: make mutation-copy MUT=/root/<name>-mut
# Then:  .venv/bin/pytest <suite> -o pythonpath=/root/<name>-mut/src -p no:randomly
#
# Build the copy, then run your suites against it **unmutated** and confirm they are green
# before you trust a single red. That baseline is the part the prose recipe never had.
MUT ?=
mutation-copy:
	@$(GUARDS)
	[ -n "$(MUT)" ] || fail \
	  "make mutation-copy needs a destination: make mutation-copy MUT=/root/<name>-mut"
	freeze_paths
	require_runtime_env
	mutation_copy "$(MUT)"
	probe_mutation_copy "$(MUT)"
	printf '%s\n' \
	  "Next: run your suites against the UNMUTATED copy and confirm green." \
	  "  .venv/bin/pytest <suite> -o pythonpath=$(MUT)/src -p no:randomly" \
	  "A red from a copy you never baselined is not evidence."

gate: foundation
	@$(GUARDS)
	freeze_paths
	require_runtime_env
	load_env
	require_env_coherence
	run_battery
	run_frontend
	check_whitespace
	printf '%s\n' "GATE OK: battery, foundation, frontend and whitespace all pass"
