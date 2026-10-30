import type { StageLinkInput } from '@/shared/api';

type Side = 'left' | 'right';
type Row = { left_profile_id?: string; right_profile_id?: string };

function relation(row: Row): StageLinkInput {
  if (row.left_profile_id !== undefined && row.right_profile_id !== undefined) {
    return { relation: 'paired', left_profile_id: row.left_profile_id, right_profile_id: row.right_profile_id };
  }
  if (row.left_profile_id !== undefined) return { relation: 'only_left', left_profile_id: row.left_profile_id };
  return { relation: 'only_right', right_profile_id: row.right_profile_id! };
}

/** Move one profile; a displaced page takes the nearest empty place below the target. */
export function moveSheet(
  input: readonly StageLinkInput[], side: Side, profileId: string, target: number,
): StageLinkInput[] {
  if (target < 0 || target >= input.length) return [...input];
  const field = side === 'left' ? 'left_profile_id' : 'right_profile_id';
  const source = input.findIndex((row) => row[field] === profileId);
  if (source < 0 || source === target) return [...input];
  const rows: Row[] = input.map((row) => ({
    ...(row.left_profile_id === undefined ? {} : { left_profile_id: row.left_profile_id }),
    ...(row.right_profile_id === undefined ? {} : { right_profile_id: row.right_profile_id }),
  }));
  const targetRow = rows[target]!;
  const displaced = targetRow[field];
  delete rows[source]![field];
  targetRow[field] = profileId;
  if (displaced !== undefined) {
    const free = rows.findIndex((row, index) => index > target && row[field] === undefined);
    if (free < 0) {
      if (!rows.some((row, index) => index !== target && row[field] === displaced)) {
        rows.push({ [field]: displaced });
      }
    }
    else rows[free]![field] = displaced;
  }
  return rows.filter((row) => row.left_profile_id !== undefined || row.right_profile_id !== undefined).map(relation);
}

/** An unplaced page remains an explicit no-pair row in the saved complete map. */
export function addUnpaired(
  input: readonly StageLinkInput[], side: Side, profileId: string,
): StageLinkInput[] {
  if (input.some((row) => row.left_profile_id === profileId || row.right_profile_id === profileId)) {
    return [...input];
  }
  return [...input, side === 'left'
    ? { relation: 'only_left', left_profile_id: profileId }
    : { relation: 'only_right', right_profile_id: profileId }];
}

/** Removing a link keeps both sheets as explicit no-pair decisions. */
export function unlinkRow(input: readonly StageLinkInput[], index: number): StageLinkInput[] {
  const selected = input[index];
  if (selected === undefined || selected.relation !== 'paired'
      || selected.left_profile_id === undefined || selected.right_profile_id === undefined) {
    return [...input];
  }
  const remaining = input.filter((_item, position) => position !== index);
  const replacement: StageLinkInput[] = [];
  if (!remaining.some((row) => row.left_profile_id === selected.left_profile_id)) {
    replacement.push({ relation: 'only_left', left_profile_id: selected.left_profile_id });
  }
  if (!remaining.some((row) => row.right_profile_id === selected.right_profile_id)) {
    replacement.push({ relation: 'only_right', right_profile_id: selected.right_profile_id });
  }
  return [...input.slice(0, index), ...replacement, ...input.slice(index + 1)];
}

/** A cross-sheet hint edits a draft only; displaced sheets stay explicitly unmatched. */
export function applyTextHint(
  input: readonly StageLinkInput[], leftProfileId: string, rightProfileId: string,
  mode: 'add' | 'replace',
): StageLinkInput[] {
  const removed = mode === 'replace' ? input.filter((row) => row.left_profile_id === leftProfileId) : [];
  const remaining = input.filter((row) => !(
    (mode === 'replace' && row.left_profile_id === leftProfileId)
    || (row.relation === 'only_left' && row.left_profile_id === leftProfileId)
    || (row.relation === 'only_right' && row.right_profile_id === rightProfileId)
  ));
  const result: StageLinkInput[] = remaining.some((row) => row.left_profile_id === leftProfileId
    && row.right_profile_id === rightProfileId) ? [...remaining]
    : [...remaining, { relation: 'paired', left_profile_id: leftProfileId, right_profile_id: rightProfileId }];
  for (const row of removed) {
    if (row.right_profile_id !== undefined && row.right_profile_id !== rightProfileId
        && !result.some((held) => held.right_profile_id === row.right_profile_id)) {
      result.push({ relation: 'only_right', right_profile_id: row.right_profile_id });
    }
  }
  return result;
}
