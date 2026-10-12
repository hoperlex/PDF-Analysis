import type { ReleaseNoteKind } from '@/shared/api';
import { RELEASE_NOTE_KIND_VALUES } from '@/shared/api';

export const RELEASE_KIND_LABELS: Readonly<Record<ReleaseNoteKind, string>> = {
  new: 'Новое',
  improved: 'Улучшено',
  fixed: 'Исправлено',
};

/** The label of a kind this build does not know. Neither the raw value nor a guess at it. */
export const OTHER_RELEASE_KIND_LABEL = 'Другое изменение';

/** True for a kind of the contract's set. */
export function isKnownReleaseKind(value: unknown): value is ReleaseNoteKind {
  return (RELEASE_NOTE_KIND_VALUES as readonly unknown[]).includes(value);
}

/**
 * The label of a release-note kind. `C-29`: a kind outside the contract's set — a newer API
 * behind an older web build — gets the generic {@link OTHER_RELEASE_KIND_LABEL} instead of
 * throwing, which used to fail the whole history and «Что нового» for one item.
 */
export function releaseKindLabel(value: unknown): string {
  return isKnownReleaseKind(value) ? RELEASE_KIND_LABELS[value] : OTHER_RELEASE_KIND_LABEL;
}

/** Keep the authored calendar day, independently of the browser's time zone. */
export function releaseDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (match === null) throw new Error('Дата выпуска имеет неизвестный формат.');
  return `${match[3]}.${match[2]}.${match[1]}`;
}
