/**
 * The reviewed AR v3 beta pack status as the server answers it, in the two shapes it has.
 *
 * One fixture, three readers: the pack panel's own test, the rendered-language guard and the
 * contrast census (`tests/unit/styles/screens.ts`), which must render the panel's installed
 * state to measure the rules that state alone carries (`.facts`, `.attestation`).
 *
 * The digest is digits only, like every digest the other fixtures seed: it is server data and
 * Latin by nature, and a hex letter in it would be read by the language guard as a word. A test
 * that cares about the leading characters passes its own.
 */

import type { ArV3BetaPackStatus } from '@/shared/api';

export const PACK_SHA256_DIGITS = `${'0123456789'.repeat(6)}0123`;

export const NOT_INSTALLED_PACK: ArV3BetaPackStatus = { state: 'not_installed' };

export function installedPackFixture(over: Partial<ArV3BetaPackStatus> = {}): ArV3BetaPackStatus {
  return {
    state: 'installed',
    analysis_profile_id: 'ap_01M5AXG1K22R027A33VTKZ468P',
    prompt_bundle_id: 'pb_01M5AXG1K2JQQH7R4ACTBW8974',
    pack_sha256: PACK_SHA256_DIGITS,
    scope_ids: ['F1', 'F2', 'A1', 'A2', 'S1', 'S2'],
    review: {
      reviewer: 'Иванова Мария Петровна',
      capacity: 'главный эксперт по разделу АР',
      reviewed_at: '2026-10-20',
      decision_ref: 'решение владельца № 146',
      scope_statement: 'шесть карт норм и шесть наборов источников для жилых домов Ф1.3',
    },
    ...over,
  };
}

/** The answer with one member REMOVED (not set to `undefined`): what an omitting server sends. */
export function withoutMember(body: ArV3BetaPackStatus, member: keyof ArV3BetaPackStatus): Record<string, unknown> {
  const copy: Record<string, unknown> = { ...body };
  delete copy[member];
  return copy;
}
