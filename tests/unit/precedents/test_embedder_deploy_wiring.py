"""`EMBED-01`: how `deploy.sh` and `verify-deployed.sh` reach the night encoder, read from the scripts as written.

Both are inert unless ``ALPHA_EMBEDDER=yes`` (the stack is what it was), both refuse a value that is neither ``yes`` nor ``no`` instead of reading it as the
default, and the build comes after the images that serve and before anything is brought up, so a full disk is a stack that is still serving. The
refusal itself (the disk checked before the build) is driven in ``test_embed_window_script.py``; this holds the wiring that calls it.
"""

from __future__ import annotations

import re
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[3] / "infra" / "deploy"
DEPLOY_SH = (DEPLOY / "deploy.sh").read_text(encoding="utf-8")
VERIFY_SH = (DEPLOY / "verify-deployed.sh").read_text(encoding="utf-8")


def position(text: str, needle: str) -> int:
    found = text.find(needle)
    assert found >= 0, needle
    return found


def test_deploy_builds_the_encoder_image_after_the_serving_images_and_before_up() -> None:
    built = position(DEPLOY_SH, "# <<< guard: images-built")
    embedder = position(DEPLOY_SH, '"$HERE/embed-window.sh" build-image --env-file "$ENV_FILE"')
    first_up = position(DEPLOY_SH, "\ncompose up -d || UP_STATUS=$?")
    assert built < embedder < first_up


def test_deploy_calls_it_only_for_yes_and_refuses_what_it_does_not_recognise() -> None:
    start = position(DEPLOY_SH, 'EMBEDDER="$(configured ALPHA_EMBEDDER)"')
    block = DEPLOY_SH[start:DEPLOY_SH.index("# --- 1a.", start)]
    assert re.search(r"case \"\$\{EMBEDDER:-no\}\" in\n\s+no\) ;;\n\s+yes\)", block), "an unset value is no"
    assert "neither yes nor no" in block and "refuse " in block
    assert block.count("build-image") == 1
    assert "NOTHING WAS STARTED OR REPLACED" in block, "a failed encoder build leaves what was serving still serving"


def test_deploy_adds_no_guard_marker_of_its_own() -> None:
    """A `# >>> guard:` block needs a case in `test_deploy_script_refusals.py`, which this lane does not own; the logic is in `embed-window.sh`, which has its own tests."""
    assert "embed" not in " ".join(re.findall(r"^# >>> guard: ([a-z-]+)$", DEPLOY_SH, re.MULTILINE))


def test_verify_asks_for_the_encoder_only_when_it_is_on_and_before_it_says_the_stack_is_this_tree() -> None:
    asked = position(VERIFY_SH, '"$HERE/embed-window.sh" verify --env-file "$ENV_FILE"')
    verdict = position(VERIFY_SH, 'echo "verify-deployed.sh: the deployed stack IS this tree')
    credential = position(VERIFY_SH, "# <<< step: default-credential-gate")
    assert credential < asked < verdict
    block = VERIFY_SH[position(VERIFY_SH, 'EMBEDDER="$(configured ALPHA_EMBEDDER)"'):verdict]
    assert re.search(r"case \"\$\{EMBEDDER:-no\}\" in\n\s+no\) ;;\n\s+yes\)", block) and "neither yes nor no" in block
    assert 'fail "$DRIFT"' in block, "a missing encoder is a stack that is not as it was deployed"


def test_the_scripts_the_encoder_needs_are_executable_and_named_where_the_wiring_says() -> None:
    for name in ("embed-window.sh",):
        assert (DEPLOY / name).stat().st_mode & 0o111, f"{name} is not executable"
    for unit in ("auditmanager-embed-window.service", "auditmanager-embed-window.timer"):
        assert (DEPLOY / "systemd" / unit).is_file()
