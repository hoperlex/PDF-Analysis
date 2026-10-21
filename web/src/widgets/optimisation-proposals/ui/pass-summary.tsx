'use client';

/**
 * One optimisation pass, as a reader needs it (`W60-OPT-PROPOSALS-01`): what it read and how
 * its proposals stand. The counts by decision are the proposals' own and say so — a proposal is
 * a separate entity beside the findings, and nothing here is a finding count.
 */

import type { OptimisationPass } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  DECISION_STATES,
  DECISION_STATE_LABELS,
  VENDOR_LIST_SCOPE_LABELS,
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
        <dt>Вендор-лист АР</dt>
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
