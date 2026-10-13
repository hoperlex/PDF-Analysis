"""The portal's recognised text is never an input of analysis (`R-117`, `W55B-RECOGNISED-01`).

Container-free. Two guards, each over an authority outside the package under test:

* the source tree: no module of ``auditmanager.analysis.text`` -- the prompt path, the only
  code that sends text to a model -- imports ``auditmanager.analysis.recognised``, directly,
  relatively or by a literal dynamic import;
* the frozen stage registry: no stage but ``source_preparation`` declares the markdown, and no
  stage at all declares ``prepared.recognised_text``, as an input.

The text-layer half of the guarantee (the layer of a bundle is byte for byte the layer of its
bare PDF) is in ``test_source_preparation_bundle.py``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
TEXT_PACKAGE = REPOSITORY_ROOT / "src" / "auditmanager" / "analysis" / "text"
REGISTRY = REPOSITORY_ROOT / "contracts" / "analysis" / "v1" / "stage-registry.json"
FORBIDDEN = "auditmanager.analysis.recognised"


def _imports(path: Path, root: Path) -> list[str]:
    """Every module ``path`` imports, relative imports resolved, literal dynamic ones included.

    ``root`` is the directory that is the package ``auditmanager.analysis.text``.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = "auditmanager.analysis.text"
    relative_to = path.relative_to(root).with_suffix("")
    parts = [*package.split("."), *relative_to.parts[:-1]]
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = parts[: len(parts) - node.level + 1]
                module = ".".join([*base, *(node.module.split(".") if node.module else [])])
            else:
                module = node.module or ""
            found.append(module)
            found.extend(f"{module}.{alias.name}" for alias in node.names)
        elif (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and (
                (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
                or (isinstance(node.func, ast.Name) and node.func.id in {"import_module", "__import__"})
            )
        ):
            found.append(node.args[0].value)
    return found


def _offenders(root: Path) -> list[str]:
    return [
        f"{path.relative_to(root)}: {name}"
        for path in sorted(root.rglob("*.py"))
        for name in _imports(path, root)
        if name == FORBIDDEN or name.startswith(FORBIDDEN + ".")
    ]


def test_the_prompt_path_imports_nothing_from_the_recognised_package() -> None:
    modules = sorted(TEXT_PACKAGE.rglob("*.py"))
    assert len(modules) >= 15, "the scan must reach the whole text package"
    assert _offenders(TEXT_PACKAGE) == []


def test_the_scan_sees_each_way_a_module_could_import_the_package(tmp_path: Path) -> None:
    """The guard can fail: three planted modules, three offenders, and a clean one passes."""
    planted = tmp_path / "text"
    planted.mkdir()
    (planted / "direct.py").write_text("import auditmanager.analysis.recognised.flags\n")
    (planted / "relative.py").write_text("from ..recognised import flags_for\n")
    (planted / "dynamic.py").write_text(
        "import importlib\nimportlib.import_module('auditmanager.analysis.recognised')\n"
    )
    (planted / "clean.py").write_text("from auditmanager.analysis.ports import artifacts\n")

    offenders = {line.split(": ")[0] for line in _offenders(planted)}
    assert offenders == {"direct.py", "dynamic.py", "relative.py"}


def test_no_stage_but_source_preparation_reads_the_portal_markdown_or_its_artifact() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    readers: dict[str, set[str]] = {}
    for stage in registry["stages"]:
        for declared in stage.get("required_inputs", ()):
            readers.setdefault(declared["role"], set()).add(stage["stage_id"])

    assert readers.get("source.markdown") == {"source_preparation"}
    assert "prepared.recognised_text" not in readers
    assert "text_analysis" not in readers.get("source.structured_companion", set())
