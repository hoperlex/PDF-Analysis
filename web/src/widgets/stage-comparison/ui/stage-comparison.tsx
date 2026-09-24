'use client';

/**
 * Two runs of one published version, side by side.
 *
 * `R-23` asked for the stage comparison as a skeleton with stubs, *«реализация по ходу
 * альфы»*. This widget is the part of that skeleton which is **not** a stub: every figure
 * it prints is a figure one of the two readings carries, and where the readings carry
 * nothing it prints nothing and says so.
 *
 * ## One request, and no second cadence
 *
 * It reads `useRunList` — the runs of this version, which `listRuns` answers *newest
 * first* and each item of which is the whole `RunStatus`, byte-identical to what
 * `getRunStatus` answers for that run (`W18-SEAL` asserts that equality server-side). So
 * comparing two runs needs no per-run request and adds no polling loop: `useRunStatus` on
 * the run screen remains the one polling loop in this application.
 *
 * ## What it does NOT say to a reviewer
 *
 * `R-18`, and `D-58` was closed by deleting exactly this: a finished application does not
 * explain its own transport to the person using it. So the screen says *«полное сравнение
 * этапов появится позже»* and never *"this operation does not return that"*. Which
 * operation carries which field is a fact about this programme and belongs in comments
 * like this one and in `docs/program/W43-COMPARE.md`.
 *
 * The machine vocabulary keeps its home in `data-` attributes throughout — `data-run-id`,
 * `data-run-state`, `data-stage-id`, `data-comparison` — which is the convention `D-62`
 * established and `PA-01` criterion 4 is re-driven from. A reviewer reads Russian; an
 * instrument reads the attribute.
 *
 * ## Why `terminal_detail` is an attribute and a count, and not printed
 *
 * `D-46` added it in wave 42 and **nothing in `web/src` rendered it before this widget**.
 * Its keys and values are drawn from the frozen catalog's `safe_detail_keys` — `dependency`,
 * `stage_id`, `reference_kind` and the rest — which are Latin classifiers that no contract
 * `enum` publishes, so there is no contract-derived label map for them and a hand-written
 * one would be the class `W30-LISTS` closed eighteen instances of. Printing them raw would
 * put untranslated machine words in front of a Russian reviewer, which is `D-62` again. So
 * the row reports **how many** classifiers each run recorded and whether the two agree, and
 * carries the classifiers themselves in `data-terminal-detail` where a developer and a
 * journey can read them.
 */

import { useState } from 'react';

import type { ProviderMode, RunStatus, StageStatus, VersionUid } from '@/shared/api';
import type { ComparedFact, ComparedStage, Comparison, FactId } from '@/entities/audit-run';
import {
  COST_BASIS_LABELS,
  EmptyState,
  ErrorState,
  LoadingState,
  NotApplicableState,
  PROVIDER_MODE_LABELS,
  PROVIDER_MODE_UNKNOWN_LABEL,
  RunStateBadge,
  STAGE_LABELS,
  StageStatusBadge,
} from '@/shared/ui';
import { classifyListingFailure, formatInstant } from '@/shared/lib';
import {
  comparedCount,
  comparedFacts,
  comparedStages,
  defaultPair,
  differenceCount,
  formatCostMicros,
  formatElapsed,
  providerModeLabel,
  terminalDetailKeys,
  terminalDetailDigest,
  useRunList,
} from '@/entities/audit-run';

import styles from './stage-comparison.module.css';

export interface StageComparisonProps {
  readonly versionUid: VersionUid;
}

/**
 * What each row of the run table is, in the reader's language.
 *
 * `Record<FactId, string>` over the whole union, so a thirteenth fact cannot be added to
 * `run-comparison.ts` without this file failing to compile. `W33-SECT` keyed its label maps
 * on the type and the type checker named two contract members its own grep had missed —
 * and `OPERATING_CONSTRAINTS.md` §4.65 is the other half of why that works here: `make gate`
 * runs `npm run typecheck` before the suite, so a type-keyed map is a guard in this tree
 * rather than well-formatted documentation.
 */
const FACT_LABELS: Readonly<Record<FactId, string>> = {
  state: 'Состояние',
  provider_mode: 'Режим провайдера',
  created_at: 'Создан',
  terminal_at: 'Завершён',
  duration: 'Длительность',
  published_finding_count: 'Опубликованных находок',
  diagnostic_observation_count: 'Диагностических наблюдений',
  model_call_count: 'Вызовов модели',
  cost_micros: 'Стоимость',
  cost_basis: 'Основание стоимости',
  terminal_reason: 'Причина остановки',
  terminal_detail: 'Уточнение причины',
};

