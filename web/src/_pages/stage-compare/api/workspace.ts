import { getStageProfileText, listStageChainRuns, listStagePairs } from '@/shared/api';
import type { StageChainRun, StagePair, StageProfileText } from '@/shared/api';
import type { PageTextItem, PageTextProvider } from '@/widgets/stage-text-evidence';

export async function readStagePairs(projectUid: string): Promise<StagePair[]> {
  const items: StagePair[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const page = (await listStagePairs({ path: { project_uid: projectUid }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    if (page.items.some((pair) => pair.project_uid !== projectUid)) throw new Error('Получены пары другого проекта.');
    items.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список пар обновился. Повторите запрос.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items;
}

export async function readStageRunOptions(pairId: string): Promise<StageChainRun[]> {
  const items: StageChainRun[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const page = (await listStageChainRuns({ path: { stage_pair_id: pairId }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    if (page.items.some((run) => run.pair_id !== pairId)) throw new Error('Получены запуски другой пары.');
    items.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список запусков обновился. Повторите запрос.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items.sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

/** Stored words become display/search lines; these keys identify decorations, never domain entities. */
export function profileTextItems(profile: StageProfileText): PageTextItem[] {
  const words = profile.words.filter((word) => [word.x0, word.top, word.x1, word.bottom].every(Number.isFinite)
    && word.x1 > word.x0 && word.bottom > word.top && word.text.trim() !== '')
    .sort((a, b) => a.top - b.top || a.x0 - b.x0);
  const lines: Array<{ words: typeof words; centre: number; height: number }> = [];
  for (const word of words) {
    const centre = (word.top + word.bottom) / 2;
    const last = lines.at(-1);
    if (last !== undefined && Math.abs(last.centre - centre) <= Math.max(1, Math.min(last.height, word.bottom - word.top) * .45)) last.words.push(word);
    else lines.push({ words: [word], centre, height: word.bottom - word.top });
  }
  return lines.map((line, index) => {
    const sorted = line.words.sort((a, b) => a.x0 - b.x0);
    const x = Math.min(...sorted.map((word) => word.x0));
    const y = Math.min(...sorted.map((word) => word.top));
    return { id: `stored-line:${index}`, text: sorted.map((word) => word.text).join(' '),
      box: { x, y, width: Math.max(...sorted.map((word) => word.x1)) - x, height: Math.max(...sorted.map((word) => word.bottom)) - y } };
  });
}

export const storedPageText: PageTextProvider = async (profileId, signal) => {
  const profile = (await getStageProfileText({ path: { comparison_page_profile_id: profileId } }, { signal })).data;
  if (profile.profile_id !== profileId) throw new Error('Получен текст другого листа.');
  return profileTextItems(profile);
};
