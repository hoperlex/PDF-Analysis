/**
 * Render a contract `date-time` for display.
 *
 * Deliberately locale-independent and UTC. The alternative — `toLocaleString()` — renders
 * differently on the server and in the browser and makes React hydration mismatch, and
 * for a single-reviewer local tool a stable UTC stamp is more useful than a localized one
 * anyway. An operator correlating a screen with a log wants the same string in both.
 */
export function formatInstant(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${parsed.toISOString().replace('T', ' ').slice(0, 19)} UTC`;
}
