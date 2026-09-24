/**
 * What two runs of one published version can honestly be said to agree and disagree on.
 *
 * `R-23`: *«Сравнение стадий — очень важно; хотя бы скелет с заглушками сейчас, реализация
 * по ходу альфы.»* This module is the *shape* of that comparison — the part that can be
 * held by a test without a browser — and it is deliberately not a mechanism. It derives
 * nothing, fetches nothing and invents nothing: every fact it compares is a field the
 * contract already carries on `RunStatus`, and every value it puts in a row is a value one
 * of the two readings put there.
 *
 * ## Why there are FOUR verdicts and not two
 *
 * The obvious shape is `same | differs`, and it is wrong in the way `run-presentation.ts`
 * is already emphatic about: **an absent figure and a reported zero are different facts.**
 * `published_finding_count` is optional on the wire; a run that never reached publication
 * does not carry it, and a run that published nothing carries `0`. Folding the first into
 * the second is the `D-3` class of invention — an answer produced for a question nothing
 * was asked — and a comparison screen is exactly where it would do the most damage,
 * because "these two runs agree" is the sentence a reviewer would act on.
 *
 * So the verdict distinguishes four cases, and the screen says which one it is:
 *
 *   `same`        both readings carry the fact and the values are equal;
 *   `differs`     both readings carry the fact and the values are not equal;
 *   `one_sided`   exactly one reading carries it — which is a difference in what was
 *                 RECORDED, not a measured difference in the fact, and the two must not
 *                 be printed in the same words;
 *   `absent`      neither reading carries it. Not agreement: nothing was compared.
 *
 * `absent` is the one that would otherwise be silently wrong. Two `published` runs carry
 * no `terminal_reason` between them, and a row saying *«совпадает»* there would claim the
 * two runs agree about a failure neither of them had.
 *
 * ## Why the comparison is on the MACHINE value and never on the label
 *
 * `OPERATING_CONSTRAINTS.md` §12: a query that shares an assumption with its subject
 * cannot see the subject being wrong. The labels a comparison screen prints come from
 * `STATE_LABELS` and `STAGE_LABELS`; comparing the labels would mean two contract members
 * that happened to share a label would compare `same`. Every verdict below is taken on the
 * contract value, and the label is applied afterwards by the widget that renders it.
 *
 * ## What is NOT compared here, and why that is not an omission
 *
 * Nothing compares *findings*. `listRuns` carries `published_finding_count` and not the
 * findings, so a claim about which finding appeared or disappeared between two runs is not
 * in this data at any cost, and the addendum to `R-23` is explicit: an empty screen is more
 * honest than a plausible one. The screen says that deeper comparison arrives later, in a
 * reviewer's words; this module simply has no such function to call.
 */

import type { RunStatus, StageId, StageStatus } from '@/shared/api';

import type { StageRow } from './run-presentation';
import { STAGE_DEPENDS_ON, elapsedMs, runCost, stageRows } from './run-presentation';

/** What comparing one fact across two readings produced. */
export type Comparison = 'same' | 'differs' | 'one_sided' | 'absent';

/**
 * Compare one fact across two readings.
 *
 * `null` and `undefined` both mean *this reading does not carry the fact*; every other
 * value is compared with `Object.is`, which is strict equality with `NaN` folded — and a
 * `NaN` here would be a malformed reading rather than a figure, so treating two of them as
 * equal is the answer that does not invent a difference.
 */
export function compareReadings(left: unknown, right: unknown): Comparison {
  const hasLeft = left !== null && left !== undefined;
  const hasRight = right !== null && right !== undefined;
  if (!hasLeft && !hasRight) return 'absent';
  if (hasLeft !== hasRight) return 'one_sided';
  return Object.is(left, right) ? 'same' : 'differs';
}

/** The facts of a run this screen puts side by side. Each is a field of `RunStatus`. */
export type FactId =
  | 'state'
  | 'provider_mode'
  | 'created_at'
  | 'terminal_at'
  | 'duration'
  | 'published_finding_count'
  | 'diagnostic_observation_count'
  | 'model_call_count'
  | 'cost_micros'
  | 'terminal_reason'
  | 'terminal_detail';

