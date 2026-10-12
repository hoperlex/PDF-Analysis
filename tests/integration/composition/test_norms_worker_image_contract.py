"""`W54-BGE-IMAGE` -- the norms-worker image definition, checked without a container.

The image itself is a heavy step (`W54-FREEZE-01`): its build and the `--network none`
reproduction of the recorded bake-off MRR run in an owner window. What a gate can hold is the
definition, and this file holds all of it:

* every FROM is a tag plus an index digest, and the Dockerfile has no build argument;
* the model comes only from the frozen revision, file by file, each behind `ADD --checksum`,
  and the wheels only from the hashed lock with `--require-hashes --no-deps`;
* nothing reaches the network at run time: the offline variables are baked, the self-check
  runs under `RUN --network=none`, and the reproduction runs `docker run --network none`;
* the profile constants equal the bake-off record, the `0013` profile row and the lock;
* every pin the repository has not recorded is spelled `TODO-PIN-WINDOW` and declared under
  `images.norms_worker.pending_pins` -- an undeclared gap and a stale declaration both fail;
* (`W54-EMBED-01`) the embedder is baked in from exactly the norms package, after the model
  layers, behind a build context cut to an allowlist, and checked offline at build time; the
  build runner and the window check each make one offline `docker run`; the embedder's profile
  constants equal the self-check's.

Each structural check is a function returning its errors, and each is shown able to fail on a
mutant of the real text. The reproduction runner is driven end to end against a `docker` stub
on `PATH`, so its refusals and its comparison are exercised without a container.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKER = ROOT / "infra/norms-worker"
DOCKERFILE = WORKER / "Dockerfile"
REQUIREMENTS_IN = WORKER / "requirements.in"
REQUIREMENTS_LOCK = WORKER / "requirements.lock"
REPRODUCE = WORKER / "reproduce-mrr.sh"
RUN_BUILD = WORKER / "run-build.sh"
CHECK_WINDOWS = WORKER / "check-windows.sh"
DOCKERIGNORE = WORKER / "Dockerfile.dockerignore"
EMBEDDER_PROFILE = ROOT / "src/auditmanager/norms/embedding/profile.py"
SELF_CHECK = WORKER / "self_check.py"
COMPARATOR = WORKER / "compare_bakeoff.py"
LOCK = ROOT / "docs/program/FOUNDATION_LOCK.json"
BAKEOFF_DOC = ROOT / "docs/program/NORM_EMBEDDING_BAKEOFF.md"
RECORDED = ROOT / "fixtures/evaluation/norms/results/bge-m3.json"
PROFILE_MIGRATION = ROOT / "db/migrations/versions/20261001_0013_norm_embeddings.py"

#: Literals, not read from the files under test.
BASE = (
    "python:3.12-slim-bookworm@sha256:"
    "782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254"
)
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
LOCAL_IMAGE = "auditmanager-norms-worker:bge-m3-dense-v1-5617a9f"
TODO = "TODO-PIN-WINDOW"
SNAPSHOT = f"/opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/{REVISION}"
SOURCE = f"https://huggingface.co/BAAI/bge-m3/resolve/{REVISION}/"
RECORDED_MRR = 0.848611

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_FROM_PINNED = re.compile(r"^[a-z0-9][a-z0-9._/-]*:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$")
_FORBIDDEN_FETCHERS = (
    "curl",
    "wget",
    "huggingface-cli",
    "hf download",
    "snapshot_download",
    "hf_hub_download",
    "pip download",
    "git clone",
)


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SELF = _load(SELF_CHECK, "norms_worker_self_check")
COMPARE = _load(COMPARATOR, "norms_worker_compare_bakeoff")


def _instructions(dockerfile: str) -> list[tuple[str, str]]:
    """(keyword, arguments) per instruction, continuation lines joined, comments dropped."""
    logical: list[str] = []
    pending = ""
    for raw in dockerfile.splitlines():
        stripped = raw.strip()
        if not pending and (not stripped or stripped.startswith("#")):
            continue
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
            continue
        logical.append(pending + stripped)
        pending = ""
    assert not pending, "a dangling line continuation"
    result = []
    for line in logical:
        keyword, _, arguments = line.partition(" ")
        result.append((keyword.upper(), " ".join(arguments.split())))
    return result


def _env(dockerfile: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for keyword, arguments in _instructions(dockerfile):
        if keyword == "ENV":
            for pair in arguments.split():
                name, _, value = pair.partition("=")
                values[name] = value
    return values


def _adds(dockerfile: str) -> list[tuple[str, str, str]]:
    """(checksum, source, destination) for every ADD."""
    result = []
    for keyword, arguments in _instructions(dockerfile):
        if keyword != "ADD":
            continue
        words = arguments.split()
        flags = [word for word in words if word.startswith("--")]
        operands = [word for word in words if not word.startswith("--")]
        checksum = next(
            (flag.split("=sha256:", 1)[1] for flag in flags if flag.startswith("--checksum=sha256:")),
            "",
        )
        assert len(operands) == 2, f"ADD must have one source and one destination: {arguments}"
        result.append((checksum, operands[0], operands[1]))
    return result


# --- the structural checks, each a function of the text so a mutant can be fed to it --------


def base_errors(dockerfile: str) -> list[str]:
    errors: list[str] = []
    instructions = _instructions(dockerfile)
    froms = [arguments.split()[0] for keyword, arguments in instructions if keyword == "FROM"]
    if not froms:
        errors.append("no FROM")
    for reference in froms:
        if not _FROM_PINNED.match(reference):
            errors.append(f"FROM {reference} is not tag plus index digest")
    if froms and froms != [BASE]:
        errors.append(f"FROM set {froms} != [{BASE}]")
    if any(keyword == "ARG" for keyword, _ in instructions):
        errors.append("an ARG makes an identity redirectable from a call site")
    if ":latest" in dockerfile:
        errors.append(":latest appears")
    return errors


def model_errors(dockerfile: str) -> list[str]:
    errors: list[str] = []
    adds = _adds(dockerfile)
    fetched = []
    for checksum, source, destination in adds:
        if not (_DIGEST.match(checksum) or checksum == TODO):
            errors.append(f"ADD {source} has no SHA-256 checksum (found {checksum!r})")
        if not source.startswith(SOURCE):
            errors.append(f"ADD {source} is not from the frozen revision")
            continue
        name = source[len(SOURCE) :]
        if destination != f"{SNAPSHOT}/{name}":
            errors.append(f"ADD {name} lands at {destination}, not in the revision snapshot")
        fetched.append(name)
    if sorted(fetched) != sorted(SELF.MODEL_FILES):
        errors.append(f"fetched {sorted(fetched)} != self-check {sorted(SELF.MODEL_FILES)}")
    for keyword, arguments in _instructions(dockerfile):
        if keyword == "RUN":
            for fetcher in _FORBIDDEN_FETCHERS:
                if fetcher in arguments:
                    errors.append(f"RUN fetches outside the checksummed ADDs: {fetcher}")
    installs = [
        arguments
        for keyword, arguments in _instructions(dockerfile)
        if keyword == "RUN" and "pip install" in arguments
    ]
    if len(installs) != 1:
        errors.append(f"expected exactly one pip install, found {len(installs)}")
    for arguments in installs:
        for flag in ("--require-hashes", "--no-deps", "--only-binary=:all:"):
            if flag not in arguments:
                errors.append(f"pip install lacks {flag}")
        if "--requirement /opt/norms-worker/requirements.lock" not in arguments:
            errors.append("pip install does not read the hashed lock")
        refusal = "grep -q 'TODO-PIN' /opt/norms-worker/requirements.lock"
        if refusal not in arguments or arguments.index(refusal) > arguments.index("pip install"):
            errors.append("the TODO wheel-lock refusal does not precede pip install")
    return errors


def offline_errors(dockerfile: str, runner: str) -> list[str]:
    errors: list[str] = []
    env = _env(dockerfile)
    for name, value in SELF.OFFLINE_ENVIRONMENT.items():
        if env.get(name) != value:
            errors.append(f"ENV {name}={env.get(name)!r}, expected {value!r}")
    if env.get("HF_HOME") != "/opt/norms-worker/hf":
        errors.append("HF_HOME is not the baked hub cache")
    instructions = _instructions(dockerfile)
    if ("RUN", "--network=none python /opt/norms-worker/self_check.py") not in instructions:
        errors.append("the self-check does not run under RUN --network=none")
    if instructions[-1] != ("CMD", '["python", "/opt/norms-worker/self_check.py"]'):
        errors.append("the default command is not the offline self-check")
    if any(keyword == "ENTRYPOINT" for keyword, _ in instructions):
        errors.append("an ENTRYPOINT would wrap every run")
    last_model_layer = max(
        (index for index, (keyword, _) in enumerate(instructions) if keyword == "ADD"), default=-1
    )
    if any(
        keyword == "RUN" and "pip install" in arguments
        for keyword, arguments in instructions[last_model_layer + 1 :]
    ):
        errors.append("a pip install after the model layers")

    invocations = [
        line for line in runner.replace("\\\n", " ").splitlines() if line.strip().startswith("docker ")
    ]
    if len(invocations) != 1:
        errors.append(f"expected exactly one docker invocation, found {len(invocations)}")
    for line in invocations:
        words = line.split()
        if words[:2] != ["docker", "run"]:
            errors.append(f"the runner calls docker {words[1:2]}, not docker run")
        for flag in ("--network none", "--pull never", "--rm"):
            if flag not in " ".join(words):
                errors.append(f"docker run lacks {flag}")
        if "target=/work,readonly" not in line or "target=/corpus,readonly" not in line:
            errors.append("the checkout or the corpus is mounted writable")
    return errors


def pending_errors(dockerfile: str, wheel_lock: str, entry: dict) -> list[str]:
    errors: list[str] = []
    measured: set[str] = set()
    checksums = {
        source[len(SOURCE) :]: checksum
        for checksum, source, _ in _adds(dockerfile)
        if source.startswith(SOURCE)
    }
    if entry["model_files_sha256"] != checksums:
        errors.append("the lock's model_files_sha256 differs from the Dockerfile's checksums")
    for name, checksum in checksums.items():
        if checksum == TODO:
            measured.add(f"model_files_sha256/{name}")
    if "TODO-PIN" in wheel_lock:
        measured.add("wheel_lock")
    else:
        requirements = [
            line for line in wheel_lock.replace("\\\n", " ").splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "--"))
        ]
        if not requirements:
            errors.append("the wheel lock pins nothing")
        for line in requirements:
            if not re.search(r"--hash=sha256:[0-9a-f]{64}", line):
                errors.append(f"wheel lock line without a SHA-256: {line.split()[0]}")
    if entry["image_id"] == TODO:
        measured.add("image_id")
    elif not re.fullmatch(r"sha256:[0-9a-f]{64}", entry["image_id"]):
        errors.append(f"image_id {entry['image_id']!r} is neither a digest nor {TODO}")
    declared = set(entry["pending_pins"])
    if len(declared) != len(entry["pending_pins"]):
        errors.append("pending_pins repeats an entry")
    if declared - measured:
        errors.append(f"declared pending but pinned: {sorted(declared - measured)}")
    if measured - declared:
        errors.append(f"unpinned but not declared pending: {sorted(measured - declared)}")
    return errors


def _norms_worker() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))["images"]["norms_worker"]


# --- the real definition passes every check ---------------------------------------------------


def test_every_from_is_pinned_by_index_digest_and_no_identity_is_a_build_argument() -> None:
    assert base_errors(DOCKERFILE.read_text(encoding="utf-8")) == []


def test_the_model_and_wheels_come_only_from_checksummed_and_hashed_inputs() -> None:
    assert model_errors(DOCKERFILE.read_text(encoding="utf-8")) == []


def test_nothing_reaches_the_network_at_run_time() -> None:
    assert offline_errors(
        DOCKERFILE.read_text(encoding="utf-8"), REPRODUCE.read_text(encoding="utf-8")
    ) == []


def test_every_unmeasured_pin_is_declared_pending_and_nothing_else_is() -> None:
    assert pending_errors(
        DOCKERFILE.read_text(encoding="utf-8"),
        REQUIREMENTS_LOCK.read_text(encoding="utf-8"),
        _norms_worker(),
    ) == []


# --- each check is shown able to fail -----------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (f"FROM {BASE}", "FROM python:3.12-slim-bookworm", "not tag plus index digest"),
        (
            f"FROM {BASE}",
            "FROM python:3.12-slim-bookworm@sha256:" + "0" * 64,
            "FROM set",
        ),
        (f"FROM {BASE}", f"ARG BASE={BASE}\nFROM {BASE}", "ARG"),
        ("USER 10001", "USER 10001\nFROM busybox:latest AS extra", ":latest"),
    ],
)
def test_the_base_check_can_fail(old: str, new: str, expected: str) -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert old in text
    errors = base_errors(text.replace(old, new, 1))
    assert any(expected in error for error in errors), errors


#: Mutations as (pattern, replacement), so they hold whether a checksum is still
#: TODO-PIN-WINDOW or already a measured digest.
_MODEL_MUTANTS = [
    (
        r"--checksum=sha256:\S+ (\\\n    " + re.escape(SOURCE) + r"config\.json)",
        r"\1",
        "no SHA-256",
    ),
    (
        r"--checksum=sha256:\S+ (\\\n    " + re.escape(SOURCE) + r"modules\.json)",
        r"--checksum=sha256:abc \1",
        "no SHA-256",
    ),
    (
        re.escape(SOURCE) + r"tokenizer\.json",
        "https://huggingface.co/BAAI/bge-m3/resolve/main/tokenizer.json",
        "frozen revision",
    ),
    (re.escape(f"{SNAPSHOT}/modules.json"), "/tmp/modules.json", "not in the revision snapshot"),
    (
        r"ADD [^\n]*\\\n    " + re.escape(SOURCE) + r"sentencepiece\.bpe\.model \\\n[^\n]*\n",
        "",
        "!= self-check",
    ),
    (r"--require-hashes --no-deps", "--no-deps", "--require-hashes"),
    (r"--no-deps --only-binary", "--only-binary", "--no-deps"),
    (r"--no-deps --only-binary=:all:", "--no-deps", "--only-binary=:all:"),
    (r"python -m venv", "curl -sSf https://example.invalid/x; python -m venv", "curl"),
    (r"    if grep -q 'TODO-PIN'", "    if false", "refusal"),
]


@pytest.mark.parametrize(("pattern", "replacement", "expected"), _MODEL_MUTANTS)
def test_the_model_and_wheel_check_can_fail(pattern: str, replacement: str, expected: str) -> None:
    mutant, count = re.subn(pattern, replacement, DOCKERFILE.read_text(encoding="utf-8"), count=1)
    assert count == 1, f"the mutation {pattern!r} matched nothing"
    errors = model_errors(mutant)
    assert any(expected in error for error in errors), errors


@pytest.mark.parametrize(
    ("target", "old", "new", "expected"),
    [
        ("dockerfile", "    HF_HUB_OFFLINE=1 \\\n", "", "HF_HUB_OFFLINE"),
        ("dockerfile", "    TRANSFORMERS_OFFLINE=1 \\\n", "", "TRANSFORMERS_OFFLINE"),
        ("dockerfile", "RUN --network=none python", "RUN python", "--network=none"),
        ("dockerfile", 'CMD ["python", "/opt/norms-worker/self_check.py"]', 'CMD ["bash"]', "default command"),
        ("runner", "docker run --rm --pull never --network none", "docker run --rm --pull never", "--network none"),
        ("runner", "--pull never ", "", "--pull never"),
        ("runner", "target=/corpus,readonly", "target=/corpus", "writable"),
        ("runner", "target=/work,readonly", "target=/work", "writable"),
    ],
)
def test_the_offline_check_can_fail(target: str, old: str, new: str, expected: str) -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    runner = REPRODUCE.read_text(encoding="utf-8")
    if target == "dockerfile":
        assert old in dockerfile
        dockerfile = dockerfile.replace(old, new, 1)
    else:
        assert old in runner
        runner = runner.replace(old, new, 1)
    errors = offline_errors(dockerfile, runner)
    assert any(expected in error for error in errors), errors


def test_the_pending_check_can_fail_both_ways() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    wheel_lock = REQUIREMENTS_LOCK.read_text(encoding="utf-8")
    entry = _norms_worker()

    undeclared = dict(entry, pending_pins=[pin for pin in entry["pending_pins"] if pin != "wheel_lock"])
    if "TODO-PIN" in wheel_lock:
        errors = pending_errors(dockerfile, wheel_lock, undeclared)
        assert any("not declared pending" in error for error in errors), errors

    stale = dict(entry, pending_pins=[*entry["pending_pins"], "model_files_sha256/onnx/model.onnx"])
    errors = pending_errors(dockerfile, wheel_lock, stale)
    assert any("declared pending but pinned" in error for error in errors), errors

    drifted = dict(entry, model_files_sha256=dict(entry["model_files_sha256"], **{"config.json": "a" * 64}))
    errors = pending_errors(dockerfile, wheel_lock, drifted)
    assert any("differs from the Dockerfile" in error for error in errors), errors

    unhashed = "torch==2.7.1+cpu\n"
    errors = pending_errors(dockerfile, unhashed, dict(entry, pending_pins=[
        pin for pin in entry["pending_pins"] if pin != "wheel_lock"
    ]))
    assert any("without a SHA-256" in error for error in errors), errors


# --- the profile equals the bake-off, the 0013 row and the lock ---------------------------------


def test_profile_constants_equal_the_recorded_bakeoff() -> None:
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))
    doc = BAKEOFF_DOC.read_text(encoding="utf-8")

    assert SELF.PROFILE_ID == "bge-m3-dense-v1"
    assert recorded["model"]["repository"] == SELF.REPOSITORY == "BAAI/bge-m3"
    assert recorded["model"]["revision"] == SELF.REVISION == REVISION
    assert recorded["model"]["query_mode"] == "plain"
    assert recorded["runtime"]["torch"] == SELF.RUNTIME["torch"]
    assert recorded["runtime"]["transformers"] == SELF.RUNTIME["transformers"]
    assert recorded["runtime"]["sentence_transformers"] == SELF.RUNTIME["sentence_transformers"]
    assert recorded["runtime"]["threads"] == SELF.THREADS == 8
    assert f"`tokenizers=={SELF.RUNTIME['tokenizers']}`" in doc
    assert f"`numpy=={SELF.RUNTIME['numpy']}`" in doc
    assert recorded["inference"]["dimension"] == SELF.DIMENSIONS == 1024
    assert recorded["inference"]["normalization"] == "L2"
    assert recorded["tokenization"]["limit"] == SELF.MAX_TOKENS == 512
    assert recorded["tokenization"]["overlap"] == SELF.OVERLAP_TOKENS == 64
    assert recorded["tokenization"]["special_tokens"] == SELF.SPECIAL_TOKENS == 2
    assert recorded["tokenization"]["passage_prefix"] == ""
    assert "| plain | CLS | 16 |" in doc and SELF.POOLING == "cls"
    assert SELF.DTYPE == "float32" and "1024-dimensional float32 vector" in doc
    assert recorded["benchmark"]["mrr"] == RECORDED_MRR
    assert recorded["benchmark"]["queries"] == 24
    assert recorded["benchmark"]["candidate_windows"] == 563


def test_profile_constants_equal_the_0013_profile_row() -> None:
    migration = PROFILE_MIGRATION.read_text(encoding="utf-8")
    row = (
        f"'{SELF.PROFILE_ID}', '{SELF.REPOSITORY}',\n"
        f"            '{SELF.REVISION}',\n"
        f"            '{SELF.REVISION}',\n"
        f"            '{SELF.RUNTIME['transformers']}', '{SELF.RUNTIME['sentence_transformers']}', "
        f"'{SELF.POOLING}', {SELF.DIMENSIONS}, true, 'inner_product', "
        f"{SELF.MAX_TOKENS}, {SELF.OVERLAP_TOKENS}"
    )
    assert row in migration


def test_wheel_inputs_and_image_environment_carry_the_same_runtime_and_threads() -> None:
    requirements = {
        name.strip(): version.strip()
        for name, version in (
            line.split("==", 1)
            for line in REQUIREMENTS_IN.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        )
    }
    assert requirements == {name.replace("_", "-"): value for name, value in SELF.RUNTIME.items()}
    env = _env(DOCKERFILE.read_text(encoding="utf-8"))
    assert env["OMP_NUM_THREADS"] == env["MKL_NUM_THREADS"] == str(SELF.THREADS)
    assert env["TOKENIZERS_PARALLELISM"] == "false"
    assert env["AUDITMANAGER_EMBEDDING_PROFILE"] == SELF.PROFILE_ID
    assert f"--threads {SELF.THREADS}" in REPRODUCE.read_text(encoding="utf-8")
    assert f'io.auditmanager.embedding.revision="{REVISION}"' in DOCKERFILE.read_text(encoding="utf-8")


def test_foundation_lock_matches_the_executable_definition() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    entry = lock["images"]["norms_worker"]
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))

    assert entry["dockerfile"] == "infra/norms-worker/Dockerfile"
    assert entry["build_context"] == "."
    assert entry["dockerignore"] == "infra/norms-worker/Dockerfile.dockerignore"
    assert entry["local_image"] == LOCAL_IMAGE
    assert entry["base_image"] == BASE
    assert entry["wheel_inputs"] == "infra/norms-worker/requirements.in"
    assert entry["wheel_lock"] == "infra/norms-worker/requirements.lock"
    assert entry["runtime"] == SELF.RUNTIME
    assert entry["profile"] == {
        "id": SELF.PROFILE_ID,
        "repository": SELF.REPOSITORY,
        "revision": SELF.REVISION,
        "pooling": SELF.POOLING,
        "dimensions": SELF.DIMENSIONS,
        "dtype": SELF.DTYPE,
        "normalized": True,
        "distance": "inner_product",
        "max_tokens": SELF.MAX_TOKENS,
        "overlap_tokens": SELF.OVERLAP_TOKENS,
        "threads": SELF.THREADS,
    }
    assert entry["model_source_template"] == f"{SOURCE}<file>"
    assert sorted(entry["model_files_sha256"]) == sorted(SELF.MODEL_FILES)
    reproduction = entry["reproduction"]
    assert reproduction["runner"] == "infra/norms-worker/reproduce-mrr.sh"
    assert reproduction["comparator"] == "infra/norms-worker/compare_bakeoff.py"
    assert reproduction["recorded_result"] == "fixtures/evaluation/norms/results/bge-m3.json"
    assert reproduction["mrr"] == recorded["benchmark"]["mrr"] == RECORDED_MRR
    assert reproduction["queries"] == recorded["benchmark"]["queries"]
    assert reproduction["candidate_windows"] == recorded["benchmark"]["candidate_windows"]
    assert "infra/norms-worker" in lock["images"]["immutability"]["rule"]
    assert f"--tag {LOCAL_IMAGE} ." in DOCKERFILE.read_text(encoding="utf-8")
    embedder = entry["embedder"]
    assert embedder["package"] == "src/auditmanager/norms/embedding"
    assert embedder["build_runner"] == "infra/norms-worker/run-build.sh"
    assert embedder["window_check"] == "infra/norms-worker/check-windows.sh"
    assert embedder["build_self_check"] == f"RUN {EMBEDDER_SELF_TEST}"
    assert embedder["digest_format"] == "norm-embedding-set/2"
    assert embedder["embed_texts_format"] == "auditmanager-embed-texts/1"


# --- the comparator and the runner, driven without a container ---------------------------------


def _recorded() -> dict:
    return json.loads(RECORDED.read_text(encoding="utf-8"))


def test_the_comparator_accepts_the_record_and_ignores_only_host_fields() -> None:
    measured = _recorded()
    measured["runtime"]["python"] = "3.12.99"
    measured["runtime"]["platform"] = "Linux-container"
    measured["inference"]["passage_seconds"] = 1.0
    measured["inference"]["max_rss_mib"] = 1.0
    assert COMPARE.differences(_recorded(), measured) == []


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("benchmark", "mrr"), 0.848612),
        (("benchmark", "ranks", "q19_ventilation_purpose"), 2),
        (("benchmark", "candidate_windows"), 562),
        (("runner_sha256",), "0" * 64),
        (("runtime", "torch"), "2.7.1"),
        (("tokenization", "character_chunks", "windowed_rows"), 62324),
        (("inference", "dimension"), 768),
    ],
)
def test_the_comparator_refuses_any_deterministic_difference(path: tuple[str, ...], value: object) -> None:
    measured = _recorded()
    target = measured
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    found = COMPARE.differences(_recorded(), measured)
    assert [line.split(":", 1)[0] for line in found] == [".".join(path)]


def test_the_comparator_refuses_a_missing_field() -> None:
    measured = _recorded()
    del measured["benchmark"]["recall_at_5"]
    assert COMPARE.differences(_recorded(), measured) == [
        "benchmark.recall_at_5: recorded 0.958333, absent from the run"
    ]


_DOCKER_STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$STUB_ARGV"
for argument in "$@"; do
  case "$argument" in
    type=bind,source=*,target=/out)
      directory=${argument#type=bind,source=}
      cp "$STUB_RESULT" "${directory%,target=/out}/bge-m3.json"
      ;;
  esac
done
"""


