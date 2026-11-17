/**
 * The tabs of a version, as the original's strip «Инфо · Блоки N · Лог · Замечания N · Оптимизация N» in our nouns
 * (`UI-A-22`, `R-151m`; the words by `UIP-G-02`, the frame by `UIP-G-09`): «Инфо», «Блоки», «Лог», «Разбор» with the
 * number of findings of the latest result, «Оптимизация» with the number of proposals of the version's latest pass.
 *
 * Pure, so the claim is a function a test calls. «Разбор» opens the version's **latest result run** (the newest run
 * that published a result, the rule the audit chip uses, `R-150s`); with no such run it is a label that says why it
 * is not a link rather than a link to nowhere. «Лог» opens the **latest run** of any state, on its journal, and says
 * the same when the version has none; it is the operator's tab (`R-150w`), absent for a read-only account. On a run and
 * on the «Разбор» of one the tabs stay, as the original's strip stays on every view of its project: the run opens none,
 * «Разбор» is the open one. «Оптимизация» is the document's own tab (`R-151r`), so on the document page it is the open
 * one when the address says `?tab=optimisation`.
 *
 * The numbers are the frame's to show and not always its to read: «Разбор» comes from the version's runs, which the tabs
 * read anyway; «Блоки» and «Оптимизация» come from the one read of the version itself (`UIP-S04-02`, `versionFigures`): the
 * portal blocks it counts and the proposals of its latest optimisation pass. A number the server did not give is no number
 * and never a zero.
 */

import type { DocumentAudit, DocumentVersion, RunStatus } from '@/shared/api';
import { routes } from '@/shared/lib';
import { runHasPublishedResult } from '@/entities/audit-run';

export type VersionTabKey = 'version' | 'blocks' | 'log' | 'review' | 'optimisation';

/**
 * Where the frame stands: one of the tabs, or a place that is under the version and opens none (a run, the document's
 * own page with its versions).
 */
export type TabLevel = 'document' | 'optimisation' | 'version' | 'blocks' | 'log' | 'run' | 'review';

export interface VersionTab {
  readonly key: VersionTabKey;
  readonly label: string;
  /** `null` when the tab is not reachable (no run yet) or is the page itself. */
  readonly href: string | null;
  readonly current: boolean;
  /** The number the tab carries: findings of the latest result, blocks of the version, proposals of the latest pass. */
  readonly count: number | null;
  /** Said when the tab is not a link and the reason is worth a sentence, or when the number has a second one. */
  readonly title: string | null;
}

/**
 * The version's latest optimisation pass as the tab reads it: all its proposals, and those with no decision in force
 * (`null` when the server did not say).
 */
export interface OptimisationCount {
  readonly proposals: number;
  readonly undecided: number | null;
}

/** The two figures of the tabs that the version read carries: the blocks of the version, and its optimisation pass. */
export interface VersionFigures {
  /** The version's portal blocks; absent is not zero (no run has built the index yet). */
  readonly blockCount: number | undefined;
  /** The version's latest pass, or `null` when none was started over it. */
  readonly optimisation: OptimisationCount | null;
}

/**
 * The proposals of the version's latest pass, from the audit the version read carries (`UIP-S04-01`): both counts are
 * present when a pass was started over the version and both absent when none was. No proposal count is no pass, never a
 * zero; a pass whose undecided count is missing still shows its proposals and says nothing of the undecided.
 */
export function optimisationOf(audit: DocumentAudit | undefined): OptimisationCount | null {
  const proposals = audit?.optimisation_proposal_count;
  if (proposals === undefined) return null;
  return { proposals, undecided: audit?.optimisation_undecided_count ?? null };
}

/** The figures of the tabs, from the version's own read: one source for both numbers. */
export function versionFigures(version: DocumentVersion): VersionFigures {
  return { blockCount: version.block_count, optimisation: optimisationOf(version.audit) };
}

export interface VersionTabFacts {
  readonly projectUid: string;
  readonly versionUid: string;
  readonly documentUid: string | undefined;
  /** The version's runs, newest first, or `undefined` while they are not known. */
  readonly runs: readonly RunStatus[] | undefined;
  /** The level of the page the tabs are on. */
  readonly current: TabLevel;
  /** The version's portal blocks, from the version's read (`UIP-S04-02`); absent is not zero. */
  readonly blockCount?: number | undefined;
  /** The version's latest pass, or `null` when it has none, or `undefined` while it is not known. */
  readonly optimisation?: OptimisationCount | null | undefined;
  /** Whether this account reads the journal (`R-150w`); an account not known yet is left to the server. */
  readonly mayReadLog?: boolean | undefined;
}

/** The newest run that published a result, or `null`. The list is the server's, newest first. */
export function latestResultRun(runs: readonly RunStatus[] | undefined): RunStatus | null {
  return runs?.find((run) => runHasPublishedResult(run.state)) ?? null;
}

/** The journal of a run: the run's own page on its journal (`UIP-G-09`), the operator's reading of it. */
export function runLogAddress(projectUid: string, runId: string): string {
  return `${routes.run(projectUid, runId)}?tab=journal`;
}

/** The roles that read a run's journal (`R-150w`); an account not known yet is left to the server. */
export function mayReadLogOf(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}

export function versionTabs(facts: VersionTabFacts): readonly VersionTab[] {
  const result = latestResultRun(facts.runs);
  const latest = facts.runs?.[0] ?? null;
  const tabs: VersionTab[] = [
    {
      key: 'version',
      label: 'Инфо',
      href: facts.current === 'version' ? null : routes.version(facts.projectUid, facts.versionUid),
      current: facts.current === 'version',
      count: null,
      title: null,
    },
    {
      key: 'blocks',
      label: 'Блоки',
      href: facts.current === 'blocks' ? null : routes.versionBlocks(facts.projectUid, facts.versionUid),
      current: facts.current === 'blocks',
      count: facts.blockCount ?? null,
      title: null,
    },
  ];
  if (facts.mayReadLog !== false) {
    tabs.push({
      key: 'log',
      label: 'Лог',
      href: facts.current === 'log' || latest === null ? null : runLogAddress(facts.projectUid, latest.run_id),
      current: facts.current === 'log',
      count: null,
      title: latest !== null
        ? 'Журнал последнего прогона версии'
        : facts.runs === undefined ? null : 'У версии ещё не было прогонов',
    });
  }
  tabs.push({
    key: 'review',
    label: 'Разбор',
    href: facts.current === 'review' || result === null ? null : routes.review(facts.projectUid, result.run_id),
    current: facts.current === 'review',
    count: result?.published_finding_count ?? null,
    title: result !== null
      ? 'Замечания последнего прогона с результатом'
      : facts.runs === undefined ? null : 'У версии ещё нет прогона с результатом',
  });
  if (facts.documentUid !== undefined) {
    const pass = facts.optimisation ?? null;
    tabs.push({
      key: 'optimisation',
      label: 'Оптимизация',
      href: facts.current === 'optimisation' ? null : routes.documentOptimisation(facts.projectUid, facts.documentUid),
      current: facts.current === 'optimisation',
      count: pass?.proposals ?? null,
      title: pass === null
        ? 'Оптимизация документа'
        : pass.undecided === null
          ? `Предложений последнего прохода: ${pass.proposals}`
          : `Предложений последнего прохода: ${pass.proposals}, из них без решения: ${pass.undecided}`,
    });
  }
  return tabs;
}
