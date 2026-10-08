import type { ReleaseEntry, ReleaseNoteKind } from '@/shared/api';
import { RELEASE_NOTE_KIND_VALUES } from '@/shared/api';

export class UnknownReleaseKindError extends Error {
  constructor() {
    super('Категория изменения не распознана.');
    this.name = 'UnknownReleaseKindError';
  }
}

export const RELEASE_KIND_LABELS: Readonly<Record<ReleaseNoteKind, string>> = {
  new: 'Новое',
  improved: 'Улучшено',
  fixed: 'Исправлено',
};

export function releaseKindLabel(value: unknown): string {
  if (!(RELEASE_NOTE_KIND_VALUES as readonly unknown[]).includes(value)) {
    throw new UnknownReleaseKindError();
  }
  return RELEASE_KIND_LABELS[value as ReleaseNoteKind];
}

/** Keep the authored calendar day, independently of the browser's time zone. */
export function releaseDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (match === null) throw new Error('Дата выпуска имеет неизвестный формат.');
  return `${match[3]}.${match[2]}.${match[1]}`;
}

export function assertReleaseKinds(entries: readonly ReleaseEntry[]): void {
  for (const entry of entries) for (const item of entry.items) releaseKindLabel(item.kind);
}
