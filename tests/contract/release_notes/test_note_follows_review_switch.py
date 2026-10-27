"""While the beta switch is off, the current release note may not quote what the screens no longer show.

``R-146ba`` took two indications off the screens for the beta: the profile label «рабочая версия,
проверка человеком не проводилась» and the wording that calls an AR v3 citation provisional and
waiting for the expert. One web constant, ``SHOW_REVIEW_INDICATION``, decides whether they are drawn.
A note that says a screen shows one of them while the constant is ``false`` says something untrue
about the product, so this test reads the constant and the note of the current ``VERSION`` together.

Not covered by the switch, and so allowed in a note: the label above the version-comparison summary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SWITCH_MODULE = ROOT / "web" / "src" / "shared" / "config" / "review-indication.ts"
DECLARATION = re.compile(r"^export const SHOW_REVIEW_INDICATION\s*=\s*(true|false)\s+as boolean;$", re.M)

# What the switch governs, as a note would quote or paraphrase it. «проверк… эксперт…/человек…» is the
# profile label and the «требует проверки эксперта» family; «предварительн…» is the provisional wording.
SWITCHED = re.compile(
    r"рабочая версия, проверка человеком|предварительн|проверк\w*\s+(?:эксперт|человек)|экспертн\w*\s+проверк",
    re.I,
)
# Quotes the switch does not govern: the label above the comparison summary (owner and integrator rule)
# and the label of a draft profile (the owner took off the label of a reviewed profile only).
NOT_SWITCHED = (
    "Сводка подготовлена моделью, проверка человеком не проводилась",
    "черновик, требует экспертной проверки",
)


def switch_default(source: str) -> bool:
    """The default of the constant, read from its one declaration (a second or a changed form is an error)."""
    found = DECLARATION.findall(source)
    assert len(found) == 1, "SHOW_REVIEW_INDICATION must be declared once as `= true|false as boolean;`"
    return found[0] == "true"


def claims_a_switched_screen(text: str) -> bool:
    """Whether an item of a note quotes wording the switch governs."""
    for allowed in NOT_SWITCHED:
        text = text.replace(allowed, "")
    return SWITCHED.search(text) is not None


def current_note() -> dict:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    return json.loads((ROOT / "release-notes" / f"{version}.json").read_text(encoding="utf-8"))


def test_the_switch_is_declared_once_and_its_default_is_readable() -> None:
    assert isinstance(switch_default(SWITCH_MODULE.read_text(encoding="utf-8")), bool)


def test_the_current_note_quotes_nothing_the_switch_hides_while_it_is_off() -> None:
    if switch_default(SWITCH_MODULE.read_text(encoding="utf-8")):
        return  # the wording is on the screens; a note may quote it
    note = current_note()
    offending = [
        (number, item["text"])
        for number, item in enumerate(note["items"], start=1)
        if claims_a_switched_screen(f'{item["text"]} {item["where"]}')
    ]
    assert offending == [], f"release note {note['version']} quotes wording the screens no longer show: {offending}"


def test_the_check_can_fail() -> None:
    label = "рабочая версия, проверка человеком не проводилась"
    assert claims_a_switched_screen(f"У профилей пометка «{label}» вместо черновика.")
    assert claims_a_switched_screen("Результат — предварительные цитаты для проверки экспертом.")
    assert claims_a_switched_screen("Каждая тема требует проверки эксперта.")
    assert not claims_a_switched_screen("У профилей состояние «проверен» вместо черновика.")
    assert not claims_a_switched_screen("Ни человек, ни реальные документы эти инструкции не проверяли.")
    summary, draft = NOT_SWITCHED
    assert not claims_a_switched_screen(f"Сводка готовится с пометкой «{summary}» и ссылками.")
    assert claims_a_switched_screen(f"Сводка с пометкой «{summary}»; профиль «{label}».")
    assert not claims_a_switched_screen(f"Состояние «проверен» вместо «{draft}».")
    assert claims_a_switched_screen(f"Состояние «{label}» вместо «{draft}».")
    on = "export const SHOW_REVIEW_INDICATION = true as boolean;"
    off = "export const SHOW_REVIEW_INDICATION = false as boolean;"
    assert switch_default(on) is True and switch_default(off) is False
    for broken in ("", f"{on}\n{off}", "export const SHOW_REVIEW_INDICATION = (flag) as boolean;"):
        try:
            switch_default(broken)
        except AssertionError:
            continue
        raise AssertionError(f"a declaration the test cannot read was accepted: {broken!r}")