def _sandbox(tmp_path: Path, script_text: str | None = None) -> tuple[Path, Path, Path, dict[str, str]]:
    """A checkout-shaped copy of the runner and comparator, a corpus, and a docker stub."""
    checkout = tmp_path / "checkout"
    (checkout / "infra/norms-worker").mkdir(parents=True)
    (checkout / "fixtures/evaluation/norms/results").mkdir(parents=True)
    runner = checkout / "infra/norms-worker/reproduce-mrr.sh"
    runner.write_text(script_text or REPRODUCE.read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copy(COMPARATOR, checkout / "infra/norms-worker/compare_bakeoff.py")
    shutil.copy(RECORDED, checkout / "fixtures/evaluation/norms/results/bge-m3.json")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "MANIFEST.json").write_text("{}", encoding="utf-8")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    docker = stubs / "docker"
    docker.write_text(_DOCKER_STUB, encoding="utf-8")
    docker.chmod(0o755)
    environment = dict(
        os.environ,
        PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}",
        STUB_ARGV=str(tmp_path / "docker.argv"),
        STUB_RESULT=str(RECORDED),
    )
    return runner, corpus, tmp_path / "docker.argv", environment


def _run(runner: Path, corpus: Path, output: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(runner), LOCAL_IMAGE, str(corpus), str(output)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=60,
    )


