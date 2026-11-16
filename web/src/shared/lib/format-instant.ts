/**
 * Every moment of time the screens print, in one place (`UIP-G-13`, poll 2: the original's way).
 *
 * A moment is shown in the BROWSER'S local time, as the original shows it: `ДД.ММ.ГГГГ ЧЧ:ММ` for a stamp
 * (`formatInstant`), `ЧЧ:ММ:СС` for a line of a log (`formatClock`), `ЧЧ:ММ` (`formatTime`) and `ДД.ММ`
 * (`formatDayMonth`) for the short forms of a row. The exact, zone-independent stamp -- `ГГГГ-ММ-ДД ЧЧ:ММ:СС UTC`
 * (`formatInstantUtc`) -- is for the two places that need one string for everybody: a tooltip (`title`), and a text
 * that is copied off the screen, where an operator checks the screen against a log and wants the same line on both.
 * «UTC» is written there and nowhere else.
 *
 * Local time is computed in the browser, after the data has been read: a server render knows the server's zone, not
 * the reader's, and would print a time the browser then contradicts. A place that could draw an instant before the
 * first read draws a dash (or nothing) until the data is in.
 *
 * The parts come from `Intl.DateTimeFormat#formatToParts`, never from `format()`: the `ru-RU` locale prints
 * «14.11.2026, 09:12» with a comma, and that string is the locale data's to change. Only the numbers are taken from
 * it; the separators are ours. `timeZone` exists for tests: the application never passes it, so the zone is the
 * browser's own.
 */

/** What a time function accepts: the contract's `date-time` text, epoch milliseconds, or a `Date`. */
export type InstantInput = string | number | Date | null | undefined;

type PartName = 'year' | 'month' | 'day' | 'hour' | 'minute' | 'second';

const DASH = '—';

/** One formatter per zone: building a `DateTimeFormat` costs more than using it, and a table prints hundreds. */
const formatters = new Map<string, Intl.DateTimeFormat>();

function formatterFor(timeZone: string | undefined): Intl.DateTimeFormat {
  const key = timeZone ?? '';
  const known = formatters.get(key);
  if (known !== undefined) return known;
  const made = new Intl.DateTimeFormat('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    // `h23`, not `hour12: false`: the latter prints midnight as «24» in some engines.
    hourCycle: 'h23',
    ...(timeZone === undefined ? {} : { timeZone }),
  });
  formatters.set(key, made);
  return made;
}

function partsOf(moment: Date, timeZone: string | undefined): Record<PartName, string> {
  const found: Record<PartName, string> = { year: '', month: '', day: '', hour: '', minute: '', second: '' };
  for (const part of formatterFor(timeZone).formatToParts(moment)) {
    if (part.type in found) found[part.type as PartName] = part.value;
  }
  return found;
}

/**
 * The shared envelope of the five functions. An absent value is a dash; a text that is not a moment is returned as it
 * came (a screen that cannot read an instant shows what the server sent rather than invent one).
 */
function render(value: InstantInput, build: (moment: Date) => string): string {
  if (value === null || value === undefined || value === '') return DASH;
  const moment = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(moment.getTime())) return String(value);
  return build(moment);
}

/** `ДД.ММ.ГГГГ ЧЧ:ММ` in the reader's local time (the stamp of a row, a card, a sentence). */
export function formatInstant(value: InstantInput, timeZone?: string): string {
  return render(value, (moment) => {
    const p = partsOf(moment, timeZone);
    return `${p.day}.${p.month}.${p.year} ${p.hour}:${p.minute}`;
  });
}

/** `ЧЧ:ММ:СС` in local time: the time of a line of a log, where the day is said elsewhere. */
export function formatClock(value: InstantInput, timeZone?: string): string {
  return render(value, (moment) => {
    const p = partsOf(moment, timeZone);
    return `${p.hour}:${p.minute}:${p.second}`;
  });
}

/** `ЧЧ:ММ` in local time: «≈ до 14:05», «нет связи с 14:02». */
export function formatTime(value: InstantInput, timeZone?: string): string {
  return render(value, (moment) => {
    const p = partsOf(moment, timeZone);
    return `${p.hour}:${p.minute}`;
  });
}

/** `ДД.ММ` in local time: the day of a row that is not today's. */
export function formatDayMonth(value: InstantInput, timeZone?: string): string {
  return render(value, (moment) => {
    const p = partsOf(moment, timeZone);
    return `${p.day}.${p.month}`;
  });
}

/**
 * `ГГГГ-ММ-ДД ЧЧ:ММ:СС UTC`: the one stamp that reads the same on every machine. For a tooltip and for a text that is
 * copied from the screen. It is what `formatInstant` printed before the local reading was adopted, byte for byte, and
 * the language guard recognises its «UTC» only after a stamp of this shape, so its form is not to be changed.
 */
export function formatInstantUtc(value: InstantInput): string {
  return render(value, (moment) => `${moment.toISOString().replace('T', ' ').slice(0, 19)} UTC`);
}
