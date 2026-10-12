/**
 * The norms snapshots and the history of the current one, for administrators
 * (`W55A-WEB-NORMS`, plan §A3.2, §A3.7, R-113).
 *
 * One snapshot is current at a time; it is replaced, never unset. A snapshot QUALIFIES only
 * with a complete search index and a confirmed source binding for every document's PDF —
 * `qualified` is the server's own predicate, and the row says which half is missing.
 * «Сделать текущим» is drawn only for a qualifying snapshot that is not current, and only
 * while the screen knows which snapshot IS current, because that belief is what the request
 * carries (`expected_current`). Pressing it only asks the page to confirm; the server still
 * decides every write.
 */

import type { NormSnapshot, NormSnapshotEvent } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { EmptyState } from '@/shared/ui';
import type { CurrentSnapshotReading } from '@/entities/norms';
import { buildStateLabel } from '@/entities/norms';

import styles from './norm-snapshots.module.css';

/** Why a snapshot that is not current cannot become current, from the server's own facts. */
function unqualifiedReason(snapshot: NormSnapshot): string {
  return snapshot.build_state === 'complete'
    ? 'Нельзя сделать текущим: не у всех документов подтверждена привязка к исходному PDF.'
    : 'Нельзя сделать текущим: поисковый индекс построен не полностью.';
}

export interface NormSnapshotListProps {
  readonly items: readonly NormSnapshot[];
  readonly current: CurrentSnapshotReading;
  /** Whether the session may designate (an administrator). Experts see no control. */
  readonly canDesignate: boolean;
  readonly busy: boolean;
  readonly onDesignate: (snapshot: NormSnapshot) => void;
}

function SnapshotRow({
  snapshot, current, canDesignate, busy, onDesignate,
}: { readonly snapshot: NormSnapshot } & Omit<NormSnapshotListProps, 'items'>) {
  const offered = canDesignate && snapshot.qualified && !snapshot.current && current.kind !== 'beyond';
  return (
    <li
      className={styles.row}
      data-norm-snapshot={snapshot.norms_snapshot_id}
      data-norm-snapshot-current={snapshot.current ? 'true' : 'false'}
      data-norm-snapshot-qualified={snapshot.qualified ? 'true' : 'false'}
      data-norm-build-state={snapshot.build_state}
    >
      <p>
        <strong>{snapshot.current ? 'Текущий снимок' : 'Снимок'}</strong> <code>{snapshot.content_key}</code>
      </p>
      <p>Загружен: <time dateTime={snapshot.created_at}>{formatInstant(snapshot.created_at)}</time></p>
      <p>
        Документов: {snapshot.document_count}. Абзацев: {snapshot.paragraph_count}, из них с
        ненадёжно распознанным текстом: {snapshot.unreliable_count}.
      </p>
      <p>Поисковый индекс: {buildStateLabel(snapshot.build_state)}.</p>
      {snapshot.current ? null : (
        <p>{snapshot.qualified ? 'Может стать текущим.' : unqualifiedReason(snapshot)}</p>
      )}
      <p className="am-form__hint">Идентификатор <code>{snapshot.norms_snapshot_id}</code></p>
      {offered ? (
        <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={() => onDesignate(snapshot)}>
          Сделать текущим
        </button>
      ) : null}
    </li>
  );
}

export function NormSnapshotList({ items, current, canDesignate, busy, onDesignate }: NormSnapshotListProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Снимков норм нет"
        detail="Ни один снимок нормативной базы не загружен, поэтому назначить текущий пока нечего."
      />
    );
  }
  return (
    <section aria-label="Снимки норм" className={styles.list} data-norm-snapshots={items.length}>
      {current.kind === 'beyond' ? (
        <p role="status" className="am-note" data-norm-current="beyond">
          Текущий снимок не найден среди прочитанных снимков, поэтому назначение недоступно: запрос
          должен знать, какой снимок текущий сейчас.
        </p>
      ) : null}
      <ol>
        {items.map((snapshot) => (
          <SnapshotRow
            key={snapshot.norms_snapshot_id}
            snapshot={snapshot}
            current={current}
            canDesignate={canDesignate}
            busy={busy}
            onDesignate={onDesignate}
          />
        ))}
      </ol>
    </section>
  );
}

export interface NormSnapshotHistoryProps {
  readonly items: readonly NormSnapshotEvent[];
  readonly onFirst: (() => void) | null;
  readonly onNext: (() => void) | null;
}

/** The append-only history of designations, newest first. */
export function NormSnapshotHistory({ items, onFirst, onNext }: NormSnapshotHistoryProps) {
  if (items.length === 0 && onFirst === null) {
    return <EmptyState title="Текущий снимок ещё не назначался" detail="История появится после первого назначения." />;
  }
  return (
    <section aria-label="История назначений текущего снимка" className={styles.list} data-norm-events={items.length}>
      {items.length === 0 ? (
        <EmptyState title="На этой странице назначений нет" detail="Вернитесь к началу истории." />
      ) : (
        <ol>
          {items.map((event) => (
            <li key={event.event_id} className={styles.row} data-norm-event={event.event_id}>
              <p><time dateTime={event.changed_at}>{formatInstant(event.changed_at)}</time></p>
              <p>
                {event.from_norms_snapshot_id === null
                  ? 'Назначен первый текущий снимок '
                  : <>Вместо <code>{event.from_norms_snapshot_id}</code> текущим стал </>}
                <code>{event.to_norms_snapshot_id}</code>
              </p>
              <p className="am-form__hint">Назначил <code>{event.actor_user_uid}</code></p>
            </li>
          ))}
        </ol>
      )}
      <div className="am-pager">
        {onFirst === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onFirst}>
            В начало
          </button>
        )}
        {onNext === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onNext}>
            Дальше
          </button>
        )}
      </div>
    </section>
  );
}