def test_the_runner_reproduces_the_recorded_line_through_one_offline_docker_run(tmp_path: Path) -> None:
    runner, corpus, argv_log, environment = _sandbox(tmp_path)
    output = tmp_path / "out"
    completed = _run(runner, corpus, output, environment)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines()[-1] == (
        "norms-worker MRR reproduced: 0.848611 (24 queries, 563 windows)"
    )
    argv = argv_log.read_text(encoding="utf-8").splitlines()
    assert argv[:6] == ["run", "--rm", "--pull", "never", "--network", "none"]
    checkout = runner.parents[2].resolve()
    assert f"type=bind,source={checkout},target=/work,readonly" in argv
    assert f"type=bind,source={corpus.resolve()},target=/corpus,readonly" in argv
    assert f"type=bind,source={output.resolve()},target=/out" in argv
    assert LOCAL_IMAGE in argv
    tail = argv[argv.index(LOCAL_IMAGE) + 1 :]
    assert tail == [
        "python",
        "/work/tools/norms/embedding_bakeoff.py",
        "--corpus",
        "/corpus",
        "--fixture",
        "/work/fixtures/evaluation/norms/retrieval_queries.v1.json",
        "--model",
        "bge-m3",
        "--output",
        "/out/bge-m3.json",
        "--threads",
        "8",
    ]