/**
 * The four verdicts, in a reviewer's words.
 *
 * `one_sided` and `absent` are deliberately not phrased as differences. One run recording
 * something the other did not is a difference in what was written down; neither recording
 * it is nothing at all, and calling that «совпадает» would claim an agreement that was
 * never measured.
 */
const COMPARISON_LABELS: Readonly<Record<Comparison, string>> = {
  same: 'совпадает',
  differs: 'отличается',
  one_sided: 'есть только у одного прогона',
  absent: 'не сообщается ни одним прогоном',
};

/** The provider mode of a reading, in Russian. `unknown` is never `live`. */
function providerModeText(value: string | number | null): string {
  if (value === null) return '—';
  const label = providerModeLabel(value);
  return label === 'unknown'
    ? PROVIDER_MODE_UNKNOWN_LABEL
    : PROVIDER_MODE_LABELS[label as ProviderMode];
}

/** One run's side of one fact. The machine value stays in the cell's `data-` attribute. */
function FactCell({
  factId,
  run,
  value,
}: {
  readonly factId: FactId;
  readonly run: RunStatus;
  readonly value: string | number | null;
}) {
  if (factId === 'state') {
    return <RunStateBadge state={run.state} />;
  }
  if (factId === 'provider_mode') {
    return (
      <span data-provider-mode={value ?? 'absent'}>{providerModeText(value)}</span>
    );
  }
  if (factId === 'created_at' || factId === 'terminal_at') {
    return <span className={styles.instant}>{formatInstant(value === null ? null : String(value))}</span>;
  }
  if (factId === 'duration') {
    return (
      <span className={styles.figure} data-elapsed-ms={value ?? 'unknown'}>
        {formatElapsed(typeof value === 'number' ? value : null)}
      </span>
    );
  }
  if (factId === 'cost_micros') {
    return (
      <span className={styles.figure} data-cost-micros={value ?? 'absent'}>
        {typeof value === 'number' ? formatCostMicros(value) : '—'}
      </span>
    );
  }
  if (factId === 'cost_basis') {
    return (
      <span data-cost-basis={value ?? 'absent'}>
        {value === 'measured' || value === 'estimated' ? COST_BASIS_LABELS[value] : '—'}
      </span>
    );
  }
  if (factId === 'terminal_reason') {
    // An error code is the one Latin string this programme shows deliberately: it is
    // rendered beside its meaning on the run screen, and it is what an operator quotes.
    return value === null ? (
      <span className={styles.absent}>—</span>
    ) : (
      <code data-terminal-reason={value}>{value}</code>
    );
  }
  if (factId === 'terminal_detail') {
    const keys = terminalDetailKeys(run);
    return (
      <span data-terminal-detail={terminalDetailDigest(run) ?? 'absent'}>
        {keys === null ? '—' : `уточнений: ${keys.length}`}
      </span>
    );
  }
  return (
    <span className={styles.figure} data-count={value ?? 'absent'}>
      {typeof value === 'number' ? String(value) : '—'}
    </span>
  );
}

/** One run's side of one stage. */
function StageCell({ status, errorCode }: { readonly status: StageStatus | null; readonly errorCode: string | null }) {
  if (status === null) {
    return (
      <em className={styles.absent} data-stage-status="not-reported">
        не сообщён
      </em>
    );
  }
  return <StageStatusBadge status={status} errorCode={errorCode} />;
}

/** A run, as one line of a chooser. Newest first, exactly as the server ordered them. */
function runChoiceLabel(run: RunStatus): string {
  return `${formatInstant(run.created_at)} · ${run.run_id}`;
}

function Chooser({
  name,
  runs,
  selected,
  onSelect,
}: {
  readonly name: string;
  readonly runs: readonly RunStatus[];
  readonly selected: string;
  readonly onSelect: (runId: string) => void;
}) {
  return (
    <label className={styles.choice}>
      <span>{name}</span>
      <select value={selected} onChange={(event) => onSelect(event.target.value)}>
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {runChoiceLabel(run)}
          </option>
        ))}
      </select>
    </label>
  );
}

