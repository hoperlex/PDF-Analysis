/**
 * Every catalog code has a Russian sentence, derived from the frozen catalog.
 *
 * `R-18` requires the alpha in Russian. `W31-UI` translated what `web/src` owns and
 * reported the wall: a failure `detail` is often `error.envelope.message`, which the
 * backend renders from `contracts/domain/v1/error-codes.json`'s `summary` fields — and
 * measured on `ae2adf5` **not one of the 22 carries a Cyrillic character**.
 * `catalog-message.ts` is the repair. This guard is what keeps it from rotting the way
 * `PC01_ERROR_CODES` did twice: `W15-AUTH` found that list missing both authorization
 * codes and `W25-SEAL` found it missing `staged_upload_lost`, each time because a
 * hand-kept subset of a resealable surface had nothing reading it. `W30-LISTS` §4 is the
 * census of that class, and this map is a new member of it.
 *
 * **What licenses the set: the whole catalog, not `PC01_ERROR_CODES`.** `transport.ts`'s
 * `decodeFailure` builds an `ApiError` exactly when `isErrorCode()` passes, and that tests
 * `ERROR_CODE_VALUES` — all 22. Every classifier consuming this map has a `default:` arm
 * that fires for any code it has no branch for, and six catalog codes sit outside
 * `PC01_ERROR_CODES`. The field is constrained by the catalog, so this guard reads the
 * catalog document rather than the narrower list, and rather than the generated enum the
 * module imports.
 *
 * It deliberately does **not** check the set against today's producers in `src/`. A guard
 * keyed on what the API happens to emit today would be narrower than the surface, which is
 * the exact defect `D-40` records.
 */

import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  ERROR_CODE_VALUES,
  UNDESCRIBED_MESSAGE_PREFIX,
  catalogMessage,
} from '@/shared/api';
import { terminalReasonNote } from '@/entities/audit-run';
import { REPO_ROOT, readJson } from '../guards/lib/repo';

const ERROR_CATALOG_PATH = join(REPO_ROOT, 'contracts', 'domain', 'v1', 'error-codes.json');

interface Catalog {
  readonly codes: Record<string, { readonly summary: string }>;
}

const catalog = readJson<Catalog>(ERROR_CATALOG_PATH);
const catalogCodes = Object.keys(catalog.codes).sort();

describe('the sentence set is the frozen catalog, read from the contract', () => {
  it('describes every code the catalog declares', () => {
    const undescribed = catalogCodes.filter((code) =>
      catalogMessage(code).includes(UNDESCRIBED_MESSAGE_PREFIX),
    );
    expect(
      undescribed,
      'contracts/domain/v1/error-codes.json declares these and catalog-message.ts has no ' +
        'sentence for them. A failure carrying one would render the undescribed default ' +
        'where the screen used to render the API English.',
    ).toEqual([]);
  });

  it('agrees with the generated enum the module is typed against', () => {
    // Two independent readings of one frozen set: the catalog document, and the enum the
    // client was generated from. A reseal that moved one and not the other reddens here.
    expect([...ERROR_CODE_VALUES].sort()).toEqual(catalogCodes);
  });

  it('is keyed on the whole catalog and not on the PC-01 render subset', () => {
    // The six that are in the catalog and outside `PC01_ERROR_CODES`. If this map were
    // keyed on that list — which is what `W29-SAY` was told to do for `terminal-reason.ts`
    // and refused — these six would render the undescribed default.
    const outsidePc01 = [
      'cost_budget_exceeded',
      'execution_token_invalid',
      'partial_result_not_publishable',
      'required_norm_unavailable',
      'stale_attempt',
      'unsupported_contract_version',
    ];
    for (const code of outsidePc01) {
      expect(catalogCodes, `${code} is not in the catalog any more`).toContain(code);
      expect(catalogMessage(code), `${code} renders the undescribed default`).not.toContain(
        UNDESCRIBED_MESSAGE_PREFIX,
      );
    }
  });
});

describe('every sentence is Russian, and a sentence', () => {
  it('carries Cyrillic and no English prose', () => {
    for (const code of catalogCodes) {
      const sentence = catalogMessage(code);
      expect(/[а-яА-ЯёЁ]/u.test(sentence), `${code} carries no Cyrillic at all`).toBe(true);
      // The catalog's own summary must not have been pasted through.
      expect(sentence, `${code} carries its English summary verbatim`).not.toContain(
        catalog.codes[code]?.summary ?? '\u0000',
      );
    }
  });

  it('writes a sentence, not an identifier repeated', () => {
    for (const code of catalogCodes) {
      const sentence = catalogMessage(code);
      expect(sentence.trim().endsWith('.'), `${code} does not end in a full stop`).toBe(true);
      expect(
        sentence.split(/\s+/).length,
        `${code} is too short to be a sentence`,
      ).toBeGreaterThan(10);
      if (code.includes('_')) {
        expect(sentence, `${code} echoes its own identifier`).not.toContain(code);
      }
    }
  });

  it('gives each code a sentence of its own', () => {
    const seen = new Map<string, string>();
    for (const code of catalogCodes) {
      const sentence = catalogMessage(code);
      const first = seen.get(sentence);
      expect(first, `${code} renders the same sentence as ${first}`).toBeUndefined();
      seen.set(sentence, code);
    }
    expect(seen.size).toBe(catalogCodes.length);
  });
});

describe('it is not a second copy of terminal-reason.ts', () => {
  /**
   * The two tables restate the same 22 summaries and are read in different places:
   * `terminal_reason` is a field on a **200** and is phrased for a run that has stopped;
   * this one stands where an **error envelope's** message was and is read by four
   * classifiers, only one of which is about a run. If a later editor collapses them, the
   * run register leaks onto the upload and project screens. That is what this asserts.
   */
  it('shares no sentence with the terminal-reason table', () => {
    for (const code of catalogCodes) {
      const note = terminalReasonNote(code);
      if (note.kind !== 'described') throw new Error(`${code} is not described`);
      expect(
        catalogMessage(code),
        `${code}: catalog-message.ts and terminal-reason.ts render the same sentence`,
      ).not.toBe(note.sentence);
    }
  });
});

describe('a code outside the catalog says so instead of guessing', () => {
  /**
   * Reachable in principle rather than today: `transport.ts` narrows with `isErrorCode`
   * before constructing an `ApiError`, but the generated client casts response bodies
   * rather than validating them, and this function takes a `string`.
   */
  const ROGUE = 'recording_not_found_for_this_document';

  it('names itself undescribed rather than borrowing a neighbour', () => {
    const sentence = catalogMessage(ROGUE);
    expect(sentence).toContain(UNDESCRIBED_MESSAGE_PREFIX);
    expect(sentence.trim().length).toBeGreaterThan(UNDESCRIBED_MESSAGE_PREFIX.length);
    expect(sentence).not.toContain('хранилище метаданных');
  });

  it('is not what any catalog code renders', () => {
    for (const code of catalogCodes) {
      expect(catalogMessage(code)).not.toBe(catalogMessage(ROGUE));
    }
  });
});
