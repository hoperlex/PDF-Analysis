import { getStageSynthesis, listStageCardVerdicts, listStageChangeCards } from '@/shared/api';
import type { StageAiSynthesis, StageCardVerdict, StageChangeCard } from '@/shared/api';

export const STAGE_REVIEW_KEYS = {
  cards: (runId: string) => ['stage-changes', runId, 'cards'] as const,
  journal: (runId: string) => ['stage-journal', runId] as const,
};

export async function readCards(runId: string): Promise<{ cards: StageChangeCard[]; counts: Record<string, number> }> {
  const cards: StageChangeCard[] = [];
  let counts: Record<string, number> = {};
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const answer = (await listStageChangeCards({ path: { stage_chain_run_id: runId },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    cards.push(...answer.items);
    counts = answer.counts;
    cursor = answer.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список изменений обновился. Откройте его заново.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return { cards, counts };
}

export async function readSyntheses(runId: string): Promise<StageAiSynthesis[]> {
  const items: StageAiSynthesis[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const answer = (await getStageSynthesis({ path: { stage_chain_run_id: runId },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    for (const item of answer.items) {
      if (!['REAL_CHANGE', 'DETAIL_ONLY', 'NO_HIGH_LEVEL_CHANGE', 'INSUFFICIENT_CONTEXT'].includes(item.result.decision)) {
        throw new Error('Результат обобщения не распознан. Обновите сравнение.');
      }
    }
    items.push(...answer.items);
    cursor = answer.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список обобщений обновился. Откройте его заново.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items;
}

export async function readVerdicts(cardId: string): Promise<StageCardVerdict[]> {
  const items: StageCardVerdict[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const answer = (await listStageCardVerdicts({ path: { stage_change_card_id: cardId },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    items.push(...answer.items);
    cursor = answer.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('История решений обновилась. Откройте её заново.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items;
}
