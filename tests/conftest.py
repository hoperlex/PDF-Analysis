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

import os
from collections.abc import Iterator

import pytest

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
