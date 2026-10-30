import { describe, expect, it } from 'vitest';

import { addUnpaired, moveSheet, unlinkRow } from '@/widgets/stage-sheet-map/model/draft';

describe('stage sheet draft moves', () => {
  it('puts a displaced page in the nearest free row below the target', () => {
    const rows = [
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_b' },
      { relation: 'only_left', left_profile_id: 'cpr_c' },
      { relation: 'only_right', right_profile_id: 'cpr_d' },
    ] as const;
    expect(moveSheet(rows, 'right', 'cpr_d', 0)).toEqual([
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_d' },
      { relation: 'paired', left_profile_id: 'cpr_c', right_profile_id: 'cpr_b' },
    ]);
  });

  it('keeps a displaced page explicitly unpaired when there is no free place below', () => {
    const rows = [
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_c' },
      { relation: 'only_left', left_profile_id: 'cpr_b' },
    ] as const;
    expect(moveSheet(rows, 'left', 'cpr_a', 1)).toEqual([
      { relation: 'only_right', right_profile_id: 'cpr_c' },
      { relation: 'only_left', left_profile_id: 'cpr_a' },
      { relation: 'only_left', left_profile_id: 'cpr_b' },
    ]);
    expect(addUnpaired([], 'right', 'cpr_z')).toEqual([
      { relation: 'only_right', right_profile_id: 'cpr_z' },
    ]);
  });

  it('turns a removed link into two explicit no-pair rows', () => {
    expect(unlinkRow([
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_b' },
    ], 0)).toEqual([
      { relation: 'only_left', left_profile_id: 'cpr_a' },
      { relation: 'only_right', right_profile_id: 'cpr_b' },
    ]);
    expect(unlinkRow([
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_b' },
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_c' },
    ], 0)).toEqual([
      { relation: 'only_right', right_profile_id: 'cpr_b' },
      { relation: 'paired', left_profile_id: 'cpr_a', right_profile_id: 'cpr_c' },
    ]);
  });
});
