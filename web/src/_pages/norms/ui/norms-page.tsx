/**
 * `/norms` — the normative documents, on their way (`R-66`, group «Знания»).
 *
 * An honest stub in `R-23`'s sense: it says the section is coming, what will be in it and
 * when — the "when" named by an event in words, never by a number. The owner ruled the
 * event: **after the normative corpus moves onto the stand.** The corpus is stored and
 * loaded on the development host (`CURRENT_STATE.md`, "Normative-corpus persistence"); the
 * stand does not hold it yet.
 *
 * What the section would read: the list of normative documents, and each document's text
 * paragraph by paragraph. The frozen contract has no operation over the normative corpus —
 * `docs/program/W50-REGISTRY-01.md` records the measurement — so the screen shows no number
 * and invents no document.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function NormsPage() {
  return (
    <RoutePlaceholder
      screen="Нормы"
      route="/norms"
      promise="Здесь будут нормативные документы: их список, а внутри каждого документа — его текст по пунктам. Экран появится после того, как нормативная база будет перенесена на стенд."
    />
  );
}
