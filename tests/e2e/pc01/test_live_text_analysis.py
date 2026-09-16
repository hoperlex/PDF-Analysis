"""Criteria 4 and 5 against a **live** ``text_analysis``, through the router.

This module is opt-in and skipped by default, because running it spends money. That is a
deliberate asymmetry with the rest of the suite: the root ``tests/conftest.py`` strips
every provider-selecting variable for the whole session so a paid call cannot happen by
accident, and the way to make one happen is to say so here, explicitly, in the test's own
body. Nothing is inherited from a shell.

Run it with::

    C2_PC01_LIVE=1 .venv/bin/pytest tests/e2e/pc01/test_live_text_analysis.py -s

The credential is read from ``.env.provider`` by path -- ``C2_PC01_PROVIDER_ENV`` names it,
or it is found beside the checkout. Sourcing it into the shell would not work and should
not: the root conftest strips the provider names for the whole session, and that guard is
the reason this suite cannot spend by accident.

``PROXY_LLM_MODEL`` is pinned to ``anthropic/claude-opus-5`` here rather than left to the
proxy's default. The proxy's default is a small fast model and the PC-01 prompt was
written against Opus, so a run on the default would measure something other than what
criterion 5 asks -- and it would look like a valid measurement.

**Never fabricate a transcript.** If the call fails, this module fails with the provider's
own refusal and the cost of the attempt. It has no recorded fallback, on purpose: a live
test that quietly fell back to a fixture would be the exact "fake success" criterion 10
forbids, one level up.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_DRIVER_NAME = "c2_pc01_driver"


def _load_driver() -> Any:
    existing = sys.modules.get(_DRIVER_NAME)
    if existing is not None:
        return existing
    path = Path(__file__).resolve().with_name("driver.py")
    spec = importlib.util.spec_from_file_location(_DRIVER_NAME, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[_DRIVER_NAME] = module
    spec.loader.exec_module(module)
    return module


driver = _load_driver()

#: The provider-selecting names this module sets for itself. They are named here rather
#: than read from a shell so that the diff shows exactly what a live run is configured to
#: do, and so that a reviewer can see the model choice without running anything.
LIVE_MODE = "proxy"
LIVE_MODEL = "anthropic/claude-opus-5"

#: Criterion 5's threshold, from PROTOTYPE_PROFILE.md section 8 item 5.
REQUIRED_SEEDED_ISSUES = 2


def _main_checkout() -> Path | None:
    """The main repository checkout, from inside a linked worktree or the checkout itself.

    ``None`` when git cannot answer -- a source export with no repository, say. A missing
    credential must make this suite *skip*, never error, so every failure mode here is
    swallowed deliberately.
    """
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=driver.REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if common.returncode != 0 or not common.stdout.strip():
        return None
    return Path(common.stdout.strip()).parent


def _provider_file() -> Path | None:
    """Where the credential is, or ``None``.

    Read from a file rather than from the process environment on purpose. The root
    ``tests/conftest.py`` removes ``PROXY_LLM_BASE_URL`` and ``PROXY_LLM_TOKEN`` for the
    whole session precisely so that a sourced shell cannot make the suite spend, and that
    strip is doing its job -- a live test that read those names back out of ``os.environ``
    would either find nothing or, worse, be re-enabled the day someone reordered the
    fixture. So the credential is fetched by an explicitly named path, which is a thing a
    reviewer can see in the diff.
    """
    named = os.environ.get("C2_PC01_PROVIDER_ENV")
    candidates = [Path(named)] if named else []
    candidates.append(driver.REPOSITORY_ROOT / ".env.provider")
    # A dispatched worktree does not carry the git-ignored credential file; the checkout
    # it was created from does. Ask git where that is instead of guessing a depth:
    # `--git-common-dir` resolves to the *main* repository's `.git` from inside any linked
    # worktree, so its parent is the checkout holding the credential, whatever the worktree
    # is called and wherever it sits.
    #
    # This replaces `REPOSITORY_ROOT.parents[2]`, which assumed one layout and broke on
    # another. It happened to land on the repository root for a worktree under
    # `.claude/worktrees/`, and raised `IndexError` for one directly under `/root/` -- the
    # layout the dispatch briefs themselves prescribe. `W5-CERT` hit it from `/root/w5cert`
    # and the suite *errored* rather than skipping, so criterion 4's live step could not be
    # reproduced from a dispatched worktree at all.
    main_checkout = _main_checkout()
    if main_checkout is not None:
        candidates.append(main_checkout / ".env.provider")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    return values


def _live_configuration() -> dict[str, str]:
    """The explicit provider configuration, or the reason there is none.

    Nothing here is inherited: every value the composition root will read is named in the
    returned mapping, so what a live run is configured to do is visible without running it.
    """
    if os.environ.get("C2_PC01_LIVE") != "1":
        pytest.skip(
            "live text_analysis is opt-in: set C2_PC01_LIVE=1. Running it spends money "
            "against the OD-03 ceiling."
        )
    path = _provider_file()
    if path is None:
        pytest.skip(
            "no .env.provider was found; point C2_PC01_PROVIDER_ENV at the operator's "
            "credential file before asking for a live run"
        )
    supplied = _read_env_file(path)
    missing = [n for n in ("PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN") if not supplied.get(n)]
    if missing:
        pytest.skip(f"{path} carries no {', '.join(missing)}")
    print(f"\nlive provider configuration read from {path}")
    return {
        "AUDITMANAGER_PROVIDER_MODE": LIVE_MODE,
        "PROXY_LLM_BASE_URL": supplied["PROXY_LLM_BASE_URL"],
        "PROXY_LLM_TOKEN": supplied["PROXY_LLM_TOKEN"],
        # Pinned here, never taken from the file: the proxy's default is a small fast
        # model and this measurement is only meaningful against the one the prompt was
        # written for.
        "PROXY_LLM_MODEL": LIVE_MODEL,
    }


@pytest.fixture(scope="module")
def live_run(page_texts: tuple[str, ...]) -> dict[str, Any]:
    """One live run, driven through the router, kept for every assertion below.

    Module-scoped because it is a paid call: re-running it per test would spend four times
    to learn four properties of one answer.
    """
    configuration = _live_configuration()
    client = driver.build_client(**configuration)
    assert client.app.settings.provider_mode == LIVE_MODE
    assert client.app.settings.proxy_model == LIVE_MODEL, (
        "the run would have gone to the proxy's default model, which is not the one the "
        "PC-01 prompt was written against"
    )

    tag = driver.key("live", unique=True)
    answer = client.create_project(name=f"C2 live PC-01 {tag}", key=tag)
    assert answer.status == 201, answer.body
    project = answer.json

    answer = client.upload_document(
        project_uid=project["project_uid"],
        content=driver.BASELINE_PDF.read_bytes(),
        key=f"{tag}-upload",
    )
    assert answer.status == 201, answer.body
    version = answer.json

    answer = client.start_run(
        version_uid=version["version_uid"], key=f"{tag}-run", provider_mode="live"
    )
    if answer.status != 202:
        pytest.fail(
            "the live run did not start. Reported verbatim, with no recorded fallback and "
            f"no invented transcript: {answer.status} {answer.body!r}"
        )
    started = answer.json

    status = client.run_status(started["run_id"])
    assert status.status == 200, status.body
    findings = client.run_findings(started["run_id"])
    assert findings.status == 200, findings.body

    return {
        "client": client,
        "version": version,
        "status": status.json,
        "findings": findings.json["items"],
    }


def test_live_the_run_is_published_and_records_itself_as_live(live_run) -> None:
    """Criterion 4, live.

    ``provider_mode`` must read ``live``: a model really answered, and the proxy is the
    transport rather than a third provenance. A run that had silently fallen back to the
    recorded adapter would say ``recorded`` here, which is the assertion that makes this
    test worth running.
    """
    status = live_run["status"]
    assert status["provider_mode"] == "live", status
    assert status["state"] == "published", status
    assert status["degradation_set"] == [], status
    stages = {s["stage_id"]: s["status"] for s in status.get("stages", [])}
    assert set(stages) == {
        "document_context_build",
        "page_geometry_extraction",
        "source_preparation",
        "text_analysis",
    }, stages
    assert set(stages.values()) == {"succeeded"}, stages


def test_live_every_published_quotation_exists_on_its_declared_page(
    live_run, page_texts: tuple[str, ...]
) -> None:
    """Criterion 5, second half -- the half that is a hard gate.

    A model that invented a quotation, or attributed a real one to the wrong page, fails
    here regardless of how many issues it found. The page texts are pinned to the corpus
    manifest in the fixture, so this is measured against the corpus.
    """
    checked = 0
    for finding in live_run["findings"]:
        for item in finding["observation"]["evidence"]:
            page = item["page_number"]
            assert 1 <= page <= len(page_texts), page
            assert item["quote"] in page_texts[page - 1], (
                f"{finding['finding_uid']} quotes {item['quote']!r} as page {page}; that "
                "page's text does not contain it"
            )
            checked += 1
    assert checked >= REQUIRED_SEEDED_ISSUES, f"only {checked} quotations were published"


def test_live_at_least_two_seeded_issues_are_located(live_run, manifest) -> None:
    """Criterion 5, first half.

    A run that finds fewer than two is not a broken gate -- it is the product outcome
    ``PROTOTYPE_PROFILE.md`` risk 1 names in advance, and it redirects P04 rather than
    stopping it. It is asserted here anyway, because a silent shortfall recorded nowhere
    is not a finding either; the *report* is where the distinction is drawn.

    Matched on the pages the manifest declares rather than on free text: a run that
    published the right number of findings about the wrong pages would pass a count.
    """
    seeded = {issue["id"]: set(issue["pages"]) for issue in manifest["seeded_issues"]}
    published_pages = {
        item["page_number"]
        for finding in live_run["findings"]
        for item in finding["observation"]["evidence"]
    }
    located = sorted(k for k, pages in seeded.items() if pages & published_pages)
    print(f"\nlive run located {len(located)} of {len(seeded)} seeded issues: {located}")
    assert len(located) >= REQUIRED_SEEDED_ISSUES, (
        f"evidence pages {sorted(published_pages)} locate only {located} of {sorted(seeded)}"
    )


def test_live_the_near_miss_controls_are_reported(live_run, manifest) -> None:
    """The six controls the corpus plants to catch a model that flags anything similar.

    Not a gate: a flagged control is a precision result, and the brief asks for it to be
    reported rather than to stop the run. The count itself therefore goes in the session
    report and nothing here fails on it.

    But "0 of 6 flagged" and "compared against nothing" produce the same number, and the
    assertion that stood here was ``isinstance(flagged, list)`` -- which ``flagged`` is by
    construction, two lines above. `W6-CERT` had to confirm the zero from the published
    evidence by hand because the test could not tell it anything.

    So the measurement's *preconditions* are asserted instead, which keeps it out of the
    way of the result: there were controls to compare against, there was published text to
    compare, and anything reported as flagged is a real control. A zero that survives those
    is a zero that means something.
    """
    quotes = {
        item["quote"]
        for finding in live_run["findings"]
        for item in finding["observation"]["evidence"]
    }
    flagged = []
    for control in manifest["controls"]:
        quotation = control["quotation"]
        if any(quotation in q or q in quotation for q in quotes):
            flagged.append(control["id"])
    print(
        f"\nnear-miss controls flagged: {flagged or 'none'} "
        f"({len(flagged)} of {len(manifest['controls'])}, "
        f"compared against {len(quotes)} published quotation(s))"
    )

    # The universe being compared against, not the answer. Each of these failing would
    # produce an empty `flagged` that reads as a clean precision result.
    assert manifest["controls"], (
        "the manifest declares no near-miss controls, so a zero here means nothing was "
        "checked rather than nothing was flagged"
    )
    assert quotes, (
        "the run published no quotations at all, so no control could have been matched "
        "however badly the model behaved -- that is a failed run, not a clean one"
    )
    known = {control["id"] for control in manifest["controls"]}
    assert set(flagged) <= known, (
        f"flagged ids that are not controls: {sorted(set(flagged) - known)}"
    )


def test_live_the_findings_are_exportable_and_resolve_to_this_run(live_run) -> None:
    """The live run's findings reach the CSV the same way a recorded run's do."""
    client = live_run["client"]
    run_id = live_run["status"]["run_id"]
    answer = client.export_csv(run_id)
    assert answer.status == 200, answer.body
    text = answer.body.decode("utf-8-sig")
    assert text.splitlines(), "the export is empty"
    for finding in live_run["findings"]:
        assert finding["finding_uid"] in text
    assert run_id in text
    # Read the named column rather than hunting for a substring. The disjunct that stood
    # here -- `",live," in text or text.count("live") >= 1` -- was satisfied by the letters
    # "live" appearing anywhere at all, including inside a quotation a model had written,
    # so it could pass on a recorded export. `W6-CERT` found it. The CSV declares a
    # `provider_mode` column; asserting on that is both stricter and simpler.
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows, "the export carries a header but no data rows"
    assert "provider_mode" in rows[0], (
        f"the export has no provider_mode column: {sorted(rows[0])}"
    )
    modes = {row["provider_mode"] for row in rows}
    assert modes == {"live"}, (
        f"a live run must export every row as live provenance, got {sorted(modes)}"
    )
