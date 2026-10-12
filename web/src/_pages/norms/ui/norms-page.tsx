'use client';

/**
 * `/norms` — «Нормы» (`W55A-WEB-NORMS`, plan §A3.7; R-112, R-113).
 *
 * Graduated from the `R-66` stub. Any account holding a role searches the CURRENT norms
 * snapshot by designation, clause and words, and opens a result's document at its page. The
 * screen first reads the snapshot list (`listNormSnapshots`, any role) to say which snapshot
 * search reads; before an administrator designates one it renders the refusal — search would
 * answer `required_norm_unavailable` — and never an empty list.
 *
 * An administrator also sees every snapshot, «Сделать текущим» on a qualifying one behind a
 * confirmation, and the append-only history. The roles come from the session the route
 * guard already read (as on the home page), so an expert's screen draws no control and
 * never asks for the history; the API still refuses both operations to anyone but `admin`.
 */

import { useRef, useState } from 'react';

import type { NormSnapshot, NormsSnapshotId } from '@/shared/api';
import type { CurrentSnapshotReading, NormFailure } from '@/entities/norms';
import {
  currentSnapshotOf, normFailure, useNormSearch, useNormSnapshotEvents, useNormSnapshots,
} from '@/entities/norms';
import { useSetCurrentSnapshot } from '@/features/set-current-snapshot';
import { NoCurrentSnapshot, NormSearchForm, NormSearchResults } from '@/widgets/norm-search';
import { NormSnapshotHistory, NormSnapshotList } from '@/widgets/norm-snapshots';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';

export interface NormsPageProps {
  /** The signed-in session's roles, as the route guard read them. */
  readonly roles: readonly string[];
  /** The search the address carries (`?q=`), or `null` for none. */
  readonly query?: string | null | undefined;
}

/** A confirmed-to-be designation: the snapshot, and which snapshot the screen showed current. */
export interface DesignationIntent {
  readonly snapshot: NormSnapshot;
  readonly expectedCurrent: NormSnapshot | null;
}

/** The lazy initial value of the pending designation. Exported so a test can seed one. */
export function noDesignationIntent(): DesignationIntent | null {
  return null;
}

export function designationIntentLabel(intent: DesignationIntent): string {
  const replaced = intent.expectedCurrent === null
    ? 'Сейчас текущего снимка нет.'
    : `Снимок ${intent.expectedCurrent.content_key} перестанет быть текущим.`;
  return (
    `Сделать текущим снимок ${intent.snapshot.content_key}? ${replaced} Поиск по нормам ` +
    'переключится на него, а новые прогоны и повторные проверки запишут его как свой снимок норм.'
  );
}

/** A definite refusal: the server answered and nothing changed, so repeating will not help. */
const REFUSALS: ReadonlySet<string> = new Set([
  'stale_current_snapshot', 'index_incomplete', 'source_unbound', 'conflict', 'not_found',
  'permission_denied', 'authentication_required', 'validation_failed', 'required_norm_unavailable',
  'unrecognized',
]);

function CurrentSnapshotStatus({ reading }: { readonly reading: CurrentSnapshotReading }) {
  if (reading.kind === 'none') return <NoCurrentSnapshot />;
  if (reading.kind === 'beyond') {
    return (
      <p role="status" className="am-note" data-norm-current="beyond">
        Текущий снимок не найден среди прочитанных снимков. Поиск всё равно идёт по тому снимку,
        который сервер считает текущим.
      </p>
    );
  }
  return (
    <p role="status" className="am-note" data-norm-current="current">
      Поиск идёт по текущему снимку <code>{reading.snapshot.content_key}</code>: документов{' '}
      {reading.snapshot.document_count}, абзацев {reading.snapshot.paragraph_count}.
    </p>
  );
}

function SearchFailure({ failure, onRetry }: { readonly failure: NormFailure; readonly onRetry: () => void }) {
  if (failure.kind === 'no_current_snapshot') return <NoCurrentSnapshot />;
  if (failure.kind === 'search_too_broad') {
    return (
      <div data-norms-search-failure={failure.kind}>
        <UnsupportedState title="Запрос слишком широкий" detail={failure.detail} />
      </div>
    );
  }
  if (failure.kind === 'validation_failed') {
    return (
      <div data-norms-search-failure={failure.kind}>
        <UnsupportedState title="Запрос не принят" detail={failure.detail} />
      </div>
    );
  }
  return (
    <div data-norms-search-failure={failure.kind}>
      <ErrorState
        title="Поиск не выполнен"
        detail={failure.detail}
        correlationId={failure.correlationId}
        onRetry={failure.retryable ? onRetry : undefined}
      />
    </div>
  );
}

/** One search, its own pages. Keyed by the query, so a new search starts on its first page. */
function SearchSection({ query }: { readonly query: string }) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const search = useNormSearch(query, cursor, true);
  if (search.isPending) return <LoadingState what="результаты поиска" />;
  if (search.error !== null) {
    return <SearchFailure failure={normFailure(search.error)} onRetry={() => void search.refetch()} />;
  }
  const next = search.data.page.next_cursor;
  return (
    <NormSearchResults
      items={search.data.items}
      onFirst={cursor === undefined ? null : () => setCursor(undefined)}
      onNext={next === null ? null : () => setCursor(next)}
    />
  );
}

