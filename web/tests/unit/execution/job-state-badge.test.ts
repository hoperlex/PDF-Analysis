/**
 * `UI-B-50`: a job's state is a coloured badge in the run badge's tones.
 */
import { describe, expect, it } from 'vitest';

import { jobStateTone } from '@/entities/execution';

describe('jobStateTone', () => {
  it('maps every job state onto a run-badge tone', () => {
    expect(jobStateTone('queued')).toBe('pending');
    expect(jobStateTone('retry_wait')).toBe('pending');
    expect(jobStateTone('leased')).toBe('active');
    expect(jobStateTone('running')).toBe('active');
    expect(jobStateTone('succeeded')).toBe('ok');
    expect(jobStateTone('failed')).toBe('failed');
    expect(jobStateTone('dead_letter')).toBe('failed');
    expect(jobStateTone('cancelled')).toBe('inert');
  });

  it('gives a state it does not know the inert tone', () => {
    expect(jobStateTone('something_new')).toBe('inert');
  });
});
