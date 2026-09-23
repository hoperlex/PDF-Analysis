"""`D-74`. A router calling a method one implementation lacks is an ``AttributeError``.

``AttributeError`` inside a handler is a ``500`` with no catalog code, and it appears only
on the wiring that is missing the method -- so a port method added for the shipped adapter
and forgotten on a suite's stand-in is green everywhere except the one suite that drives it,
and sometimes green there too because nothing drives that operation.

``test_router_answers.py`` already asserts that every **shipped** adapter accepts every
parameter its port declares. That is the other half of the same rule and it is narrower in
two ways this module widens:

* it checks parameters, not the existence of the method;
* it checks ``auditmanager.bootstrap.adapters`` and nothing else, while the wirings that
  actually reach a router are spread over the tree.

**The set of implementations is derived from the tree, not written down here.** Every
``build_router(...)`` call in ``src/`` and ``tests/`` is found by parsing, the class behind
each port argument is resolved, and every one of them must carry the whole protocol. A list
in this file would have stopped covering whatever is wired after it was written -- which is
`D-74`'s own shape, one level up.

**An argument this module cannot resolve is a failure, not a skip.** A checker that cannot
read a claim has not verified it, and a silent skip here would be indistinguishable from a
wiring that passes.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any

import pytest

from auditmanager.api.routers import ports as port_module

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The keyword each port is passed under, and the protocol it must satisfy. Read off
#: ``build_router``'s own signature below, so a seventh port cannot be missed here.
PORT_FOR_ARGUMENT = {
    "projects": "ProjectPort",
    "documents": "DocumentPort",
    "runs": "RunPort",
    "findings": "FindingPort",
    "decisions": "DecisionPort",
    "exports": "CsvExportPort",
    "credentials": "CredentialPort",
}


def _python_files() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for root in ("src", "tests"):
        found.extend(sorted((REPOSITORY_ROOT / root).rglob("*.py")))
    return found


def _parsed() -> dict[pathlib.Path, ast.Module]:
    trees: dict[pathlib.Path, ast.Module] = {}
    for path in _python_files():
        try:
            trees[path] = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - none in this tree
            continue
    return trees


def _class_definitions(
    trees: dict[pathlib.Path, ast.Module],
) -> dict[str, list[tuple[str, ast.ClassDef]]]:
    """Every class in the tree, by name, **with every file that defines it**.

    Not one entry per name. ``_Unused`` is defined twice in this tree, in two suites that
    mean two different things by it, and a name-keyed map silently answered with whichever
    file sorted first -- a guard reading the wrong class is not a guard. So the index keeps
    both and :func:`_locate` resolves against the file that did the wiring.
    """
    found: dict[str, list[tuple[str, ast.ClassDef]]] = {}
    for path, tree in trees.items():
        where = str(path.relative_to(REPOSITORY_ROOT))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                found.setdefault(node.name, []).append((where, node))
    return found


def _locate(
    name: str, where: str, classes: dict[str, list[tuple[str, ast.ClassDef]]]
) -> ast.ClassDef | None:
    """The class ``name`` means in ``where``: defined there, or uniquely in the tree.

    ``None`` when the name is defined nowhere, or in several files and none of them is
    this one -- both of which the caller reports rather than guessing past.
    """
    candidates = classes.get(name, [])
    local = [definition for path, definition in candidates if path == where]
    if local:
        return local[0]
    if len(candidates) == 1:
        return candidates[0][1]
    return None


def _construction_name(node: ast.expr) -> str | None:
    """``SomeAdapter(...)`` -> ``"SomeAdapter"``; anything else -> ``None``."""
    if isinstance(node, ast.Call):
        return getattr(node.func, "id", None) or getattr(node.func, "attr", None)
    return None


def _resolve(tree: ast.Module, node: ast.expr) -> str | None | Any:
    """The class behind one port argument.

    Returns the class name, ``None`` for a literal ``None`` (a port this wiring never
    drives), or the sentinel :data:`UNRESOLVED`.
    """
    if isinstance(node, ast.Constant) and node.value is None:
        return None
    direct = _construction_name(node)
    if direct is not None:
        return direct
    if isinstance(node, ast.Name):
        # `runs=run_port`, with the construction a few lines above it.
        for other in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(other, ast.Assign):
                targets = list(other.targets)
                value = other.value
            elif isinstance(other, ast.AnnAssign) and other.value is not None:
                targets = [other.target]
                value = other.value
            else:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id == node.id:
                    resolved = _construction_name(value)
                    if resolved is not None:
                        return resolved
    return UNRESOLVED


UNRESOLVED = object()


def _wirings() -> list[tuple[str, int, str, str | None | Any]]:
    """``(file, line, port_argument, class)`` for every ``build_router`` call in the tree."""
    rows: list[tuple[str, int, str, str | None | Any]] = []
    for path, tree in _parsed().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "build_router":
                continue
            where = str(path.relative_to(REPOSITORY_ROOT))
            for keyword in node.keywords:
                if keyword.arg in PORT_FOR_ARGUMENT:
                    rows.append(
                        (where, node.lineno, keyword.arg, _resolve(tree, keyword.value))
                    )
    return rows


def _declared(port_name: str) -> frozenset[str]:
    port = getattr(port_module, port_name)
    return frozenset(
        name
        for name in dir(port)
        if not name.startswith("_") and callable(getattr(port, name, None))
    )


def _implemented(
    definition: ast.ClassDef,
    where: str,
    classes: dict[str, list[tuple[str, ast.ClassDef]]],
    seen: set[str],
) -> frozenset[str] | None:
    """The method names this class answers to, or ``None`` when it answers to anything.

    ``None`` is the ``__getattr__`` case: a stand-in that raises on every attribute cannot
    be caught out by a missing method, because it has none and never had.
    """
    names: set[str] = set()
    for node in definition.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "__getattr__":
                return None
            names.add(node.name)
    for base in definition.bases:
        base_name = getattr(base, "id", None) or getattr(base, "attr", None)
        if not isinstance(base_name, str) or base_name in seen:
            continue
        found = _locate(base_name, where, classes)
        if found is None:
            continue
        seen.add(base_name)
        inherited = _implemented(found, where, classes, seen)
        if inherited is None:
            return None
        names |= inherited
    return frozenset(names)


def test_build_router_still_takes_the_ports_this_module_names() -> None:
    """The control. A port added to ``build_router`` and not to the map above would
    otherwise leave this whole guard silently narrower than the surface it guards."""
    import inspect

    from auditmanager.api.routers import build_router

    taken = {
        name
        for name, parameter in inspect.signature(build_router).parameters.items()
        if parameter.kind is not parameter.VAR_KEYWORD
    }
    assert taken == set(PORT_FOR_ARGUMENT), (
        f"`build_router` takes {sorted(taken)}; this guard knows {sorted(PORT_FOR_ARGUMENT)}. "
        "A port it does not know is a port it does not check."
    )


def test_the_tree_really_wires_these_ports() -> None:
    """A parser that found nothing would make every assertion below vacuously true."""
    rows = _wirings()
    files = {row[0] for row in rows}
    assert len(rows) >= 40, f"only {len(rows)} port arguments found across {len(files)} files"
    assert any(row[0].startswith("src/") for row in rows), rows


def test_no_port_argument_is_beyond_this_guard_s_reading() -> None:
    """An expression this guard cannot resolve is reported, never skipped.

    Classifying a claim the checker cannot read is not verifying it, and a skip here would
    look exactly like a wiring that passed.
    """
    unreadable = [
        (where, line, argument)
        for where, line, argument, resolved in _wirings()
        if resolved is UNRESOLVED
    ]
    assert unreadable == [], (
        "this guard cannot tell which class these port arguments name, so it cannot check "
        f"them: {unreadable}. Construct the adapter in the call, or bind it to a local name "
        "in the same module."
    )


@pytest.mark.parametrize("argument", sorted(PORT_FOR_ARGUMENT))
def test_every_wired_implementation_carries_the_whole_port(argument: str) -> None:
    """The rule `D-74` is a row about: a method the router calls, on every implementation."""
    classes = _class_definitions(_parsed())
    required = _declared(PORT_FOR_ARGUMENT[argument])
    assert required, f"{PORT_FOR_ARGUMENT[argument]} declares no methods"

    problems: list[str] = []
    for where, line, wired, resolved in _wirings():
        if wired != argument or resolved is None:
            continue
        definition = _locate(resolved, where, classes)
        if definition is None:
            problems.append(
                f"{where}:{line} wires {resolved}, which this guard cannot find in that "
                "file and cannot name uniquely in the tree"
            )
            continue
        answered = _implemented(definition, where, classes, {resolved})
        if answered is None:
            continue
        missing = sorted(required - answered)
        if missing:
            problems.append(f"{where}:{line} {resolved} lacks {missing}")
    assert problems == [], (
        f"an implementation wired as `{argument}` does not carry every method "
        f"{PORT_FOR_ARGUMENT[argument]} declares. A router calling one of these gets an "
        f"AttributeError and the caller gets a 500: {problems}"
    )
