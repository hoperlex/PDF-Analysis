/**
 * `AR-V3-OPT-IN` (design 4.4 and 4.6): which analysis produced a run, and when a screen says so.
 *
 * The server says it in `RunStatus.analysis_kind`; the client reads it in one place (`runAnalysis`). A reading from a
 * server that predates the field is judged by its profile id, the only thing it carries. A v3 run is ALWAYS named; a
 * standard run only where both analyses are on offer. No label says anything about review by a human.
 */

import { describe, expect, it } from 'vitest';

import type { RunStatus } from '@/shared/api';
import {
  AR_V3_ANALYSIS_LABEL,
  AR_V3_BETA_PROFILE_ID,
  STANDARD_ANALYSIS_LABEL,
  runAnalysis,
  runAnalysisKind,
  runAnalysisLabel,
} from '@/entities/audit-run';

type Fields = Pick<RunStatus, 'analysis_kind' | 'analysis_profile_id' | 'ar_v3_group_id' | 'ar_v3_scope_id'>;

const GROUP = 'arg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as NonNullable<RunStatus['ar_v3_group_id']>;
const STANDARD: Fields = { analysis_kind: 'standard' };
const MEMBER: Fields = { analysis_kind: 'ar_v3_beta', ar_v3_group_id: GROUP, ar_v3_scope_id: 'F1' };

describe('what a run is', () => {
  it('reads the server’s word', () => {
    expect(runAnalysisKind(STANDARD)).toBe('standard');
    expect(runAnalysisKind(MEMBER)).toBe('ar_v3_beta');
  });

  it('trusts the server’s word over the profile id it came with', () => {
    expect(runAnalysisKind({ analysis_kind: 'standard', analysis_profile_id: AR_V3_BETA_PROFILE_ID as never })).toBe('standard');
    expect(runAnalysisKind({ analysis_kind: 'ar_v3_beta', analysis_profile_id: 'ap_01M5AXG1K22R027A33VTKZ468P' as never })).toBe(
      'ar_v3_beta',
    );
  });

  it('falls back on the profile id for a server that does not send the field, and on nothing else', () => {
    expect(runAnalysisKind({ analysis_profile_id: AR_V3_BETA_PROFILE_ID as never })).toBe('ar_v3_beta');
    expect(runAnalysisKind({ analysis_profile_id: 'ap_01M5AXG1K22R027A33VTKZ468P' as never })).toBe('standard');
    expect(runAnalysisKind({})).toBe('standard');
  });
});

describe('what a screen says of it', () => {
  it('names a member with its scope and its group', () => {
    expect(runAnalysis(MEMBER)).toEqual({ kind: 'ar_v3_beta', label: 'АР v3 (бета) · F1', scope: 'F1', groupId: GROUP });
    expect(runAnalysis({ analysis_kind: 'ar_v3_beta' })).toEqual({
      kind: 'ar_v3_beta', label: AR_V3_ANALYSIS_LABEL, scope: null, groupId: null,
    });
  });

  it('names a standard run «Стандартный», with no scope and no group', () => {
    expect(runAnalysis({ ...STANDARD, ar_v3_group_id: GROUP, ar_v3_scope_id: 'F2' })).toEqual({
      kind: 'standard', label: STANDARD_ANALYSIS_LABEL, scope: null, groupId: null,
    });
  });

  it('always labels a v3 run, whether or not a start of v3 is allowed', () => {
    expect(runAnalysisLabel(MEMBER, false)?.label).toBe('АР v3 (бета) · F1');
    expect(runAnalysisLabel(MEMBER, true)?.label).toBe('АР v3 (бета) · F1');
  });

  it('labels a standard run only where both analyses are on offer', () => {
    expect(runAnalysisLabel(STANDARD, false)).toBeNull();
    expect(runAnalysisLabel(STANDARD, true)?.label).toBe('Стандартный');
  });

  it('says nothing about review, replacement or preference', () => {
    const sentences = [AR_V3_ANALYSIS_LABEL, STANDARD_ANALYSIS_LABEL, runAnalysis(MEMBER).label].join(' ').toLowerCase();
    for (const word of ['провер', 'эксперт', 'замен', 'лучш', 'устар', 'рекоменд', 'предварит']) {
      expect(sentences, word).not.toContain(word);
    }
  });
});
