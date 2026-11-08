/**
 * The table of rules (`EXEC2-WEB-GROUPS-01`, ADR-0026 decision 11): **exactly one row per kind of
 * model work**, the six kinds the contract names, whatever the server returned. A kind without a
 * rule is a row that says so, and under the mode `rules` says what that costs: work of that kind is
 * refused, never sent to some other group.
 *
 * A rule names an immutable group **revision**. When the group was revised after the rule was set
 * the row says so: new work still goes on the revision the rule names until the rule is set again.
 */

import type { ExecutorRoutingMode } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { WORK_KIND_LABELS } from '@/entities/executor-connection';
import type { RuleRow } from '@/entities/executor-group';

import styles from './executor-rules.module.css';

export interface RulesTableProps {
  readonly rows: readonly RuleRow[];
  readonly mode: ExecutorRoutingMode;
}

function GroupCell({ row, mode }: { readonly row: RuleRow; readonly mode: ExecutorRoutingMode }) {
  if (row.rule === null) {
    return (
      <span data-rule-state="none">
        Правила нет{mode === 'rules' ? ': работа этого вида не запустится, пока ему не назначена группа' : ''}
      </span>
    );
  }
  if (row.group === null) {
    return <span data-rule-state="group-missing">Группа правила не найдена в списке групп</span>;
  }
  return (
    <span data-rule-state={row.onCurrentRevision ? 'current' : 'earlier'}>
      «{row.group.display_name}», модель «{row.group.current_revision.pin_id}»
      {row.onCurrentRevision
        ? ''
        : '. Правило называет прежнюю версию группы: после него группу меняли'}
    </span>
  );
}

export function RulesTable({ rows, mode }: RulesTableProps) {
  return (
    // A table wider than its box scrolls inside it, and Tab reaches the box.
    <div className={styles.tableWrap} role="region" aria-label="Правила по видам работы, таблица" tabIndex={0}>
      <table data-rules-table={rows.length}>
        <caption>Правила: какая группа принимает работу каждого вида</caption>
        <thead>
          <tr>
            <th scope="col">Вид работы</th>
            <th scope="col">Группа</th>
            <th scope="col">Назначено</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.workKind} data-rule-row={row.workKind}>
              <th scope="row">{WORK_KIND_LABELS[row.workKind]}</th>
              <td><GroupCell row={row} mode={mode} /></td>
              <td>
                {row.rule === null
                  ? '—'
                  : <><time dateTime={row.rule.set_at}>{formatInstant(row.rule.set_at)}</time>, автор <code>{row.rule.set_by}</code></>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
