"""`CMP-VC-AIPAIR-01`: what ties the lane to the rest of the tree, container-free -- the names it exports, the vocabulary pinned to
the migration and to the contract, the limits pinned to the executors' and to the original's, who writes which table, the module
flag as the first statement of every operation, and the context boundary."""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

import pytest

from auditmanager.api.schemas import models
from auditmanager.comparison import public
from auditmanager.comparison.ai_pairs import handler, method, model, prompt
from auditmanager.comparison.work.registry import HandlerRegistry
from auditmanager.comparison.work.model import WorkDependencies
from auditmanager.executors.public import MAX_IMAGES

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src/auditmanager"
PACKAGE = SRC / "comparison/ai_pairs"


def _migration():
    path = next((ROOT / "db/migrations/versions").glob("*_0040_comparison_ai_reports.py"))
    spec = importlib.util.spec_from_file_location("migration_0040_for_ai_pairs_pins", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# -- the names ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["PAIR_CHECK_KIND", "PAIR_CHECK_PROMPT_VERSION", "AiPairModelBinder", "ComparisonAiPairService",
                                  "PairCheckHandler", "decide_pair_check", "pair_check_handler"])
def test_the_lane_is_exported_from_the_comparison_public_surface(name: str) -> None:
    assert name in public.__all__ and getattr(public, name) is not None


def test_the_work_kind_has_exactly_one_handler_in_the_shipped_tuple() -> None:
    kinds = [factory(WorkDependencies(None, None, None, None)).kind for factory in public.HANDLER_FACTORIES]  # type: ignore[arg-type]
    assert kinds.count("comparison_pair_check") == 1
    assert HandlerRegistry.build(public.HANDLER_FACTORIES, WorkDependencies(None, None, None, None)).kinds >= {"comparison_pair_check"}  # type: ignore[arg-type]


def test_the_kind_is_the_one_the_executors_route_and_the_core_derives_from_the_method() -> None:
    from auditmanager.executors.model import WORK_KINDS

    assert model.PAIR_CHECK_KIND == "comparison_pair_check" == public.ai_work_kind_of("pair_check")
    assert model.PAIR_CHECK_KIND in WORK_KINDS and handler.PairCheckHandler.kind == model.PAIR_CHECK_KIND


def test_the_method_is_a_method_of_the_core_and_its_prompt_version_is_in_the_estimate() -> None:
    assert isinstance(method.PairCheckMethod(provider_mode="recorded"), public.AiMethod)
    assert method.PairCheckMethod.method == "pair_check" and method.PairCheckMethod.prompt_version == model.PROMPT_VERSION


# -- the vocabulary is the database's and the contract's -----------------------------------------------------------------------------


def test_the_vocabulary_is_the_migrations() -> None:
    migration = _migration()
    assert model.DECISIONS == migration.DECISIONS
    assert model.QUESTION_STATES == migration.QUESTION_STATES
    assert model.ANSWER_KINDS == migration.ANSWER_KINDS
    assert model.ANSWER_CONFIDENCES == migration.CONFIDENCES
    assert (model.KIND_NO_PAIR, model.KIND_MEDIUM_PAIR) == migration.QUESTION_KINDS


def test_the_vocabulary_is_the_contracts() -> None:
    assert {member.value for member in models.ComparisonAiPairDecision} == set(model.DECISIONS)
    assert {member.value for member in models.ComparisonAiPairQuestionKind} == {model.KIND_NO_PAIR, model.KIND_MEDIUM_PAIR}
    assert {member.value for member in models.ComparisonAiConfidence} == set(model.ANSWER_CONFIDENCES)


def test_every_hint_decision_is_a_decision_and_no_decision_is_both_a_hint_and_a_link() -> None:
    assert model.HINT_DECISIONS < set(model.DECISIONS) and model.DECISION_LINK_ACCEPTED not in model.HINT_DECISIONS
    assert model.CONFLICT_MATRIX_STALE == "comparison_matrix_stale"


# -- the limits ------------------------------------------------------------------------------------------------------------------------


