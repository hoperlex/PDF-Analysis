/**
 * Which analysis produced a run, and what a screen says about it (`AR-V3-OPT-IN`, design 4.4 and 4.6).
 *
 * Two analyses exist. The **standard** analysis is the one the imported profile of the section gives, and it is the
 * default of every start. **АР v3 (бета)** is one run of a group of six, started by its own operation and never by
 * default. A run holds exactly one of them and the server says which in `RunStatus.analysis_kind`; this module is the one
 * place the client reads it, so no screen compares a profile id by hand. A reading from a server that predates the field
 * carries none; its profile id is then the only thing to go by, and `AR_V3_BETA_PROFILE_ID` answers for it.
 *
 * What the screens say, and when:
 *
 *   - a v3 run is ALWAYS labelled «АР v3 (бета)» (with its scope, F1 to S2, where it has one): it is the run that is not
 *     the default, and it stays labelled when the deployment later stops allowing starts;
 *   - a standard run is labelled «Стандартный» only where both analyses are on offer on this server
 *     (`start_allowed`): naming the default on every row of a deployment that has no other would be noise.
 *
 * No wording here says the standard analysis is replaced, superseded or discouraged, and none says anything about review
 * by a human, so the label cannot collide with `SHOW_REVIEW_INDICATION` (`R-146ba`).
 */

import type { RunStatus } from '@/shared/api';

import { AR_V3_BETA_PROFILE_ID } from './run-presentation';

export type RunAnalysisKind = 'standard' | 'ar_v3_beta';

export const STANDARD_ANALYSIS_LABEL = 'Стандартный';
export const AR_V3_ANALYSIS_LABEL = 'АР v3 (бета)';

export type RunAnalysisFields = Pick<
  RunStatus,
  'analysis_kind' | 'analysis_profile_id' | 'ar_v3_group_id' | 'ar_v3_scope_id'
>;

export interface RunAnalysis {
  readonly kind: RunAnalysisKind;
  /** The sentence for a cell or a line: «Стандартный», «АР v3 (бета)» or «АР v3 (бета) · F1». */
  readonly label: string;
  /** The scope of a member of an AR v3 group, `null` for a standard run and for a v3 run that names none. */
  readonly scope: string | null;
  /** The group of a member, `null` where the reading names none. */
  readonly groupId: string | null;
}

export function runAnalysisKind(run: Pick<RunAnalysisFields, 'analysis_kind' | 'analysis_profile_id'>): RunAnalysisKind {
  if (run.analysis_kind !== undefined) return run.analysis_kind;
  return run.analysis_profile_id === AR_V3_BETA_PROFILE_ID ? 'ar_v3_beta' : 'standard';
}

export function runAnalysis(run: RunAnalysisFields): RunAnalysis {
  if (runAnalysisKind(run) === 'standard') {
    return { kind: 'standard', label: STANDARD_ANALYSIS_LABEL, scope: null, groupId: null };
  }
  const scope = run.ar_v3_scope_id ?? null;
  return {
    kind: 'ar_v3_beta',
    label: scope === null ? AR_V3_ANALYSIS_LABEL : `${AR_V3_ANALYSIS_LABEL} · ${scope}`,
    scope,
    groupId: run.ar_v3_group_id ?? null,
  };
}

/**
 * The label a run's row or page line shows, or `null` where it shows none: a v3 run always, a standard run only while
 * `bothOffered` (the deployment allows a start of v3, so the reader has two analyses to tell apart).
 */
export function runAnalysisLabel(run: RunAnalysisFields, bothOffered: boolean): RunAnalysis | null {
  const analysis = runAnalysis(run);
  return analysis.kind === 'ar_v3_beta' || bothOffered ? analysis : null;
}