def test_the_runner_fails_when_the_run_differs_from_the_record(tmp_path: Path) -> None:
    runner, corpus, _, environment = _sandbox(tmp_path)
    drifted = _recorded()
    drifted["benchmark"]["mrr"] = 0.84
    drifted_path = tmp_path / "drifted.json"
    drifted_path.write_text(json.dumps(drifted), encoding="utf-8")
    environment["STUB_RESULT"] = str(drifted_path)

    completed = _run(runner, corpus, tmp_path / "out", environment)

    assert completed.returncode == 1
    assert "MISMATCH benchmark.mrr: recorded 0.848611, measured 0.84" in completed.stderr
    assert "norms-worker MRR NOT reproduced" in completed.stderr


_GUARDS = {
    "not-a-corpus": (
        'if [ ! -f "$corpus/MANIFEST.json" ]; then\n'
        '  echo "refused: $corpus is not a corpus drop (no MANIFEST.json)" >&2\n'
        "  exit 2\n"
        "fi\n"
    ),
    "inside-the-corpus": (
        'case "$output/" in\n'
        '  "$corpus/"*)\n'
        '    echo "refused: the output directory $output lies inside the corpus drop" >&2\n'
        "    exit 2\n"
        "    ;;\n"
        "esac\n"
    ),
    "not-empty": (
        'if [ -n "$(ls -A -- "$output")" ]; then\n'
        '  echo "refused: the output directory $output is not empty" >&2\n'
        "  exit 2\n"
        "fi\n"
    ),
}


