import type { ExecutionJournalEntry } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { visibleJournal } from '@/entities/execution';
import { EmptyState } from '@/shared/ui';

import styles from './execution-journal.module.css';

export interface ExecutionJournalProps {
  readonly entries: readonly ExecutionJournalEntry[];
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
}

export function ExecutionJournal({ entries, onNext, onPrevious }: ExecutionJournalProps) {
  if (entries.length === 0 && onPrevious === null) {
    return <EmptyState title="Записей пока нет" detail="После выполнения прогонов события появятся здесь." />;
  }
  return (
    <section aria-label="События выполнения" className={styles.list}>
      {entries.length === 0 ? <EmptyState title="На этой странице записей нет" detail="Вернитесь к предыдущей странице." /> : null}
      {/* One line per event, as the original's log: time, what happened, the state and code the closed projection allows, the run. */}
      {entries.length === 0 ? null : (
        <div className={styles.scroll}>
          <table className={styles.table} data-journal-table="">
            <thead>
              <tr>
                <th scope="col">Время</th>
                <th scope="col">Событие</th>
                <th scope="col">Состояние</th>
                <th scope="col">Код</th>
                <th scope="col">Прогон</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const visible = visibleJournal(entry);
                return (
                  <tr key={entry.event_id}>
                    <td className={styles.time}><time dateTime={entry.occurred_at}>{formatInstant(entry.occurred_at)}</time></td>
                    <td className={styles.event}><strong>{visible.event}</strong></td>
                    <td>{visible.state === null ? null : <strong>{visible.state}</strong>}</td>
                    <td>{visible.code === null ? null : <code>{visible.code}</code>}</td>
                    <td className={styles.identity}><a href={routes.logs(entry.run_id)}><code>{entry.run_id}</code></a></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <nav aria-label="Страницы журнала" className={styles.paging}>
        <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
        <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
      </nav>
    </section>
  );
}
