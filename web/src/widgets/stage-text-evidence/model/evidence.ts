import type {
  ComparisonBox, StageTextDifference, StageTextExclusion, StageTextFragment, StageTextHint,
} from '@/shared/api';

export interface StageTextEvidenceData {
  readonly fragments: readonly StageTextFragment[];
  readonly exclusions: readonly StageTextExclusion[];
  readonly differences: readonly StageTextDifference[];
  readonly hints: readonly StageTextHint[];
}

export interface PageTextItem {
  readonly id: string;
  readonly text: string;
  readonly box: ComparisonBox;
}

/** Later supplied by the stored page-word endpoint, without changing viewer state. */
export type PageTextProvider = (profileId: string, signal: AbortSignal) => Promise<readonly PageTextItem[]>;

export function fragmentBox(fragment: StageTextFragment): ComparisonBox | null {
  const anchor = fragment.box_anchor;
  const x = anchor.x0 ?? anchor.x;
  const y = anchor.top ?? anchor.y;
  const width = anchor.x1 === undefined ? anchor.width : anchor.x1 - (x ?? 0);
  const height = anchor.bottom === undefined ? anchor.height : anchor.bottom - (y ?? 0);
  if (x === undefined || y === undefined || width === undefined || height === undefined
      || ![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) return null;
  return { x, y, width, height };
}

export function pageText(fragments: readonly StageTextFragment[], profileId: string): PageTextItem[] {
  return fragments.flatMap((fragment) => {
    const box = fragmentBox(fragment);
    return fragment.profile_id === profileId && box !== null
      ? [{ id: fragment.fragment_id, text: fragment.text, box }] : [];
  }).sort((a, b) => a.box.y - b.box.y || a.box.x - b.box.x || a.id.localeCompare(b.id));
}

function plain(value: string): string {
  return value.normalize('NFKC').toLocaleLowerCase('ru').replaceAll('ё', 'е').trim();
}

export function searchPageText(items: readonly PageTextItem[], query: string): PageTextItem[] {
  const value = plain(query);
  return value === '' ? [] : items.filter((item) => plain(item.text).includes(value));
}

export function provenFragments(
  data: StageTextEvidenceData | undefined, profileId: string, side: 'left' | 'right',
): PageTextItem[] {
  if (data === undefined) return [];
  const ids = new Set(data.exclusions.map((row) => side === 'left' ? row.left_fragment_id : row.right_fragment_id));
  return pageText(data.fragments.filter((fragment) => ids.has(fragment.fragment_id)), profileId);
}

export function fragmentLookup(data: StageTextEvidenceData | undefined): ReadonlyMap<string, StageTextFragment> {
  return new Map(data?.fragments.map((fragment) => [fragment.fragment_id, fragment]) ?? []);
}
