/**
 * `/queue` — the analysis queue, on its way (`R-66`, group «Система»).
 *
 * An honest stub in `R-23`'s sense: it says the section is coming, what will be in it and
 * when — the "when" named by an event in words, never by a number, because wave numbers move
 * and the prepared-sections guard refuses a digit on this screen. The owner ruled the event:
 * **with durable execution of analyses.** Today a run is executed in process, stage after
 * stage, as soon as it is accepted, so there is no queue for this screen to show.
 *
 * What the section would read: each analysis waiting to be executed, with its state, its
 * priority and how long it has waited. The frozen contract has no operation that lists
 * waiting work — `docs/program/W50-REGISTRY-01.md` records the measurement — so the screen
 * shows no number and invents no row.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function QueuePage() {
  return (
    <RoutePlaceholder
      screen="Очередь"
      route="/queue"
      promise="Здесь будет очередь анализов: состояние и приоритет каждого анализа, который ждёт выполнения, и сколько времени он уже ждёт. Экран появится вместе с устойчивым выполнением анализов."
    />
  );
}