function DesignationHistory() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const events = useNormSnapshotEvents(cursor, true);
  if (events.isPending) return <LoadingState what="историю назначений" />;
  if (events.error !== null) {
    const failure = normFailure(events.error);
    return (
      <div data-norms-events-failure={failure.kind}>
        <ErrorState
          title="История назначений не прочитана"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void events.refetch()}
        />
      </div>
    );
  }
  const next = events.data.page.next_cursor;
  return (
    <NormSnapshotHistory
      items={events.data.items}
      onFirst={cursor === undefined ? null : () => setCursor(undefined)}
      onNext={next === null ? null : () => setCursor(next)}
    />
  );
}

export function NormsPage({ roles, query = null }: NormsPageProps) {
  const administrator = roles.includes('admin');
  const snapshots = useNormSnapshots();
  const designate = useSetCurrentSnapshot();
  const [intent, setIntent] = useState<DesignationIntent | null>(noDesignationIntent);
  const [commandFailure, setCommandFailure] = useState<NormFailure | null>(null);
  const [completed, setCompleted] = useState(false);
  const sequence = useRef(0);
  const busy = designate.isPending;

  const readFailure = snapshots.error === null ? null : normFailure(snapshots.error);
  const reading = snapshots.data === undefined ? null : currentSnapshotOf(snapshots.data);
  // Search refuses before any snapshot is current (R-113); the screen knows that from the
  // list and says so once, instead of sending a search that can only be refused.
  const searchRefused = reading?.kind === 'none';

  function select(snapshot: NormSnapshot) {
    if (reading === null || reading.kind === 'beyond') return;
    sequence.current += 1;
    setIntent({ snapshot, expectedCurrent: reading.kind === 'current' ? reading.snapshot : null });
    setCommandFailure(null);
    setCompleted(false);
  }

  async function execute(chosen: DesignationIntent) {
    const mine = sequence.current;
    const expected: NormsSnapshotId | null = chosen.expectedCurrent?.norms_snapshot_id ?? null;
    try {
      await designate.mutateAsync({ normsSnapshotId: chosen.snapshot.norms_snapshot_id, expectedCurrent: expected });
      if (mine !== sequence.current) return;
      setCommandFailure(null);
      setCompleted(true);
      setIntent(null);
    } catch (error) {
      if (mine !== sequence.current) return;
      const failure = normFailure(error);
      setCommandFailure(failure);
      setCompleted(false);
      // A refusal is final for this intent: its belief about the current snapshot (or the
      // target) is what was refused, and the list is being read again. Anything else (an
      // unavailable dependency, a lost answer) keeps the intent: the same compare-and-set
      // may be sent again, and cannot designate twice.
      if (REFUSALS.has(failure.kind)) setIntent(null);
    }
  }

  return (
    <PageShell
      title="Нормы"
      subtitle="Поиск по тексту нормативных документов текущего снимка: по обозначению, номеру пункта и словам."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => void snapshots.refetch()}>Обновить</button>}
    >
      <section aria-label="Текущий снимок норм">
        {snapshots.isPending ? <LoadingState what="снимки норм" /> : null}
        {readFailure !== null ? (
          <div data-norms-snapshots-failure={readFailure.kind}>
            <ErrorState
              title="Снимки норм не прочитаны"
              detail={readFailure.detail}
              correlationId={readFailure.correlationId}
              onRetry={() => void snapshots.refetch()}
            />
          </div>
        ) : null}
        {reading !== null ? <CurrentSnapshotStatus reading={reading} /> : null}
      </section>

      <NormSearchForm query={query} disabled={searchRefused} />
      {query !== null && !searchRefused ? <SearchSection key={query} query={query} /> : null}

      {administrator ? (
        <section aria-label="Снимки нормативной базы" data-norms-administration>
          <h2>Снимки нормативной базы</h2>
          {snapshots.data !== undefined && reading !== null ? (
            <NormSnapshotList
              items={snapshots.data.items}
              current={reading}
              canDesignate={administrator}
              busy={busy}
              onDesignate={select}
            />
          ) : null}
          {intent !== null ? (
            <section role="group" aria-label="Подтверждение назначения текущего снимка" data-norms-intent={intent.snapshot.norms_snapshot_id}>
              <p>{designationIntentLabel(intent)}</p>
              <button type="button" className="am-button" disabled={busy} onClick={() => void execute(intent)}>
                {commandFailure === null ? 'Подтвердить' : 'Повторить'}
              </button>{' '}
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={busy}
                onClick={() => { sequence.current += 1; setIntent(null); setCommandFailure(null); }}
              >
                Отмена
              </button>
            </section>
          ) : null}
          {commandFailure !== null ? (
            <div data-norms-designation-failure={commandFailure.kind}>
              {REFUSALS.has(commandFailure.kind) ? (
                <>
                  <UnsupportedState title="Снимок не назначен" detail={commandFailure.detail} />
                  {commandFailure.correlationId !== null
                    ? <p>Идентификатор корреляции <code>{commandFailure.correlationId}</code></p>
                    : null}
                </>
              ) : (
                <ErrorState
                  title="Назначение не выполнено"
                  detail={commandFailure.detail}
                  correlationId={commandFailure.correlationId}
                />
              )}
            </div>
          ) : null}
          {completed ? <p role="status" className="am-note">Текущий снимок назначен.</p> : null}
          <h2>История назначений</h2>
          <DesignationHistory />
        </section>
      ) : null}
    </PageShell>
  );
}