def test_a_request_never_carries_more_pictures_than_the_executors_allow() -> None:
    """A-12 and ADR-0025 decision 18: the sheet and its candidates, at most eight in all."""
    assert 1 + model.MAX_CANDIDATES_NO_PAIR <= MAX_IMAGES and 1 + model.MAX_REVERSE_CANDIDATES + 1 <= MAX_IMAGES
    assert model.MAX_CANDIDATES_NO_PAIR == 4 and model.MAX_REVERSE_CANDIDATES == 3, "the original's [:4] and [:3] (sheet_match.py:154, :320)"


def test_the_answer_schema_is_the_originals() -> None:
    schema = prompt.ANSWER_SCHEMA
    assert schema["required"] == ["choice", "page", "confidence", "reason"] and schema["additionalProperties"] is False
    assert schema["properties"] == {
        "choice": {"type": "integer"}, "page": {"type": "integer"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]}, "reason": {"type": "string"},
    }


# -- who writes what ---------------------------------------------------------------------------------------------------------------------


def _sources() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py")}


def test_only_the_repository_writes_the_three_tables_and_nothing_here_writes_the_job_or_the_journal() -> None:
    write = re.compile(r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+(\w+)", re.IGNORECASE)
    allowed = {"comparison_ai_pair_question", "comparison_ai_pair_answer", "comparison_ai_link"}
    for name, source in _sources().items():
        for _verb, table in write.findall(re.sub(r'""".*?"""', "", source, flags=re.DOTALL)):
            if table.lower() in allowed:
                assert name == "repository.py", f"{name} writes {table}"
            else:
                pytest.fail(f"{name} writes {table}: the job is the core's, the journal and the queue are the wrapper's")


def test_no_module_calls_a_provider_or_a_transport_by_itself() -> None:
    """The one door to a model is the spend wrapper: nothing here imports a client, an HTTP library or a provider adapter."""
    forbidden = re.compile(r"^\s*(import|from)\s+(httpx|requests|anthropic|openai|urllib3|socket|boto3|botocore)\b", re.MULTILINE)
    for name, source in _sources().items():
        assert forbidden.search(source) is None, name
    assert "ComparisonModelCaller" in (PACKAGE / "handler.py").read_text(encoding="utf-8")
    assert ".complete(" not in "".join(_sources().values()), "an adapter is only ever called by the wrapper"


def test_the_package_reaches_other_contexts_only_through_their_public_surfaces() -> None:
    contexts = {"analysis": "public", "executors": "public", "storage": "public", "ingest": "public"}
    pattern = re.compile(r"^\s*from\s+auditmanager\.(\w+)(?:\.(\w+))?", re.MULTILINE)
    for name, source in _sources().items():
        for context, sub in pattern.findall(source):
            if context in contexts:
                assert sub == contexts[context], f"{name} reaches into {context}.{sub}"
            else:
                assert context in {"comparison", "shared"}, f"{name} imports {context}"


# -- the module flag first -----------------------------------------------------------------------------------------------------------


def _first_statement(function: ast.FunctionDef) -> ast.stmt:
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body[0]


def _is_gate(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Attribute)
        and statement.value.func.attr == "_require_versions_module"
    )


@pytest.mark.parametrize(("path", "class_name", "skip"), [
    (SRC / "bootstrap/adapters.py", "ComparisonAiPairAdapter", {"__init__", "_consent", "_roles"}),
    (PACKAGE / "service.py", "ComparisonAiPairService", {"__init__", "jobs", "method", "_require_versions_module", "_scope", "_command"}),
])
def test_the_module_flag_is_the_first_statement_of_every_operation(path: Path, class_name: str, skip: set[str]) -> None:
    """ADR-0025 decision 23: ``_require_versions_module()`` precedes any read, write or model call."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == class_name)
    operations = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name not in skip]
    assert len(operations) == 7, [op.name for op in operations]
    for operation in operations:
        assert _is_gate(_first_statement(operation)), f"{class_name}.{operation.name} does not begin with the module flag"


def test_the_adapter_carries_the_seven_operations_of_the_port() -> None:
    from auditmanager.api.routers.ports import ComparisonAiPairPort
    from auditmanager.bootstrap.adapters import ComparisonAiPairAdapter

    names = {"estimate_pair_check", "start_pair_check", "get_pair_check", "pause_pair_check", "resume_pair_check", "cancel_pair_check", "list_pair_hints"}
    assert all(callable(getattr(ComparisonAiPairAdapter, name)) for name in names)
    assert names <= {n for n in dir(ComparisonAiPairPort) if not n.startswith("_")}