/**
 * One row of the side-by-side.
 *
 * `left` and `right` carry the **machine** value, or `null` where the reading does not
 * carry the fact. The widget decides how each is printed; nothing here writes a label,
 * because a label is presentation and a stage id printed raw is `D-62`.
 */
export interface ComparedFact {
  readonly factId: FactId;
  readonly left: string | number | null;
  readonly right: string | number | null;
  readonly comparison: Comparison;
}

/**
 * How long a run took, from the two instants the contract carries.
 *
 * `elapsedMs` refuses a backwards pair, so a run whose stamps disagree contributes `null`
 * — an absent duration rather than a negative one — and the row reports that it could not
 * be compared instead of reporting a run that finished before it started.
 */
export function runElapsedMs(run: RunStatus): number | null {
  return elapsedMs(run.created_at, run.terminal_at ?? null);
}

/**
 * The cost a reading reports, or `null`.
 *
 * Routed through `runCost` rather than read off the field, so the two states that field
 * has beyond a number are kept: a run that made no provider call carries no cost at all,
 * and a reading that carries a cost without its call count is **unreadable** rather than
 * zero (`D-15`). Both come back `null` here, and the row then reads `one_sided` or
 * `absent` — never `same` against a real figure.
 */
export function comparableCostMicros(run: RunStatus): number | null {
  const reading = runCost(run);
  return reading.kind === 'reported' ? reading.micros : null;
}

/**
 * How many classifiers a reading's `terminal_detail` carries, or `null`.
 *
 * `D-46` added the object in wave 42 and the schema forbids an empty one: absent and
 * `{}` are the same fact and the contract spells it one way. So a count of `0` cannot
 * arrive, and `null` is the only absence.
 */
export function terminalDetailKeys(run: RunStatus): readonly string[] | null {
  const detail = run.terminal_detail;
  if (detail === null || detail === undefined) return null;
  const keys = Object.keys(detail).sort();
  return keys.length === 0 ? null : keys;
}

/**
 * The `terminal_detail` of a reading as one comparable string, or `null`.
 *
 * Keys sorted, so two readings that carry the same classifiers in a different order
 * compare `same` — the object is a bag of classifiers and its key order is not a fact
 * about the run.
 */
export function terminalDetailDigest(run: RunStatus): string | null {
  const detail = run.terminal_detail;
  const keys = terminalDetailKeys(run);
  if (detail === null || detail === undefined || keys === null) return null;
  return keys.map((key) => `${key}=${String(detail[key])}`).join(' ');
}

/**
 * The eleven facts, in the order a reviewer reads them: what the run IS, when it ran, what
 * it produced, what it cost, and why it stopped.
 */
export function comparedFacts(left: RunStatus, right: RunStatus): readonly ComparedFact[] {
  const fact = (
    factId: FactId,
    a: string | number | null | undefined,
    b: string | number | null | undefined,
  ): ComparedFact => ({
    factId,
    left: a ?? null,
    right: b ?? null,
    comparison: compareReadings(a, b),
  });

  return [
    fact('state', left.state, right.state),
    fact('provider_mode', left.provider_mode, right.provider_mode),
    fact('created_at', left.created_at, right.created_at),
    fact('terminal_at', left.terminal_at, right.terminal_at),
    fact('duration', runElapsedMs(left), runElapsedMs(right)),
    fact('published_finding_count', left.published_finding_count, right.published_finding_count),
    fact(
      'diagnostic_observation_count',
      left.diagnostic_observation_count,
      right.diagnostic_observation_count,
    ),
    fact('model_call_count', left.model_call_count, right.model_call_count),
    fact('cost_micros', comparableCostMicros(left), comparableCostMicros(right)),
    fact('terminal_reason', left.terminal_reason, right.terminal_reason),
    fact('terminal_detail', terminalDetailDigest(left), terminalDetailDigest(right)),
  ];
}

/** One run's side of a stage row. `null` status is a stage this run has not reported. */
export interface StageSide {
  readonly status: StageStatus | null;
  readonly errorCode: string | null;
  readonly elapsedMs: number | null;
}

