/**
 * `RUN-SCREEN-01a`: the rail reads the extended review's saved reading without asking for it again.
 *
 * The review panel owns the read and its polling; the run screen subscribes to the same query entry with `skipToken`, which never
 * fetches. Two observers on one key are the whole mechanism, so it is measured with two observers: the passive one sees what the
 * panel's fetch brings, and the endpoint is asked once.
 */

import { QueryClient, QueryObserver, skipToken } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';

import type { ExtendedRunReview } from '@/shared/api';
import { extendedReviewKey } from '@/widgets/extended-review';

const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const READING: ExtendedRunReview = { run_id: RUN, status: 'running', result: { procedures: [{ id: 'block_analysis', title: 'Анализ блоков', status: 'running' }] } };
const flush = () => new Promise((done) => setTimeout(done, 0));

describe('the passive reading of the review panel\'s query', () => {
  it('shares the panel\'s key', () => {
    expect(extendedReviewKey(RUN)).toEqual(['extended-run-review', RUN]);
  });

  it('sees the panel\'s fetch, and fetches nothing itself, whichever observer mounts first', async () => {
    for (const passiveFirst of [true, false]) {
      const client = new QueryClient();
      let asked = 0;
      const queryFn = async (): Promise<ExtendedRunReview> => { asked += 1; return READING; };
      const passive = new QueryObserver<ExtendedRunReview>(client, { queryKey: extendedReviewKey(RUN), queryFn: skipToken });
      const panel = new QueryObserver<ExtendedRunReview>(client, { queryKey: extendedReviewKey(RUN), queryFn });
      const stops: (() => void)[] = [];
      if (passiveFirst) stops.push(passive.subscribe(() => undefined));
      await flush();
      expect(asked, 'the passive observer asked').toBe(0);
      expect(passive.getCurrentResult().data).toBeUndefined();
      stops.push(panel.subscribe(() => undefined));
      if (!passiveFirst) stops.push(passive.subscribe(() => undefined));
      await flush();
      await flush();
      expect(asked).toBe(1);
      expect(passive.getCurrentResult().data).toEqual(READING);
      for (const stop of stops) stop();
    }
  });
});
