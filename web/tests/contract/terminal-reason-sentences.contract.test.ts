/**
 * Every reason a `failed` run can record has a sentence, derived from the frozen catalog.
 *
 * `W28-LIVE` measured the run screen printing `Terminal reason: dependency_unavailable`
 * and nothing else. `terminal-reason.ts` is the repair. This guard is what keeps the
 * repair from rotting the way `PC01_ERROR_CODES` did twice — `W15-AUTH` found that list
 * missing both authorization codes and `W25-SEAL` found it missing `staged_upload_lost`,
 * each time because a hand-kept subset of a resealable surface had nothing reading it.
 *
 * **What licenses the set.** The API contract types `RunStatus.terminal_reason` as
 * `ErrorCode | null` — the whole catalog, not a subset — and migration
 * `20260910_0002_pc01_schema.py` CHECK-constrains `audit_run.terminal_reason` to the same
 * catalog with `ck_audit_run_terminal_reason`. So the reachable set is the catalog, and
 * this guard reads the catalog itself, `contracts/domain/v1/error-codes.json`, rather than
 * the generated enum the module imports. A code added to the catalog by a reseal reddens
 * this file before it can reach a screen with no sentence.
 *
 * It deliberately does **not** check the set against today's producers in `src/`.
 * `W29-RETRY` is live in `src/auditmanager/runs/` and may change which reason this screen
 * receives; a guard keyed on what the executor happens to emit today would have to be
 * re-measured every time that changes, and would be narrower than the surface — which is
 * the exact defect `D-40` records.
 */

import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { ERROR_CODE_VALUES } from '@/shared/api';
import { UNDESCRIBED_PREFIX, terminalReasonNote } from '@/entities/audit-run';
import { REPO_ROOT, readJson } from '../guards/lib/repo';

const ERROR_CATALOG_PATH = join(REPO_ROOT, 'contracts', 'domain', 'v1', 'error-codes.json');

interface Catalog {
  readonly codes: Record<string, { readonly summary: string }>;
}

const catalog = readJson<Catalog>(ERROR_CATALOG_PATH);
const catalogCodes = Object.keys(catalog.codes).sort();

describe('the sentence set is the frozen catalog, read from the contract', () => {
  it('describes every code the catalog declares', () => {
    const undescribed = catalogCodes.filter(
      (code) => terminalReasonNote(code).kind !== 'described',
    );
    expect(
      undescribed,
      'contracts/domain/v1/error-codes.json declares these and terminal-reason.ts has no ' +
        'sentence for them. A failed run carrying one would render the undescribed default.',
    ).toEqual([]);
  });

  it('agrees with the generated enum the module narrows against', () => {
    // Two independent readings of one frozen set: the catalog document, and the enum the
    // client was generated from. A reseal that moved one and not the other reddens here.
    expect([...ERROR_CODE_VALUES].sort()).toEqual(catalogCodes);
  });

  it('gives no catalog code the undescribed default', () => {
    for (const code of catalogCodes) {
      const note = terminalReasonNote(code);
      expect(note.sentence, `${code} renders the undescribed default`).not.toContain(
        UNDESCRIBED_PREFIX,
      );
    }
  });
});

describe('no sentence is a constant, and none is another code sentence', () => {
  it('gives each code a sentence of its own', () => {
    const seen = new Map<string, string>();
    for (const code of catalogCodes) {
      const note = terminalReasonNote(code);
      if (note.kind !== 'described') throw new Error(`${code} is not described`);
      const first = seen.get(note.sentence);
      expect(first, `${code} renders the same sentence as ${first}`).toBeUndefined();
      seen.set(note.sentence, code);
    }
    expect(seen.size).toBe(catalogCodes.length);
  });

  it('writes a sentence, not an identifier repeated', () => {
    for (const code of catalogCodes) {
      const note = terminalReasonNote(code);
      // A sentence: more than a handful of words, ending in a full stop, and never just
      // the code with its underscores swapped for spaces.
      expect(note.sentence.trim().endsWith('.'), `${code} does not end in a full stop`).toBe(true);
      expect(note.sentence.split(/\s+/).length, `${code} is too short to be a sentence`).toBeGreaterThan(12);
      expect(note.sentence).not.toBe(code.replace(/_/g, ' '));
      // An identifier echoed into prose is the defect this task is about. A code that is
      // one ordinary English word — `conflict`, `not_found`'s second half — is not, and
      // asserting otherwise would force a sentence to avoid the word it is about.
      if (code.includes('_')) {
        expect(note.sentence, `${code} echoes its own identifier`).not.toContain(code);
      }
    }
  });
});

describe('the one sentence whose value is what it refuses to say', () => {
  /**
   * `W28-LIVE`: in `recorded` mode a document with no recording fails with
   * `dependency_unavailable` while the provider is healthy. `W27-REFUSE` found the
   * opposite failure — nginx `413` rendered as "The upload did not reach the API", true
   * of the transport and wrong about the cause. This sentence must name the class and
   * refuse the diagnosis.
   */
  const note = terminalReasonNote('dependency_unavailable');

  it('names the catalog class rather than one member of it', () => {
    expect(note.sentence).toContain('хранилище метаданных');
    expect(note.sentence).toContain('хранилище объектов');
    expect(note.sentence).toContain('провайдера модели');
    expect(note.sentence).toContain('транспорт исполнителя');
  });

  it('says out loud that the reading does not record which one', () => {
    expect(note.sentence).toContain('не фиксирует, о какой из них шла речь');
  });

  it('never asserts that the provider is the thing that failed', () => {
    const lower = note.sentence.toLowerCase();
    expect(lower).not.toContain('the provider is down.');
    expect(lower).not.toContain('the provider this run needs is unavailable');
    // The catalog's own retryable flag is a permission. `W28-LIVE` measured three of
    // three recorded-mode runs where no retry could ever succeed.
    expect(note.sentence).toContain('а не предсказание');
  });

  it('is not the startRun classifier sentence, which this path never reaches', () => {
    // run-failure.ts:76 says "Провайдер, нужный этому прогону, недоступен." It is real UI
    // text and it is reachable only when startRun itself answers an error envelope. Here
    // startRun answered 202 and the stage failed asynchronously.
    expect(note.sentence).not.toContain('Провайдер, нужный этому прогону, недоступен.');
  });
});
