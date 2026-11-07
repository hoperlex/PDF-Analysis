/**
 * What the journal's filters keep of the events already read (`UI-A-94`).
 *
 * The server filters nothing here: `listAuthEvents` takes a cursor and a limit and answers newest first. So the filters narrow
 * the events in hand, and the screen says that they do. A kind, the words of a name (the account's label or the administrator's,
 * in any case and order) and a range of UTC days, the days the times of the list are written in. A day is `YYYY-MM-DD`, as an
 * `<input type="date">` gives it; an empty bound is no bound.
 */

import type { AuthEvent, AuthEventType } from '@/shared/api';

export interface AuthEventFilter {
  readonly type: AuthEventType | '';
  readonly text: string;
  /** The first UTC day kept, or `''`. */
  readonly from: string;
  /** The last UTC day kept, or `''`. */
  readonly to: string;
}

export const NO_AUTH_EVENT_FILTER: AuthEventFilter = { type: '', text: '', from: '', to: '' };

export function isFiltering(filter: AuthEventFilter): boolean {
  return filter.type !== '' || filter.text.trim() !== '' || filter.from !== '' || filter.to !== '';
}

function utcDay(instant: string): string | null {
  const parsed = new Date(instant);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString().slice(0, 10);
}

function normal(value: string | null): string {
  return (value ?? '').toLocaleLowerCase('ru-RU');
}

export function filterAuthEvents(items: readonly AuthEvent[], filter: AuthEventFilter): readonly AuthEvent[] {
  const words = normal(filter.text).split(/\s+/).filter((word) => word !== '');
  return items.filter((event) => {
    if (filter.type !== '' && event.event_type !== filter.type) return false;
    if (filter.from !== '' || filter.to !== '') {
      const day = utcDay(event.occurred_at);
      // An event whose time cannot be read is kept out of a dated range rather than guessed into it.
      if (day === null) return false;
      if (filter.from !== '' && day < filter.from) return false;
      if (filter.to !== '' && day > filter.to) return false;
    }
    if (words.length > 0) {
      const names = `${normal(event.subject_label)} ${normal(event.actor_label)}`;
      if (!words.every((word) => names.includes(word))) return false;
    }
    return true;
  });
}
