import type { ComparisonBox, StageLinkInput } from '@/shared/api';

export interface StageMapFocus {
  readonly token: number;
  readonly pairId: string;
  readonly runId: string;
  readonly revisionId: string;
  readonly leftProfileId?: string;
  readonly rightProfileId?: string;
  readonly leftBox?: ComparisonBox;
  readonly rightBox?: ComparisonBox;
}

export function focusedRow(rows: readonly StageLinkInput[], focus: StageMapFocus | undefined): number | undefined {
  if (focus === undefined || (focus.leftProfileId === undefined && focus.rightProfileId === undefined)) return undefined;
  const exact = rows.findIndex((row) => (focus.leftProfileId === undefined || row.left_profile_id === focus.leftProfileId)
    && (focus.rightProfileId === undefined || row.right_profile_id === focus.rightProfileId));
  if (exact >= 0) return exact;
  const source = rows.findIndex((row) => focus.leftProfileId !== undefined
    ? row.left_profile_id === focus.leftProfileId : row.right_profile_id === focus.rightProfileId);
  return source < 0 ? undefined : source;
}
