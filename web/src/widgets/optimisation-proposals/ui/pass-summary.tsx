'use client';

/**
 * One optimisation pass, as a reader needs it (`W60-OPT-PROPOSALS-01`): what it read and how
 * its proposals stand. The counts by decision are the proposals' own and say so — a proposal is
 * a separate entity beside the findings, and nothing here is a finding count.
 *
 * **«Проход от … ▾» (`UIP-S09-04`).** The list of the set's passes and the disclosure «Сведения о проходе» were two blocks over the
 * table; they are one element at the right of the top row. Its button says the open pass («Проход от ДД.ММ.ГГГГ ЧЧ:ММ ▾») and opens a
 * small panel: the passes to choose from, each with the number of its proposals and the counts of its decisions (only where the set
 * has more than one), and the facts of the open pass (the version, the run, the price list and the vendor list it read). The facts
 * stay behind the button, closed (`Г12-B`): they are for the one who asks. The panel is the element's own `<details>`, as the export
 * bar's is: the shared `Menu` takes its items as strings and cannot carry a chosen state or the facts. It closes on a press outside
 * it, on Escape (focus back on the button) and on the choice of a pass.
 */

import { useEffect, useRef } from 'react';

import type { OptimisationPass, OptimisationPassId } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  DECISION_STATES,
  DECISION_STATE_LABELS,
  VENDOR_LIST_SCOPE_LABELS,
  describeCounts,
} from '@/entities/optimisation-proposal';

import styles from './optimisation-proposals.module.css';

export interface PassSummaryProps {
  readonly pass: OptimisationPass;
}

export function PassSummary({ pass }: PassSummaryProps) {
  return (
    <div data-optimisation-pass={pass.optimisation_pass_id}>
      <dl className={styles.facts}>
        <dt>Запущен</dt>
        <dd>
          {formatInstant(pass.started_at)}, {pass.started_by_label}
        </dd>
        <dt>Версия комплекта</dt>
        <dd>
          <code>{pass.version_uid}</code>
        </dd>
        <dt>Прогон</dt>
        <dd>
          <code>{pass.run_id}</code>
        </dd>
        <dt>Прайс-лист</dt>
        <dd>
          <code>{pass.price_list_id}</code>
        </dd>
        <dt>Вендор-лист раздела</dt>
        <dd>
          {VENDOR_LIST_SCOPE_LABELS[pass.vendor_list_source]}, <code>{pass.vendor_list_id}</code>
        </dd>
        <dt>Строки спецификации</dt>
        <dd>
          всего — {pass.specification_row_count}, однозначно сопоставлено с прайс-листом —{' '}
          {pass.matched_row_count}, из них с аналогом — {pass.proposed_row_count}
        </dd>
        <dt>Предложений</dt>
        <dd>{pass.proposal_count}</dd>
      </dl>
      <p className="am-note">
        Счётчики решений относятся только к предложениям этого прохода и не смешиваются со
        счётчиками замечаний.
      </p>
      <ul className={styles.counts} aria-label="Предложения по решениям">
        {DECISION_STATES.map((state) => (
          <li key={state} className={styles.count} data-decision-count={state}>
            {DECISION_STATE_LABELS[state]}: <strong>{pass.decision_counts[state]}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

export interface PassMenuProps {
  /** The set's passes, newest first. */
  readonly passes: readonly OptimisationPass[];
  /** The open pass. A pass that is not in `passes` is read as the newest one. */
  readonly active: OptimisationPassId | null;
  readonly onOpen: (passId: OptimisationPassId) => void;
}

/**
 * «Проход от … ▾»: the open pass in one button, and under it the choice of another pass and the facts of the open one. A set with a
 * single pass shows that pass and its facts and offers no choice. Draws nothing for a set with no pass (the caller says so).
 */
export function PassMenu({ passes, active, onOpen }: PassMenuProps) {
  const root = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const node = root.current;
    if (node === null) return undefined;
    const outside = (event: Event) => {
      if (node.open && event.target instanceof Node && !node.contains(event.target)) node.open = false;
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !node.open) return;
      node.open = false;
      node.querySelector('summary')?.focus();
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, []);

  const current = passes.find((pass) => pass.optimisation_pass_id === active) ?? passes[0];
  if (current === undefined) return null;
  return (
    <details ref={root} className={styles.passMenu} data-pass-menu="" data-pass-count={passes.length}>
      <summary className={`am-button am-button--quiet ${styles.passTrigger}`}>
        Проход от {formatInstant(current.started_at)} <span aria-hidden="true">▾</span>
      </summary>
      <div className={styles.passPopup}>
        {passes.length > 1 ? (
          <ul className={styles.passes} aria-label="Проходы комплекта">
            {passes.map((pass) => (
              <li key={pass.optimisation_pass_id} className={styles.pass}>
                <button
                  type="button"
                  className={pass.optimisation_pass_id === current.optimisation_pass_id ? 'am-button' : 'am-button am-button--quiet'}
                  aria-pressed={pass.optimisation_pass_id === current.optimisation_pass_id}
                  onClick={() => {
                    if (root.current !== null) root.current.open = false;
                    onOpen(pass.optimisation_pass_id);
                  }}
                >
                  Проход от {formatInstant(pass.started_at)}
                </button>
                <span>
                  предложений — {pass.proposal_count}; {describeCounts(pass)}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        <div data-pass-summary="">
          <PassSummary pass={current} />
        </div>
      </div>
    </details>
  );
}
