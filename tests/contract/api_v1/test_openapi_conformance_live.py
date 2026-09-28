"""The conformance gate, wired to the served document. `X-1`.

`W13-CONF.md` §11 wrote this file down and did not write it:

    "The wiring is one file and is deliberately not written. When `W13-API` lands, the
    remaining step is a new `tests/contract/api_v1/test_openapi_conformance_live.py`
    holding `differences(surface(json.loads(CONTRACT_PATH.read_text())),
    surface(app.openapi()))` and asserting it empty."

`test_openapi_conformance.py` beside this file proves the comparison **engine** cannot be
fooled by anything FastAPI itself introduces (86 planted-difference cases against a
miniature, hand-built app). `test_served_document_and_health_plane.py`
(`tests/integration/api/`) proves the wired application and `create_documentation_app()`
serve byte-identical documents. Neither ever calls `differences()` with the frozen contract
on one side and a real served document on the other — `grep -rn 'differences(' tests` found
no such call anywhere before this file. `ALPHA_ROADMAP.md:306` specifies the gate as
*"`app.openapi()` against the frozen document"*, and `W13_CLOSURE.md` reported *"0
differences"* once, at wave 13, and never again. FastAPI validates **requests** from the
same Pydantic models it generates the served document from, so a model that drifts from
the contract (a field made required that the contract calls optional, a bound tightened)
refuses requests the contract and the generated client both consider valid — and until
this file, no test in `make gate` could see that class of drift, because none compared the
two documents at all.

This is that file. `create_documentation_app()` is used rather than the wired app: it needs
no database, object store or credential (`api/app.py`'s own docstring), so this comparison
runs the same way `test_openapi_conformance.py` does, with nothing behind any of the six
ports, and `test_the_documented_and_the_wired_app_agree`
(`tests/integration/api/test_served_document_and_health_plane.py`) is what already proves
that document is the one being served.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from auditmanager.api.app import create_documentation_app

_HERE = Path(__file__).resolve().parent
_REPOSITORY_ROOT = _HERE.parents[2]

#: The frozen document is the authority, read from disk on every run — never cached at
#: import, and never derived from the served document itself (`OPERATING_CONSTRAINTS.md`
#: §12): a reseal changes what is on disk while this session is open.
CONTRACT_PATH = _REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"


def _load_engine() -> Any:
    """Import the comparison engine by path, exactly as `test_openapi_conformance.py`
    does — a test module cannot `import` a sibling by bare name under
    `--import-mode=importlib`, and is explicitly forbidden from a `sys.path` hack around
    it. The path is anchored on `__file__`, so a mutation copy of the tree loads that
    copy's engine and not this one's.
    """
    spec = importlib.util.spec_from_file_location(
        "w13conf_openapi_conformance_live", _HERE / "openapi_conformance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conformance = _load_engine()
differences = conformance.differences
surface = conformance.surface


def test_the_served_document_conforms_to_the_frozen_contract() -> None:
    """`differences(surface(frozen), surface(served))` is empty.

    This is the exact call `W13-CONF.md` §11 specified and handed over as the last step of
    wave 13. `served` is `create_documentation_app().openapi()`, which
    `test_the_documented_and_the_wired_app_agree` (`tests/integration/api/
    test_served_document_and_health_plane.py`) proves is byte-identical to what the wired
    application serves. `differences()` reports a semantic disagreement at its exact
    dotted location; a passing gate is the two documents agreeing on everything this
    module's seven normalizations do not erase.
    """
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    served = create_documentation_app().openapi()

    found = differences(surface(contract), surface(served))
    assert found == [], (
        "the served document disagrees with the frozen contract -- this is the "
        "conformance gate `ALPHA_ROADMAP.md:306` specifies and `W13-CONF.md` section 11 "
        "handed over as the one file left to write:\n" + "\n".join(found)
    )
