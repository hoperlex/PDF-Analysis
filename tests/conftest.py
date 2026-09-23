"""Suite-wide isolation from ambient provider configuration.

Found by configuring a real LLM proxy in the developer's shell: twenty-five tests turned red
because they read `AUDITMANAGER_PROVIDER_MODE` from the process environment and got `proxy`
instead of the recorded default. The tests were right about their own logic and wrong to
depend on a variable nobody set for them.

The sharper version of the same problem is the one that did **not** happen here: a developer
with a live credential exported would have had the suite make real, paid model calls. A test
run must never depend on what happens to be in a shell, and must never be able to spend money
because of it.

So every provider-selecting variable is removed for the whole session. A test that wants a
specific mode sets it explicitly, which is the only way the intent is visible.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# ``tests/support/accounts.py`` is loaded **by explicit path** and registered under a
# session-unique name, the mechanism ``tests/integration/api/conftest.py`` already uses for
# the driver beside it: with ``--import-mode=importlib`` a bare ``from support.accounts
# import ...`` does not resolve, and adding to ``sys.path`` is what ``pyproject.toml``'s
# pytest section calls working around its contract rather than extending it. It is
# registered *here*, in the root conftest, because the suites that need it are spread across
# five directories -- ``e2e``, ``characterization``, ``integration/composition``,
# ``integration/ingest`` and ``integration/p02_journey`` -- and a per-directory loader would
# be five copies of this paragraph. The root conftest is imported before any of them, so the
# name is in ``sys.modules`` by the time a test module says ``from am_test_accounts import
# ...``.
#
# Why they need it at all: since `W39-REVOKE` a credential is refused unless the account it
# names exists and still accepts that credential's generation, so a suite that minted one
# for an invented identity is presenting something the seam is right to reject. See that
# module's own note.
_ACCOUNTS_NAME = "am_test_accounts"
_ACCOUNTS_PATH = Path(__file__).resolve().parent / "support" / "accounts.py"
if _ACCOUNTS_NAME not in sys.modules:
    _accounts_spec = importlib.util.spec_from_file_location(_ACCOUNTS_NAME, _ACCOUNTS_PATH)
    assert _accounts_spec is not None and _accounts_spec.loader is not None
    _accounts = importlib.util.module_from_spec(_accounts_spec)
    sys.modules[_ACCOUNTS_NAME] = _accounts
    _accounts_spec.loader.exec_module(_accounts)

#: Everything that selects a provider, a credential or a model. `DATABASE_URL` and the `S3_*`
#: names are deliberately absent: those address this lane's own disposable services, the
#: suites genuinely need them, and no test can spend money through them.
_PROVIDER_SELECTING = (
    "AUDITMANAGER_PROVIDER_MODE",
    "AUDITMANAGER_MODEL_ID",
    "AUDITMANAGER_RUN_COST_CEILING_USD",
    "ANTHROPIC_API_KEY",
    "PROXY_LLM_BASE_URL",
    "PROXY_LLM_TOKEN",
    "PROXY_LLM_MODEL",
)


@pytest.fixture(scope="session", autouse=True)
def _no_ambient_provider_configuration() -> Iterator[None]:
    removed = {name: os.environ.pop(name) for name in _PROVIDER_SELECTING if name in os.environ}
    try:
        yield
    finally:
        os.environ.update(removed)


def test_the_isolation_is_in_force() -> None:
    """Asserts the fixture actually ran, rather than trusting that autouse means applied.

    Without this, a rename or a scope change would silently stop protecting the suite and
    nothing would say so until a run made a paid call.
    """
    leaked = [name for name in _PROVIDER_SELECTING if name in os.environ]
    assert leaked == [], f"ambient provider configuration reached the suite: {leaked}"