def _arrange(case: str, corpus: Path, tmp_path: Path) -> Path:
    if case == "not-a-corpus":
        (corpus / "MANIFEST.json").unlink()
        return tmp_path / "out"
    if case == "inside-the-corpus":
        return corpus / "out"
    output = tmp_path / "out"
    output.mkdir()
    (output / "bge-m3.json").write_text("{}", encoding="utf-8")
    return output


@pytest.mark.parametrize("case", sorted(_GUARDS))
def test_each_runner_refusal_happens_before_docker_and_can_fail(case: str, tmp_path: Path) -> None:
    real = REPRODUCE.read_text(encoding="utf-8")
    assert real.count(_GUARDS[case]) == 1

    runner, corpus, argv_log, environment = _sandbox(tmp_path / "real")
    completed = _run(runner, corpus, _arrange(case, corpus, tmp_path / "real"), environment)
    assert completed.returncode == 2, completed.stderr
    assert "refused:" in completed.stderr
    assert not argv_log.exists(), "docker was invoked before the refusal"

    mutant, corpus, argv_log, environment = _sandbox(
        tmp_path / "mutant", real.replace(_GUARDS[case], "", 1)
    )
    completed = _run(mutant, corpus, _arrange(case, corpus, tmp_path / "mutant"), environment)
    assert "refused:" not in completed.stderr
    assert argv_log.exists(), "without its guard the runner reaches docker"


