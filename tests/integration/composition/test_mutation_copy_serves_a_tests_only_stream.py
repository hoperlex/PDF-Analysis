"""`make mutation-copy` carries the tests, and carries them as copies.

`DEBT_REGISTER.md` `D-10`: the target copied `src/` and linked `contracts/`, `docs/`,
`fixtures/`, `db/` and `tools/`, and carried `tests/` not at all. A stream whose
deliverable **is** a test module -- an assertion engine, a comparison harness -- therefore
could not mutate its own code with it. `W13-CONF` hit exactly that and hand-built a scratch
tree to prove its engine could fail; three of the four waves before it had a tests-only
stream.

**Why this is a test and not only a probe.** `mutation_copy` and `MUTATION_COPY_PROBE` are
each other's guard: the recipe copies the paths and the probe refuses a copy that is
missing one or that reaches outside itself. But `make mutation-copy` is not part of
`make gate`, so deleting the `cp -a tests` line and the probe branch together would leave
nothing red anywhere. This file is what notices.

**`tests/` and `pyproject.toml` must be copies, never symlinks**, and that is the load-
bearing half. `mutation_copy` refuses a destination inside the worktree with the words *"the
whole point is that no tracked file is ever edited to mutate"* -- and a symlinked `tests/`
would hand a stream exactly what that guard refuses, by a different route: editing "the
copy's" test file would edit the tracked one. The probe checks it by resolving the path and
asking whether it still lands under the copy, which a link to the worktree does not.

Every expected value here is a **literal**, per `OPERATING_CONSTRAINTS.md` section 12: a
value read from the thing it is checking cannot tell you the thing changed.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

#: Read once. Every assertion below is over these bytes.
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")

#: Copied, so a mutation inside one takes and no tracked file is touched.
COPIED = ("src", "tests", "pyproject.toml")

#: Linked unless `FULL=1`, and the recipe says so out loud because a symlinked directory
#: silently turns a mutation into a no-op, and a no-op mutation and a covered rule produce
#: identical evidence.
LINKED_UNLESS_FULL = ("contracts", "docs", "fixtures", "db", "tools")


def _mutation_copy_body() -> str:
    match = re.search(r"\nmutation_copy\(\) \{\n(.*?)\n\}\n", MAKEFILE, re.S)
    assert match is not None, "the Makefile no longer defines mutation_copy()"
    return match.group(1)


def _probe_body() -> str:
    match = re.search(r"\ndefine MUTATION_COPY_PROBE\n(.*?)\nendef\n", MAKEFILE, re.S)
    assert match is not None, "the Makefile no longer defines MUTATION_COPY_PROBE"
    return match.group(1)


class TestTheRecipeCarriesWhatAMutationNeeds:
    """Over `mutation_copy()`'s own bytes."""

    def test_every_copied_path_is_copied_not_linked(self) -> None:
        body = _mutation_copy_body()
        for name in COPIED:
            assert f'cp -a {name} "$$dest/{name}"' in body, (
                f"{name} is no longer copied into the mutation copy. A stream whose "
                f"deliverable is a {name} file cannot mutate it (D-10)."
            )
            assert f'ln -s "$$PWD/{name}"' not in body, (
                f"{name} is symlinked into the mutation copy. Editing it there would "
                f"edit the TRACKED tree, which is the one thing this target forbids."
            )

    def test_the_linked_set_is_still_the_linked_set(self) -> None:
        """The copied set grew; the linked set did not, and nothing moved between them."""
        body = _mutation_copy_body()
        declared = re.search(r"for name in ([a-z ]+); do", body)
        assert declared is not None, "the Makefile no longer loops over the linked paths"
        assert tuple(declared.group(1).split()) == LINKED_UNLESS_FULL

    def test_the_venv_is_reachable_by_repository_root_path(self) -> None:
        """`tests/integration/db/conftest.py` shells out to `$ROOT/.venv/bin/python`.

        Once `tests/` is copied that root is the copy, so without this link the db lane
        fails on a missing interpreter rather than on anything a mutation did -- a
        manufactured red, which is what wave 10 found the old recipe producing.
        """
        assert 'ln -s "$$PWD/.venv" "$$dest/.venv"' in _mutation_copy_body()


class TestTheProbeRefusesACopyThatWouldLie:
    """Over `MUTATION_COPY_PROBE`'s own bytes.

    Each of these branches was driven to red by hand when it was written -- a copy with
    no `tests/`, one whose `tests/` is a link to the worktree, one with no
    `pyproject.toml`, one with no reachable `.venv` -- and then driven green again on a
    restored copy, which is the control that proves the instrument was not failing for an
    unrelated reason. These assertions are what stops those branches being deleted.
    """

    def test_the_probe_requires_the_copied_paths(self) -> None:
        body = _probe_body()
        for name in ("tests", "pyproject.toml"):
            assert f'"{name}"' in body, f"the probe no longer looks for {name}"

    def test_the_probe_refuses_a_path_that_resolves_outside_the_copy(self) -> None:
        """Identity, not policy: a link to the worktree resolves outside `dest`."""
        assert "p.resolve().parents" in _probe_body()
        assert "outside the copy" in _probe_body()

    def test_the_probe_requires_a_reachable_interpreter(self) -> None:
        assert '".venv" / "bin" / "python"' in _probe_body()


class TestTheRecipeDoesNotCarryTheFlagThatNeverDidAnything:
    """`pytest-randomly` is not installed and is not in `uv.lock`.

    The recipe told four waves to pass `-p no:randomly`, and the integrator leaned on that
    plugin four times to explain a flake it was not causing. `W13-ORD` measured the
    difference over 191 journeys and found two samples of a 5.6% coin. The flag was a
    no-op the whole time.
    """

    def test_the_recipe_does_not_suggest_a_plugin_that_is_absent(self) -> None:
        """Comments may *name* the flag -- one does, to say why it is not there.

        What is forbidden is a line that hands it to a reader as something to run. So
        this reads every line that is not a comment, which is the distinction between
        explaining the mistake and repeating it.
        """
        offenders = [
            line
            for line in MAKEFILE.splitlines()
            if "no:randomly" in line and not line.strip().startswith("#")
        ]
        assert offenders == [], (
            "`-p no:randomly` is suggested by the Makefile again. The plugin is not "
            "installed; the flag does nothing. See W13-ORD and W13_CLOSURE.md section 4."
            f"\n  {offenders}"
        )

    def test_the_plugin_really_is_absent(self) -> None:
        """The discriminator. Without it the assertion above would pass just as happily
        on a tree where the plugin *is* installed and the flag is meaningful."""
        lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
        assert "pytest-randomly" not in lock