/**
 * One stage, as the two runs reported it.
 *
 * `ordinal` and `dependsOn` come from `run-presentation.ts` and carry its rule unchanged:
 * the nine contract stages are a graph, so a stage PC-01 does not schedule has a
 * dependency and no position, and numbering it would assert an order the contract does
 * not declare.
 */
export interface ComparedStage {
  readonly stageId: StageId;
  readonly ordinal: number | null;
  readonly dependsOn: readonly StageId[];
  readonly expected: boolean;
  readonly left: StageSide;
  readonly right: StageSide;
  /** On the reported status. */
  readonly comparison: Comparison;
  /** On the elapsed span, separately: two stages can succeed at very different speeds. */
  readonly durationComparison: Comparison;
}

/**
 * One row per stage either run knows about.
 *
 * Built from `stageRows` on both sides, so the rule that a stage PC-01 schedules is a
 * visible row with no status rather than a missing row is inherited rather than restated.
 * A stage only one run reported is a row whose other side is empty — which is a fact worth
 * seeing and is exactly what `one_sided` is for.
 */
export function comparedStages(left: RunStatus, right: RunStatus): readonly ComparedStage[] {
  const leftRows = stageRows(left);
  const rightRows = stageRows(right);
  const byId = new Map<StageId, { ordinal: number | null; expected: boolean }>();
  const order: StageId[] = [];

  for (const row of [...leftRows, ...rightRows]) {
    if (byId.has(row.stageId)) continue;
    byId.set(row.stageId, { ordinal: row.ordinal, expected: row.expected });
    order.push(row.stageId);
  }

  const side = (rows: readonly StageRow[], stageId: StageId): StageSide => {
    const row = rows.find((candidate) => candidate.stageId === stageId);
    if (row === undefined) return { status: null, errorCode: null, elapsedMs: null };
    return {
      status: row.status,
      errorCode: row.errorCode,
      elapsedMs: elapsedMs(row.startedAt, row.finishedAt),
    };
  };

  return order.map((stageId) => {
    const leftSide = side(leftRows, stageId);
    const rightSide = side(rightRows, stageId);
    const known = byId.get(stageId);
    return {
      stageId,
      ordinal: known?.ordinal ?? null,
      dependsOn: STAGE_DEPENDS_ON[stageId],
      expected: known?.expected ?? false,
      left: leftSide,
      right: rightSide,
      comparison: compareReadings(leftSide.status, rightSide.status),
      durationComparison: compareReadings(leftSide.elapsedMs, rightSide.elapsedMs),
    };
  });
}

/**
 * The two runs a freshly opened comparison shows.
 *
 * **The order is the server's, not this module's.** `listRuns` is declared *"List the runs
 * of one published version, newest first"*, so the two newest runs are the first two items
 * and nothing here re-sorts them. Re-deriving the order from `created_at` would be a
 * second opinion about a question the contract already answers, and two runs started in
 * the same millisecond would then be ordered by whichever comparator this file happened to
 * pick.
 *
 * `null` when the version has fewer than two runs, which is a screen state rather than an
 * error: one run has nothing to be compared against.
 */
export function defaultPair(runs: readonly RunStatus[]): readonly [RunStatus, RunStatus] | null {
  const [newest, previous] = runs;
  if (newest === undefined || previous === undefined) return null;
  return [previous, newest];
}

/**
 * How many of the compared facts differ, counting only the facts that were compared.
 *
 * `one_sided` counts as a difference and `absent` counts as nothing: a fact neither
 * reading carries was not compared, and including it in a denominator would make a
 * summary sentence drift with the contract's optional fields rather than with the runs.
 */
export function differenceCount(facts: readonly ComparedFact[]): number {
  return facts.filter((row) => row.comparison === 'differs' || row.comparison === 'one_sided')
    .length;
}

/** How many of the compared facts were actually comparable — `absent` rows excluded. */
export function comparedCount(facts: readonly ComparedFact[]): number {
  return facts.filter((row) => row.comparison !== 'absent').length;
}
