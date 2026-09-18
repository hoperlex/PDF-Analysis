"""`AUDITMANAGER_API_TOKEN` has a configuration channel, and a missing one refuses early.

`W13_CLOSURE.md` section 7 named this the load-bearing thing wave 13 owed wave 14:

    **`AUDITMANAGER_API_TOKEN` has no configuration channel.** `T-6` reads it fail-closed
    from the environ `create_app` already carries, but `.env.example` and `AppSettings`
    were outside stage 2's scope. **A deployment that forgets it gets a surface that
    refuses everything.**

The failure direction is right -- unconfigured means refused, not open -- and it is silent
from the outside. `/healthz` and `/readyz` stay green because `T-3` puts them on a second
port outside the authorized surface, so a browser sees twelve operations answering 401 and
reads that as a broken product rather than an unconfigured one.

So `W14-PKG` made it **required at construction**, which is the contract
``bootstrap/settings.py`` opens with and the one ``ANTHROPIC_API_KEY`` is already held to:
*a missing or malformed dependency fails at construction, not at first use.*

**Where it is NOT configured, and why that is not an omission.** Not in ``.env``. The
Makefile parses that file against a strict allowlist of exactly the fifteen names FF-01
section 3 freezes and refuses every other name with an explicit error -- so adding it there
would break `make gate` rather than configure anything. ``settings.py`` records the same
reasoning for ``AUDITMANAGER_PROVIDER_MODE``. Its channel is the deployment environment
beside the compose file, and the assertions below are over that file's bytes.

Every expected value here is a **literal**. `OPERATING_CONSTRAINTS.md` section 12: a value
read from the thing it is checking cannot tell you the thing changed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from auditmanager.api.composition import ConfigurationError, build_application
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.bootstrap.settings import API_TOKEN_ENV, load

ROOT = Path(__file__).resolve().parents[3]

#: The literal a deployment sets. Spelled here, not imported from either module, because
#: this file's job is to catch the day one of them changes.
TOKEN_NAME = "AUDITMANAGER_API_TOKEN"

#: The fifteen FF-01 section 3 names, written out. The point of the list is that
#: :data:`TOKEN_NAME` is not in it.
FROZEN_ENV_NAMES = (
    "FOUNDATION_INSTANCE",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "DATABASE_URL",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "S3_ENDPOINT_URL",
    "S3_API_PORT",
    "S3_CONSOLE_PORT",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
)

DEPLOY_ENV_EXAMPLE = ROOT / "infra/deploy/env/alpha.env.example"
COMPOSE = ROOT / "infra/deploy/compose.server.yml"

_A_TOKEN = "a-token-that-authorizes-nothing"


def _base_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()}
    assert env.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    env[TOKEN_NAME] = _A_TOKEN
    return env


class TestItIsTheSameNameEverywhere:
    def test_the_two_modules_spell_it_the_same(self) -> None:
        """``api/security.py`` reads it and ``bootstrap/settings.py`` requires it.

        They cannot import from each other -- ``bootstrap`` sits below ``api`` and must not
        depend upward -- so the name is written twice. This is the assertion that keeps the
        two copies one name.
        """
        assert API_TOKEN_VARIABLE == TOKEN_NAME
        assert API_TOKEN_ENV == TOKEN_NAME


class TestAMissingTokenRefusesAtConstruction:
    def test_building_without_it_raises_and_names_it(self) -> None:
        """Not a 401 on the first request. No application object at all."""
        env = _base_env()
        env.pop(TOKEN_NAME, None)
        with pytest.raises(ConfigurationError) as caught:
            build_application(environ=env)
        assert TOKEN_NAME in str(caught.value), (
            "the refusal does not name the variable, so an operator cannot act on it"
        )

    def test_an_empty_token_is_the_same_as_an_absent_one(self) -> None:
        """A deployment that sets the key and leaves the value blank is unconfigured.

        `security.py` already refuses an empty expected token before comparing, so without
        this the two halves could disagree about what "configured" means.
        """
        with pytest.raises(ConfigurationError, match=TOKEN_NAME):
            build_application(environ=_base_env() | {TOKEN_NAME: "   "})

    def test_the_case_discriminates(self) -> None:
        """The same environment WITH the token builds.

        Without this, the two refusals above would pass just as happily if the composition
        root were broken for some entirely different reason.
        """
        application = build_application(environ=_base_env())
        assert application.settings.api_token == _A_TOKEN
        assert len(application.router.routes) == 15

    def test_settings_alone_refuses_too(self) -> None:
        """The refusal is in ``load``, so anything that resolves settings inherits it."""
        env = _base_env()
        env.pop(TOKEN_NAME, None)
        with pytest.raises(ConfigurationError, match=TOKEN_NAME):
            load(env)

    def test_no_asgi_application_can_be_built_without_it(self) -> None:
        """There is nothing to send a first request TO.

        The distinction this whole module exists for: a process that starts and answers 401
        to everything has accepted a deployment nobody can use, and the operator learns it
        from a browser. This one exits before it binds a socket.
        """
        from auditmanager.api.app import create_asgi_app

        env = _base_env()
        env.pop(TOKEN_NAME, None)
        with pytest.raises(ConfigurationError, match=TOKEN_NAME):
            create_asgi_app(environ=env)


class TestTheChannelIsTheDeploymentEnvironmentAndNotDotEnv:
    def test_the_makefile_allowlist_is_the_fifteen_and_excludes_the_token(self) -> None:
        """Read from the Makefile's bytes, compared against the literal tuple above."""
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        declared = re.search(
            r"^FROZEN_ENV_NAMES=\"(.*?)\"$", makefile, re.MULTILINE | re.DOTALL
        )
        assert declared is not None, "the Makefile no longer declares FROZEN_ENV_NAMES"
        names = tuple(declared.group(1).replace("\\\n", " ").split())
        assert names == FROZEN_ENV_NAMES
        assert len(names) == 15
        assert TOKEN_NAME not in names, (
            "the token is now a frozen .env name; this test and the deployment "
            "environment both need rewriting, and that is an FF-01 section 3 change"
        )

    def test_dot_env_example_does_not_assign_it(self) -> None:
        """Putting it there would break `make`, not configure anything."""
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
            assert not line.strip().startswith(f"{TOKEN_NAME}="), line

    def test_the_deployment_environment_example_does_assign_it(self) -> None:
        text = DEPLOY_ENV_EXAMPLE.read_text(encoding="utf-8")
        assignments = [
            line for line in text.splitlines() if line.startswith(f"{TOKEN_NAME}=")
        ]
        assert len(assignments) == 1, assignments
        _, _, value = assignments[0].partition("=")
        assert value.strip(), "the example assigns an empty token, which is unconfigured"

    def test_compose_refuses_to_render_without_it(self) -> None:
        """A second, independent refusal one layer out.

        `settings.load` stops a container that was started without the token. This stops
        the stack being started at all -- compose's `:?` fails substitution before any
        image runs. Two guards because the failure is silent from outside and cheap here.
        """
        text = COMPOSE.read_text(encoding="utf-8")
        assert f"${{{TOKEN_NAME}:?" in text, (
            "compose no longer refuses an unset token; a stack could come up unconfigured"
        )