# --- W54-EMBED-01: the embedder inside the image ------------------------------------------------

EMBEDDER_SELF_TEST = "--network=none python -m auditmanager.norms.embedding self-test"
#: (source in the repository-root context, destination) -- every COPY the Dockerfile may hold.
COPIES = [
    ("infra/norms-worker/requirements.lock", "/opt/norms-worker/requirements.lock"),
    ("infra/norms-worker/self_check.py", "/opt/norms-worker/self_check.py"),
    ("src/auditmanager/__init__.py", "/opt/norms-worker/src/auditmanager/__init__.py"),
    ("src/auditmanager/norms/", "/opt/norms-worker/src/auditmanager/norms/"),
]
ALLOWLIST = [
    "infra/norms-worker/requirements.lock",
    "infra/norms-worker/self_check.py",
    "src/auditmanager/__init__.py",
    "src/auditmanager/norms",
]


def _patterns(dockerignore: str) -> list[str]:
    return [
        line.strip() for line in dockerignore.splitlines() if line.strip() and not line.startswith("#")
    ]


def embedder_errors(dockerfile: str, dockerignore: str) -> list[str]:
    errors: list[str] = []
    instructions = _instructions(dockerfile)
    copies = [tuple(arguments.split()) for keyword, arguments in instructions if keyword == "COPY"]
    if copies != COPIES:
        errors.append(f"COPY set {copies} != {COPIES}")
    last_model = max((index for index, (keyword, _) in enumerate(instructions) if keyword == "ADD"), default=-1)
    code = [
        index for index, (keyword, arguments) in enumerate(instructions)
        if keyword == "COPY" and arguments.startswith("src/")
    ]
    if not code or min(code) < last_model:
        errors.append("the embedder code is copied before the model layers")
    if _env(dockerfile).get("PYTHONPATH") != "/opt/norms-worker/src":
        errors.append("PYTHONPATH does not name the baked package")
    runs = [index for index, (keyword, arguments) in enumerate(instructions) if (keyword, arguments) == ("RUN", EMBEDDER_SELF_TEST)]
    if len(runs) != 1:
        errors.append("the embedder self-test does not run once under RUN --network=none")
    elif code and runs[0] < max(code):
        errors.append("the embedder self-test runs before the embedder is copied")

    patterns = _patterns(dockerignore)
    if not patterns or patterns[0] != "*":
        errors.append("the context allowlist does not start by excluding everything")
    included = [pattern[1:] for pattern in patterns if pattern.startswith("!")]
    if included != ALLOWLIST:
        errors.append(f"the context allowlist re-includes {included}, not {ALLOWLIST}")
    for source, _ in copies:
        if not any(source.rstrip("/") == entry or source.startswith(entry + "/") for entry in included):
            errors.append(f"COPY {source} is outside the context allowlist")
    if any(".local" in pattern and pattern.startswith("!") for pattern in patterns):
        errors.append("the context allowlist re-includes .local")
    return errors


