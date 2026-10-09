import type { ExecutionJournalEntry } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
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
      <ol>
        {entries.map((entry) => {
          const visible = visibleJournal(entry);
          return (
            <li key={entry.event_id} className={styles.row}>
              <div className={styles.heading}>
                <strong>{visible.event}</strong>
                <time dateTime={entry.occurred_at}>{formatInstant(entry.occurred_at)}</time>
              </div>
              <p className={styles.identity}>Прогон <code>{entry.run_id}</code></p>
              {visible.state !== null ? <p>Состояние: <strong>{visible.state}</strong></p> : null}
              {visible.code !== null ? <p>Код: <code>{visible.code}</code></p> : null}
            </li>
          );
        })}
      </ol>
      <nav aria-label="Страницы журнала" className={styles.paging}>
        <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
        <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
      </nav>
    </section>
  );
}
