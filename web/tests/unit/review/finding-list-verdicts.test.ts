/**
 * `UI-A-70`, `UI-A-71`: the finding list tallies the run's verdicts and filters by them. The page loads
 * every finding of the run (`R-150i`), so these are whole-run figures. `needs_manual_review` waits for the
 * expert like `pending`.
 */
import { describe, expect, it } from 'vitest';

import type { Finding } from '@/shared/api';
import type { FindingGroup } from '@/entities/finding';
import { filterGroups, tallyVerdicts, verdictBucket } from '@/widgets/finding-list';

function finding(uid: string, verdict: Finding['current_verdict']): Finding {
  return { finding_uid: uid, current_verdict: verdict } as unknown as Finding;
}

const GROUPS = [
  { category: 'internal_contradiction', findings: [finding('a', 'pending'), finding('b', 'accepted')] },
  { category: 'dimensions', findings: [finding('c', 'rejected'), finding('d', 'needs_manual_review')] },
  { category: 'norm_violation', findings: [finding('e', 'accepted')] },
] as unknown as FindingGroup<Finding>[];

describe('verdicts at a glance', () => {
  it('buckets needs_manual_review with pending', () => {
    expect(verdictBucket('pending')).toBe('waiting');
    expect(verdictBucket('needs_manual_review')).toBe('waiting');
    expect(verdictBucket('accepted')).toBe('accepted');
    expect(verdictBucket('rejected')).toBe('rejected');
  });

  it('tallies the whole run', () => {
    expect(tallyVerdicts(GROUPS)).toEqual({ waiting: 2, accepted: 2, rejected: 1 });
  });

  it('keeps every group under «Все», and drops a group the filter empties', () => {
    expect(filterGroups(GROUPS, 'all')).toBe(GROUPS);
    const accepted = filterGroups(GROUPS, 'accepted');
    expect(accepted.map((g) => g.category)).toEqual(['internal_contradiction', 'norm_violation']);
    expect(accepted.flatMap((g) => g.findings.map((f) => f.finding_uid))).toEqual(['b', 'e']);
    expect(filterGroups(GROUPS, 'waiting').flatMap((g) => g.findings.map((f) => f.finding_uid))).toEqual(['a', 'd']);
  });

  it('answers an empty list, not an error, when no finding has the verdict', () => {
    const onlyAccepted = [{ category: 'dimensions', findings: [finding('x', 'accepted')] }] as unknown as FindingGroup<Finding>[];
    expect(filterGroups(onlyAccepted, 'rejected')).toEqual([]);
  });
});

describe('the verdict filter read from the address', () => {
  it('reads a known value and opens active review by default', async () => {
    const { verdictFilterOf } = await import('@/widgets/finding-list');
    expect(verdictFilterOf('waiting')).toBe('waiting');
    expect(verdictFilterOf('accepted')).toBe('accepted');
    expect(verdictFilterOf('rejected')).toBe('rejected');
    expect(verdictFilterOf(null)).toBe('active');
    expect(verdictFilterOf('all')).toBe('all');
    expect(verdictFilterOf('active')).toBe('active');
    expect(verdictFilterOf('pending')).toBe('active');
  });
});
