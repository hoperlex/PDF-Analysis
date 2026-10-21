"""`HARDEN-AUTH-EDGE-01` -- the deployment texts no longer say the origin needs no credential.
`EXPOSURE-REVIEW-01` `E-8`, debt `D-193`.

**The defect.** Four places described the 2026-09-22 state as if it were today's:
`infra/deploy/compose.server.yml`, `infra/deploy/env/alpha.env.example` and
`docs/program/DEPLOYMENT_RUNBOOK.md` said `/bff/v1` "serves every operation ... with no
credential" and that the origin is "unauthenticated by design", and `infra/deploy/deploy.sh`
said `/api/v1/openapi.json` "needs no credential" while the guard a few lines below demands
`401`. Live, both answer `401` to a caller that presents nothing (`EXPOSURE-REVIEW-01.md`,
probes B and C). Prose that overstates the exposure misleads whoever judges the exposure from
it, and nothing read it.

**What is held.** (1) None of the stale sentences survives anywhere under `infra/deploy/` or in
the runbook; (2) each of the four places says what is true now (`401`); (3) the two facts that
make the corrected sentences true are still true in code -- the web tier answers `401` to a
request with no session cookie, and `deploy.sh`'s `proxy-answers` guard still demands `401`
and refuses `200`. A sentence that is right today and a code path that changes tomorrow is how
the first four became stale.

**Every check is shown able to fail**, in `test_each_check_can_fail`, by putting the stale
sentence back or taking the correction out in front of the same function the real check uses.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra" / "deploy"
RUNBOOK = ROOT / "docs" / "program" / "DEPLOYMENT_RUNBOOK.md"
ROUTE = ROOT / "web" / "src" / "app" / "bff" / "v1" / "[...path]" / "route.ts"

COMPOSE = "infra/deploy/compose.server.yml"
ENV_EXAMPLE = "infra/deploy/env/alpha.env.example"
RUNBOOK_KEY = "docs/program/DEPLOYMENT_RUNBOOK.md"
DEPLOY_SH = "infra/deploy/deploy.sh"

#: The sentences that were true on 2026-09-22 and are not now. Matched on prose with comment
#: markers, emphasis and backticks removed and whitespace collapsed, so wrapping a line
#: differently does not hide one.
STALE = (
    re.compile(r"\bserves every operation\b", re.IGNORECASE),
    re.compile(r"\bunauthenticated by design\b", re.IGNORECASE),
    re.compile(r"\badds it server-side\b", re.IGNORECASE),
    re.compile(r"openapi\.json.{0,80}?\bneeds no credential", re.IGNORECASE),
)
#: What each corrected place must say. The first three describe `/bff/v1`; the fourth the
#: documentation route the deploy guard asks for.
BFF_ANSWERS_401 = re.compile(r"/bff/v1\b.{0,900}?\b401\b")
OPENAPI_ANSWERS_401 = re.compile(r"openapi\.json.{0,300}?\banswers 401\b")
CORRECTIONS = {
    COMPOSE: BFF_ANSWERS_401,
    ENV_EXAMPLE: BFF_ANSWERS_401,
    RUNBOOK_KEY: BFF_ANSWERS_401,
    DEPLOY_SH: OPENAPI_ANSWERS_401,
}
TEXT_SUFFIXES = {".yml", ".yaml", ".sh", ".example", ".md", ".conf", ".py", ".env"}


def prose(text: str) -> str:
    """The text a reader reads: comment markers, emphasis and backticks gone, one line."""
    text = re.sub(r"(?m)^\s*#+ ?", " ", text)
    return " ".join(text.replace("*", "").replace("`", "").split())


def read_tree() -> dict[str, str]:
    """Every text file under `infra/deploy/` and the runbook, keyed by repository path."""
    texts: dict[str, str] = {}
    for path in sorted(DEPLOY.rglob("*")):
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name.endswith(".env.example")):
            texts[path.relative_to(ROOT).as_posix()] = path.read_text(encoding="utf-8")
    texts[RUNBOOK_KEY] = RUNBOOK.read_text(encoding="utf-8")
    return texts


def text_problems(texts: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for name, text in texts.items():
        flat = prose(text)
        for pattern in STALE:
            hit = pattern.search(flat)
            if hit:
                problems.append(f"{name}: still says {hit.group(0)!r}")
    for name, pattern in CORRECTIONS.items():
        if name not in texts:
            problems.append(f"{name}: is missing")
        elif not pattern.search(prose(texts[name])):
            problems.append(f"{name}: does not say that the origin answers 401 to a caller with no credential")
    return problems


def code_problems(route: str, deploy_sh: str) -> list[str]:
    """The two behaviours the corrected sentences rest on, still true in code."""
    problems: list[str] = []
    match = re.search(r"function noSession\(request: Request\): Response \{(.*?)\n\}", route, re.DOTALL)
    if match is None or "401" not in match.group(1) or "'authentication_required'" not in match.group(1):
        problems.append("the web tier no longer has a `noSession` that answers 401 authentication_required")
    handle = re.search(
        r"async function handle\(request: Request, context: RouteContext\): Promise<Response> \{(.*?)\n\}\n",
        route,
        re.DOTALL,
    )
    if handle is None or not handle.group(1).rstrip().endswith("return noSession(request);"):
        problems.append("the web tier's catch-all no longer ends in `noSession` for a request with no session cookie")
    if 'if [ "$PROXY_CODE" != 401 ]; then' not in deploy_sh:
        problems.append("deploy.sh's proxy-answers guard no longer demands 401 on /api/v1/openapi.json")
    if not re.search(r"\n\s*200\)\s*\n\s*refuse \"/api/v1/openapi\.json answered 200", deploy_sh):
        problems.append("deploy.sh no longer refuses a 200 on /api/v1/openapi.json")
    return problems


def test_no_stale_claim_survives_and_each_correction_is_present() -> None:
    assert text_problems(read_tree()) == []


def test_the_corrected_sentences_still_rest_on_true_code() -> None:
    assert code_problems(ROUTE.read_text(encoding="utf-8"), (DEPLOY / "deploy.sh").read_text(encoding="utf-8")) == []


#: (case, file, text appended or removed). Appended stale prose goes in as a comment/markdown line.
STALE_BACK = {
    "compose: the bff claim comes back": (
        COMPOSE,
        "\n    # `/bff/v1` serves every operation of this surface with no credential.\n",
    ),
    "env example: the origin is unauthenticated again": (
        ENV_EXAMPLE,
        "\n# the origin is unauthenticated by design.\n",
    ),
    "runbook: the BFF adds the credential again": (
        RUNBOOK_KEY,
        "\nThe BFF route adds it server-side, for anyone.\n",
    ),
    "deploy.sh: the openapi claim comes back": (
        DEPLOY_SH,
        "\n# `/api/v1/openapi.json` reaches the application's root and needs no credential.\n",
    ),
    "a README gains the claim": (
        "infra/deploy/README.md",
        "\n`/bff/v1` serves **every operation** of the surface.\n",
    ),
}


@pytest.mark.parametrize("case", sorted(STALE_BACK))
def test_each_check_can_fail_when_the_stale_sentence_returns(case: str) -> None:
    name, addition = STALE_BACK[case]
    texts = read_tree()
    texts[name] += addition
    assert text_problems(texts), f"{case}: the guard stayed green"


@pytest.mark.parametrize("name", sorted(CORRECTIONS))
def test_each_check_can_fail_when_a_correction_is_taken_out(name: str) -> None:
    texts = read_tree()
    # Remove every 401 from the place: the claim "answers 401" is gone, whatever else stays.
    texts[name] = re.sub(r"\b401\b", "4xx", texts[name])
    assert text_problems(texts), f"{name}: the guard stayed green without its 401"


def test_each_check_can_fail_when_the_code_changes() -> None:
    route = ROUTE.read_text(encoding="utf-8")
    deploy_sh = (DEPLOY / "deploy.sh").read_text(encoding="utf-8")
    assert code_problems(route, deploy_sh) == []
    anonymous = route.replace("function noSession(request: Request): Response {\n  return envelopeResponse(\n    401,",
                              "function noSession(request: Request): Response {\n  return envelopeResponse(\n    200,", 1)
    assert anonymous != route and code_problems(anonymous, deploy_sh)
    open_door = route.replace("  return noSession(request);\n}\n\n/** True when the catch-all's segments", "  return forwardWithCredential(request, segments, { upstream, token: null });\n}\n\n/** True when the catch-all's segments", 1)
    assert open_door != route and code_problems(open_door, deploy_sh)
    laxer = deploy_sh.replace('if [ "$PROXY_CODE" != 401 ]; then', 'if [ "$PROXY_CODE" != 200 ]; then', 1)
    assert laxer != deploy_sh and code_problems(route, laxer)
    accepting = re.sub(r"(\n\s*)200\)(\s*\n\s*)refuse \"/api/v1/openapi\.json answered 200", r"\g<1>999)\g<2>refuse \"/api/v1/openapi.json answered 200", deploy_sh, count=1)
    assert accepting != deploy_sh and code_problems(route, accepting)
