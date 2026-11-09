/**
 * The tabs of a version, as the original's strip «Инфо · Блоки · Замечания · Оптимизация» in our nouns
 * (`UI-A-22`, `R-151m`): «Версия», «Блоки», «Разбор» with the number of findings of the latest result, «Оптимизация».
 *
 * Pure, so the claim is a function a test calls. «Разбор» opens the version's **latest result run** (the newest run
 * that published a result, the rule the audit chip uses, `R-150s`); with no such run it is a label that says why it
 * is not a link rather than a link to nowhere. On a run and on the «Разбор» of one the tabs stay, as the original's strip stays on every view of its project: the run opens none, «Разбор» is the open one. «Оптимизация» is the document's own tab (`R-151r`).
 */

import type { RunStatus } from '@/shared/api';
import { routes } from '@/shared/lib';
import { runHasPublishedResult } from '@/entities/audit-run';

export type VersionTabKey = 'version' | 'blocks' | 'review' | 'optimisation';

export interface VersionTab {
  readonly key: VersionTabKey;
  readonly label: string;
  /** `null` when the tab is not reachable (no result run yet) or is the page itself. */
  readonly href: string | null;
  readonly current: boolean;
  /** The finding count of «Разбор», when the run says it. */
  readonly count: number | null;
  /** Said when the tab is not a link and the reason is worth a sentence. */
  readonly title: string | null;
}

export interface VersionTabFacts {
  readonly projectUid: string;
  readonly versionUid: string;
  readonly documentUid: string | undefined;
  /** The version's runs, newest first, or `undefined` while they are not known. */
  readonly runs: readonly RunStatus[] | undefined;
  /** The level of the page the tabs are on; a run is under the version and opens no tab. */
  readonly current: 'version' | 'blocks' | 'run' | 'review';
}

/** The newest run that published a result, or `null`. The list is the server's, newest first. */
export function latestResultRun(runs: readonly RunStatus[] | undefined): RunStatus | null {
  return runs?.find((run) => runHasPublishedResult(run.state, run.analysis_profile_id)) ?? null;
}

export function versionTabs(facts: VersionTabFacts): readonly VersionTab[] {
  const result = latestResultRun(facts.runs);
  const tabs: VersionTab[] = [
    {
      key: 'version',
      label: 'Версия',
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
      count: null,
      title: null,
    },
    {
      key: 'review',
      label: 'Разбор',
      href: facts.current === 'review' || result === null ? null : routes.review(facts.projectUid, result.run_id),
      current: facts.current === 'review',
      count: result?.published_finding_count ?? null,
      title: result !== null
        ? 'Замечания последнего прогона с результатом'
        : facts.runs === undefined ? null : 'У версии ещё нет прогона с результатом',
    },
  ];
  if (facts.documentUid !== undefined) {
    tabs.push({
      key: 'optimisation',
      label: 'Оптимизация',
      href: `${routes.document(facts.projectUid, facts.documentUid)}?tab=optimisation`,
      current: false,
      count: null,
      title: 'Оптимизация документа',
    });
  }
  return tabs;
}