export function StageComparison({ versionUid }: StageComparisonProps) {
  const query = useRunList(versionUid);
  const [chosen, setChosen] = useState<readonly [string, string] | null>(null);

  if (query.isPending) return <LoadingState what="прогоны этой версии" />;

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'прогоны этой версии',
      parent: 'version',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  }

  const runs = query.data.items;

  if (runs.length === 0) {
    return (
      <EmptyState
        title="По этой версии прогонов не запускалось."
        detail="Сравнивать пока нечего. Запустите прогон на экране версии — и вернитесь сюда, когда их станет два."
      />
    );
  }

  const pair = defaultPair(runs);

  if (pair === null) {
    return (
      <NotApplicableState
        title="Для сравнения нужны два прогона этой версии."
        detail="Пока запущен только один. Сравнение сопоставляет два прогона одной и той же версии документа: версия неизменяема, поэтому различия между прогонами — это различия анализа, а не исходного файла."
      />
    );
  }

  const byId = new Map(runs.map((run) => [run.run_id, run]));
  const [defaultLeft, defaultRight] = pair;
  const left = byId.get(chosen?.[0] ?? defaultLeft.run_id) ?? defaultLeft;
  const right = byId.get(chosen?.[1] ?? defaultRight.run_id) ?? defaultRight;

  const facts = comparedFacts(left, right);
  const stages = comparedStages(left, right);
  const differences = differenceCount(facts);
  const compared = comparedCount(facts);
  const sameRun = left.run_id === right.run_id;

  return (
    <div
      className={styles.comparison}
      data-run-count={runs.length}
      data-left-run={left.run_id}
      data-right-run={right.run_id}
    >
      <div className={styles.choosers} role="group" aria-label="Выбор прогонов для сравнения">
        <Chooser
          name="Прогон слева"
          runs={runs}
          selected={left.run_id}
          onSelect={(runId) => setChosen([runId, right.run_id])}
        />
        <Chooser
          name="Прогон справа"
          runs={runs}
          selected={right.run_id}
          onSelect={(runId) => setChosen([left.run_id, runId])}
        />
      </div>

      {sameRun ? (
        <p className={styles.summary} data-same-run="true">
          Слева и справа выбран один и тот же прогон, поэтому различий не будет.
        </p>
      ) : (
        <p
          className={styles.summary}
          data-difference-count={differences}
          data-compared-count={compared}
        >
          Сопоставлено признаков: {compared}. Различий среди них: {differences}.
        </p>
      )}

      <h3>Прогон целиком</h3>
      <div className={styles.scroller}>
        <table>
          <thead>
            <tr>
              <th scope="col">Признак</th>
              <th scope="col">Слева</th>
              <th scope="col">Справа</th>
              <th scope="col">Сопоставление</th>
            </tr>
          </thead>
          <tbody>
            {facts.map((row: ComparedFact) => (
              <tr key={row.factId} data-fact={row.factId} data-comparison={row.comparison}>
                <th scope="row" className={styles.factName}>
                  {FACT_LABELS[row.factId]}
                </th>
                <td>
                  <FactCell factId={row.factId} run={left} value={row.left} />
                </td>
                <td>
                  <FactCell factId={row.factId} run={right} value={row.right} />
                </td>
                <td className={styles.verdict}>{COMPARISON_LABELS[row.comparison]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>Этапы</h3>
      <div className={styles.scroller}>
        <table>
          <thead>
            <tr>
              <th scope="col">№</th>
              <th scope="col">Этап</th>
              <th scope="col">Слева</th>
              <th scope="col">Справа</th>
              <th scope="col">Сопоставление</th>
              <th scope="col">Длительность слева</th>
              <th scope="col">Длительность справа</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((row: ComparedStage) => (
              <tr key={row.stageId} data-stage-id={row.stageId} data-comparison={row.comparison}>
                <td className={styles.ordinal} data-stage-ordinal={row.ordinal ?? 'unscheduled'}>
                  {row.ordinal ?? '—'}
                </td>
                <td>
                  <span className={styles.stageName}>{STAGE_LABELS[row.stageId]}</span>
                  {row.expected ? null : (
                    <span className={styles.absent}> (на этом этапе не планируется)</span>
                  )}
                </td>
                <td>
                  <StageCell status={row.left.status} errorCode={row.left.errorCode} />
                </td>
                <td>
                  <StageCell status={row.right.status} errorCode={row.right.errorCode} />
                </td>
                <td className={styles.verdict}>{COMPARISON_LABELS[row.comparison]}</td>
                <td
                  className={styles.figure}
                  data-elapsed-ms={row.left.elapsedMs ?? 'unknown'}
                >
                  {formatElapsed(row.left.elapsedMs)}
                </td>
                <td
                  className={styles.figure}
                  data-elapsed-ms={row.right.elapsedMs ?? 'unknown'}
                  data-duration-comparison={row.durationComparison}
                >
                  {formatElapsed(row.right.elapsedMs)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="am-note">
        Здесь сравниваются те признаки прогона, которые система уже записывает. Разбор того,{' '}
        <em>что именно</em> изменилось внутри этапа — какие находки появились, исчезли или
        поменяли формулировку — появится позже. Пустая клетка означает, что прогон этого не
        сообщил: это честнее, чем правдоподобное число.
      </p>
    </div>
  );
}