def runner_errors(script: str, *, mounts: dict[str, str], command: str) -> list[str]:
    """One offline ``docker run``; exactly these mount targets with these modes; this command."""
    errors: list[str] = []
    joined = script.replace("\\\n", " ")
    invocations = [line for line in joined.splitlines() if line.strip().startswith("docker ")]
    if len(invocations) != 1:
        return [f"expected exactly one docker invocation, found {len(invocations)}"]
    line = " ".join(invocations[0].split())
    if not line.startswith("docker run "):
        errors.append("the runner calls docker without run")
    for flag in ("--network none", "--pull never", "--rm"):
        if flag not in line:
            errors.append(f"docker run lacks {flag}")
    found = dict(re.findall(r"target=(/\w+)(,readonly)?", line))
    expected = {target: (",readonly" if mode == "readonly" else "") for target, mode in mounts.items()}
    if found != expected:
        errors.append(f"mounts {found} != {expected}")
    if command not in line:
        errors.append(f"the container does not run {command!r}")
    return errors


RUN_BUILD_MOUNTS = {"/checkpoint": "rw"}
RUN_BUILD_COMMAND = "python -m auditmanager.norms.embedding build"
CHECK_MOUNTS = {"/work": "readonly", "/corpus": "readonly", "/out": "rw"}
CHECK_COMMAND = "python /work/infra/norms-worker/check_windows.py"


def test_the_embedder_is_baked_from_exactly_the_norms_package_behind_an_allowlist() -> None:
    assert embedder_errors(DOCKERFILE.read_text(encoding="utf-8"), DOCKERIGNORE.read_text(encoding="utf-8")) == []


def test_the_build_runner_and_the_window_check_are_one_offline_docker_run_each() -> None:
    assert runner_errors(RUN_BUILD.read_text(encoding="utf-8"), mounts=RUN_BUILD_MOUNTS, command=RUN_BUILD_COMMAND) == []
    assert runner_errors(CHECK_WINDOWS.read_text(encoding="utf-8"), mounts=CHECK_MOUNTS, command=CHECK_COMMAND) == []


@pytest.mark.parametrize(
    ("target", "old", "new", "expected"),
    [
        ("dockerfile", "COPY src/auditmanager/norms/ /opt/norms-worker/src/auditmanager/norms/",
         "COPY src/ /opt/norms-worker/src/", "COPY set"),
        ("dockerfile", "COPY src/auditmanager/__init__.py /opt/norms-worker/src/auditmanager/__init__.py\n",
         "COPY src/auditmanager/__init__.py /opt/norms-worker/src/auditmanager/__init__.py\nCOPY .local/norms /corpus\n",
         "COPY set"),
        ("dockerfile", "    PYTHONPATH=/opt/norms-worker/src \\\n", "", "PYTHONPATH"),
        ("dockerfile", "RUN --network=none python -m auditmanager.norms.embedding self-test",
         "RUN python -m auditmanager.norms.embedding self-test", "self-test does not run"),
        ("dockerignore", "*\n!infra", "!infra", "excluding everything"),
        ("dockerignore", "!src/auditmanager/norms\n", "!src/auditmanager/norms\n!.local/norms/corpus\n", "re-includes"),
        ("dockerignore", "!src/auditmanager/norms\n", "", "outside the context allowlist"),
    ],
)
def test_the_embedder_check_can_fail(target: str, old: str, new: str, expected: str) -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    dockerignore = DOCKERIGNORE.read_text(encoding="utf-8")
    if target == "dockerfile":
        assert old in dockerfile
        dockerfile = dockerfile.replace(old, new, 1)
    else:
        assert old in dockerignore
        dockerignore = dockerignore.replace(old, new, 1)
    errors = embedder_errors(dockerfile, dockerignore)
    assert any(expected in error for error in errors), errors


def test_the_code_layers_come_after_the_model_layers_and_the_check_sees_it() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    line = "COPY src/auditmanager/norms/ /opt/norms-worker/src/auditmanager/norms/\n"
    moved = dockerfile.replace(line, "", 1).replace(
        "COPY infra/norms-worker/requirements.lock", line + "COPY infra/norms-worker/requirements.lock", 1
    )
    errors = embedder_errors(moved, DOCKERIGNORE.read_text(encoding="utf-8"))
    assert any("before the model layers" in error for error in errors), errors


@pytest.mark.parametrize(
    ("script", "old", "new", "expected"),
    [
        ("build", "--network none", "", "--network none"),
        ("build", "--pull never ", "", "--pull never"),
        ("build", 'target=/checkpoint"', 'target=/checkpoint" --mount "type=bind,source=/,target=/host"', "mounts"),
        ("build", "python -m auditmanager.norms.embedding build", "python -c pass", "does not run"),
        ("check", "target=/corpus,readonly", "target=/corpus", "mounts"),
        ("check", "target=/work,readonly", "target=/work", "mounts"),
    ],
)
def test_the_runner_check_can_fail(script: str, old: str, new: str, expected: str) -> None:
    path, mounts, command = (
        (RUN_BUILD, RUN_BUILD_MOUNTS, RUN_BUILD_COMMAND) if script == "build" else (CHECK_WINDOWS, CHECK_MOUNTS, CHECK_COMMAND)
    )
    text = path.read_text(encoding="utf-8")
    assert old in text
    errors = runner_errors(text.replace(old, new, 1), mounts=mounts, command=command)
    assert any(expected in error for error in errors), errors


