/**
 * The refusal labels by section, as the administrator sees them (`PREC-WEB`, plan-v5 sections 2.6 and 3.6): the setting `section_labels` is ONE object,
 * `{"<section>": {"enabled": bool, "report_sha256": hex64, "analogous": 0..1}}`, and every write replaces the whole of it. These are the pure
 * functions that read it and build the next one, with the server's own rules for an entry, so a write is never refused for a shape this code made.
 *
 * Switching a section ON needs the digest of the replay report it was made from; the report is a product tool with no endpoint in this contract
 * (`CRIT-REPLAY-01`), so the screen offers only the way back (OFF), which needs no report. A section nobody journalled is off.
 */

import type { PrecedentSettingList } from '@/shared/api';

const SECTION_CODE = /^[A-Z][A-Z0-9_]{0,15}$/;
const SHA256 = /^[0-9a-f]{64}$/;

export interface SectionLabelState {
  readonly section: string;
  readonly enabled: boolean;
  /** The digest of the replay report the switch was made from; absent for a section that was only ever off. */
  readonly reportSha256: string | null;
  /** The cosine threshold the report chose for this section; absent: the installation's own. */
  readonly analogous: number | null;
}

type Entry = { enabled: boolean; report_sha256?: string; analogous?: number };

function entryOf(section: string, raw: unknown): Entry | null {
  if (!SECTION_CODE.test(section) || typeof raw !== 'object' || raw === null) return null;
  const entry = raw as Record<string, unknown>;
  if (typeof entry.enabled !== 'boolean') return null;
  const digest = entry.report_sha256;
  const analogous = entry.analogous;
  if (digest !== undefined && !(typeof digest === 'string' && SHA256.test(digest))) return null;
  if (analogous !== undefined && !(typeof analogous === 'number' && analogous >= 0 && analogous <= 1)) return null;
  // The server refuses a switch ON with no report; an entry like that was never in force, so it is not read as on.
  if (entry.enabled && digest === undefined) return null;
  return { enabled: entry.enabled, ...(digest === undefined ? {} : { report_sha256: digest }), ...(analogous === undefined ? {} : { analogous }) };
}

/** The revision of `section_labels` in force, as an object of entries the server would accept. An entry it would not accept is left out (it was read as off). */
export function currentSectionEntries(list: PrecedentSettingList | undefined): Readonly<Record<string, Entry>> {
  const current = list?.current.find((setting) => setting.setting_name === 'section_labels');
  const value = (current?.value ?? {}) as Record<string, unknown>;
  const entries: Record<string, Entry> = {};
  for (const [section, raw] of Object.entries(value)) {
    const entry = entryOf(section, raw);
    if (entry !== null) entries[section] = entry;
  }
  return entries;
}

export function sectionLabelStates(list: PrecedentSettingList | undefined): readonly SectionLabelState[] {
  return Object.entries(currentSectionEntries(list))
    .map(([section, entry]) => ({ section, enabled: entry.enabled, reportSha256: entry.report_sha256 ?? null, analogous: entry.analogous ?? null }))
    .sort((a, b) => Number(b.enabled) - Number(a.enabled) || a.section.localeCompare(b.section));
}

/** The value to write to switch one section OFF: the whole state again, that section `enabled: false` with its report kept as the record of what it was. */
export function valueWithSectionOff(list: PrecedentSettingList | undefined, section: string): Record<string, Entry> {
  const entries = { ...currentSectionEntries(list) };
  const was = entries[section];
  entries[section] = { ...(was ?? {}), enabled: false };
  return entries;
}

/** The first and last characters of a digest, enough to tell two reports apart on one line. */
export function shortDigest(digest: string): string {
  return `${digest.slice(0, 8)}…${digest.slice(-6)}`;
}
