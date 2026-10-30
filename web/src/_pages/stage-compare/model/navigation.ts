import type { ComparisonBox, StageCardEvidence, StageChainRun, StageChangeCard, StageLinkRevision, StageTextFragment } from '@/shared/api';
import type { StageMapFocus } from '@/widgets/stage-sheet-map';

export function anchorBox(anchor: Readonly<Record<string, number>> | undefined): ComparisonBox | undefined {
  if (anchor === undefined) return undefined;
  const x = anchor.x0 ?? anchor.x;
  const y = anchor.top ?? anchor.y;
  const width = anchor.x1 === undefined ? anchor.width : anchor.x1 - (x ?? 0);
  const height = anchor.bottom === undefined ? anchor.height : anchor.bottom - (y ?? 0);
  return x !== undefined && y !== undefined && width !== undefined && height !== undefined
    && [x, y, width, height].every(Number.isFinite) && width > 0 && height > 0
    ? { x, y, width, height } : undefined;
}

export function assertRunRevision(run: StageChainRun, revision: StageLinkRevision, pairId: string): void {
  if (run.pair_id !== pairId || revision.pair_id !== pairId
      || revision.revision_id !== (run.effective_link_revision_id ?? run.link_revision_id)) {
    throw new Error('Запуск и карта листов относятся к разным сравнениям. Выберите запуск заново.');
  }
}

export function evidenceFocus(run: StageChainRun, revision: StageLinkRevision, evidence: StageCardEvidence,
  card: StageChangeCard, token: number): StageMapFocus {
  assertRunRevision(run, revision, run.pair_id);
  if (card.run_id !== run.run_id || evidence.profile_id === undefined) throw new Error('Место на чертеже не связано с выбранным запуском.');
  const profileId = evidence.profile_id;
  const side = evidence.side === 'both'
    ? revision.items.some((item) => item.left_profile_id === profileId) ? 'left'
      : revision.items.some((item) => item.right_profile_id === profileId) ? 'right' : undefined
    : evidence.side;
  if (side === undefined) throw new Error('Сторона свидетельства не определена.');
  const row = revision.items.find((item) => side === 'left' ? item.left_profile_id === profileId : item.right_profile_id === profileId);
  if (row === undefined) throw new Error('Свидетельство отсутствует на указанной стороне сохранённой карты.');
  const opposite = (card.evidence ?? []).find((item) => item.source_id === evidence.source_id && item.side !== side && item.side !== 'both' && item.profile_id !== undefined);
  const leftId = side === 'left' ? profileId : opposite?.profile_id ?? row?.left_profile_id;
  const rightId = side === 'right' ? profileId : opposite?.profile_id ?? row?.right_profile_id;
  const box = anchorBox(evidence.box_anchor);
  const otherBox = anchorBox(opposite?.box_anchor);
  return { token, pairId: run.pair_id, runId: run.run_id, revisionId: revision.revision_id,
    ...(leftId === undefined ? {} : { leftProfileId: leftId }),
    ...(rightId === undefined ? {} : { rightProfileId: rightId }),
    ...(side === 'left' ? { ...(box === undefined ? {} : { leftBox: box }), ...(otherBox === undefined ? {} : { rightBox: otherBox }) }
      : { ...(box === undefined ? {} : { rightBox: box }), ...(otherBox === undefined ? {} : { leftBox: otherBox }) }) };
}

export function rawFocus(run: StageChainRun, revision: StageLinkRevision,
  left: StageTextFragment | undefined, right: StageTextFragment | undefined, token: number): StageMapFocus {
  assertRunRevision(run, revision, run.pair_id);
  if ((left === undefined && right === undefined) || (left !== undefined && (left.pair_id !== run.pair_id || left.side !== 'left'))
      || (right !== undefined && (right.pair_id !== run.pair_id || right.side !== 'right'))) {
    throw new Error('Сохранённые фрагменты этого запуска недоступны. Откройте место из карточки.');
  }
  const leftBox = anchorBox(left?.box_anchor);
  const rightBox = anchorBox(right?.box_anchor);
  return { token, pairId: run.pair_id, runId: run.run_id, revisionId: revision.revision_id,
    ...(left === undefined ? {} : { leftProfileId: left.profile_id }),
    ...(right === undefined ? {} : { rightProfileId: right.profile_id }),
    ...(leftBox === undefined ? {} : { leftBox }), ...(rightBox === undefined ? {} : { rightBox }) };
}