def test_the_embedder_profile_equals_the_self_check() -> None:
    profile = _load(EMBEDDER_PROFILE, "norms_embedding_profile")
    assert profile.EMBEDDING_PROFILE == SELF.PROFILE_ID
    assert profile.MODEL_REPOSITORY == SELF.REPOSITORY
    assert profile.MODEL_REVISION == SELF.REVISION == REVISION
    assert profile.DIMENSIONS == SELF.DIMENSIONS
    assert (profile.MAX_TOKENS, profile.OVERLAP_TOKENS) == (SELF.MAX_TOKENS, SELF.OVERLAP_TOKENS)
    assert profile.SPECIAL_TOKENS == SELF.SPECIAL_TOKENS
    assert profile.THREADS == SELF.THREADS
    assert profile.ENCODE_BATCH_SIZE == _recorded()["model"]["batch_size"]
    assert profile.PASSAGE_PREFIX == _recorded()["tokenization"]["passage_prefix"]


# --- run-build.sh, driven against a docker stub ---------------------------------------------------

_BUILD_STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$STUB_ARGV"
exit "${STUB_EXIT:-0}"
"""
SNAPSHOT_ID = "ns_" + "0" * 26


def _build_sandbox(tmp_path: Path, script_text: str | None = None) -> tuple[Path, Path, Path, dict[str, str]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    runner = tmp_path / "run-build.sh"
    runner.write_text(script_text or RUN_BUILD.read_text(encoding="utf-8"), encoding="utf-8")
    checkpoint = tmp_path / "builds" / "key"
    checkpoint.mkdir(parents=True)
    (checkpoint / "plan.json").write_text("{}", encoding="utf-8")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    docker = stubs / "docker"
    docker.write_text(_BUILD_STUB, encoding="utf-8")
    docker.chmod(0o755)
    environment = dict(
        os.environ, PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}", STUB_ARGV=str(tmp_path / "docker.argv")
    )
    return runner, checkpoint, tmp_path / "docker.argv", environment


def _run_build(runner: Path, *arguments: str, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(runner), LOCAL_IMAGE, *arguments],
        capture_output=True, text=True, env=environment, check=False, timeout=60,
    )


def test_run_build_makes_one_offline_docker_run_and_passes_the_exit_status_through(tmp_path: Path) -> None:
    runner, checkpoint, argv_log, environment = _build_sandbox(tmp_path)
    completed = _run_build(runner, str(checkpoint), SNAPSHOT_ID, "characters-v2:1200", "3", environment=environment)
    assert completed.returncode == 0, completed.stderr
    argv = argv_log.read_text(encoding="utf-8").splitlines()
    assert argv[:10] == ["run", "--rm", "--pull", "never", "--network", "none", "--memory", "5g", "--memory-swap", "5g"]
    assert f"type=bind,source={checkpoint.resolve()},target=/checkpoint" in argv
    assert argv[argv.index(LOCAL_IMAGE) + 1 :] == [
        "python", "-m", "auditmanager.norms.embedding", "build",
        "--snapshot", SNAPSHOT_ID, "--chunking-profile", "characters-v2:1200",
        "--checkpoint", "/checkpoint", "--max-batches", "3",
    ]
    environment["STUB_EXIT"] = "75"
    completed = _run_build(runner, str(checkpoint), SNAPSHOT_ID, "characters-v2:1200", environment=environment)
    assert completed.returncode == 75
    assert "--max-batches" not in argv_log.read_text(encoding="utf-8").splitlines()


_BUILD_GUARDS = {
    "no-plan": (
        'if [ ! -f "$checkpoint/plan.json" ]; then\n'
        '  echo "refused: $checkpoint holds no plan.json; run prepare first" >&2\n'
        "  exit 2\n"
        "fi\n"
    ),
    "inside-the-corpus": (
        'case "$checkpoint/" in\n'
        "  */.local/norms/corpus/*)\n"
        '    echo "refused: the checkpoint directory $checkpoint lies inside the corpus drop" >&2\n'
        "    exit 2\n"
        "    ;;\n"
        "esac\n"
    ),
    "bad-snapshot": (
        'if ! [[ "$snapshot" =~ ^ns_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then\n'
        '  echo "refused: $snapshot is not a norms snapshot id" >&2\n'
        "  exit 2\n"
        "fi\n"
    ),
}


def _arrange_build(case: str, checkpoint: Path) -> tuple[str, str]:
    if case == "no-plan":
        (checkpoint / "plan.json").unlink()
        return str(checkpoint), SNAPSHOT_ID
    if case == "inside-the-corpus":
        inside = checkpoint.parent / ".local" / "norms" / "corpus" / "x"
        inside.mkdir(parents=True)
        (inside / "plan.json").write_text("{}", encoding="utf-8")
        return str(inside), SNAPSHOT_ID
    return str(checkpoint), "ns_not-an-id"


@pytest.mark.parametrize("case", sorted(_BUILD_GUARDS))
def test_each_run_build_refusal_happens_before_docker_and_can_fail(case: str, tmp_path: Path) -> None:
    real = RUN_BUILD.read_text(encoding="utf-8")
    assert real.count(_BUILD_GUARDS[case]) == 1

    runner, checkpoint, argv_log, environment = _build_sandbox(tmp_path / "real")
    directory, snapshot = _arrange_build(case, checkpoint)
    completed = _run_build(runner, directory, snapshot, "characters-v2:1200", environment=environment)
    assert completed.returncode == 2 and "refused:" in completed.stderr
    assert not argv_log.exists(), "docker was invoked before the refusal"

    mutant, checkpoint, argv_log, environment = _build_sandbox(
        tmp_path / "mutant", real.replace(_BUILD_GUARDS[case], "", 1)
    )
    directory, snapshot = _arrange_build(case, checkpoint)
    completed = _run_build(mutant, directory, snapshot, "characters-v2:1200", environment=environment)
    assert "refused:" not in completed.stderr
    assert argv_log.exists(), "without its guard the runner reaches docker"
