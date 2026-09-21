/**
 * `terminalReasonNote` — the three arms, and the two that exist for reasons nobody
 * anticipated.
 *
 * The contract-derived completeness check lives in
 * `tests/contract/terminal-reason-sentences.contract.test.ts`. This file holds the
 * behaviour a completeness check cannot state: what happens to a reason that is **not**
 * in the catalog, and what happens to a `failed` reading that carries none at all.
 *
 * `W15-AUTH` found five classifiers collapsing into `server_error` for want of a branch,
 * and `W27-WEB` found a render list narrower than its surface twice. The failure mode
 * both share is a default that says nothing new. These tests assert the default says
 * something a reader can act on, and that it says it about the code that was actually
 * received.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorCode } from '@/shared/api';
import { ABSENT_SENTENCE, UNDESCRIBED_PREFIX, terminalReasonNote } from '@/entities/audit-run';

describe('a catalog reason is described', () => {
  it('carries the code alongside the sentence, never instead of it', () => {
    const note = terminalReasonNote('analysis_failed');
    expect(note.kind).toBe('described');
    if (note.kind === 'absent') throw new Error('unreachable');
    expect(note.code).toBe('analysis_failed');
    expect(note.sentence.length).toBeGreaterThan(40);
  });

  it('gives two different codes two different sentences', () => {
    const a = terminalReasonNote('analysis_failed');
    const b = terminalReasonNote('cost_budget_exceeded');
    expect(a.sentence).not.toBe(b.sentence);
  });
});

describe('a reason this client does not know still says something true', () => {
  /**
   * Reachable, not hypothetical. The generated client casts the response body and never
   * validates it, so a deployment one reseal ahead of this client puts a string here that
   * `ErrorCode` says cannot exist. The cast below is that case, written down.
   */
  const ROGUE = 'recording_not_found_for_this_document' as ErrorCode;

  it('classifies it as undescribed rather than describing it wrongly', () => {
    const note = terminalReasonNote(ROGUE);
    expect(note.kind).toBe('undescribed');
  });

  it('says it has no description instead of printing nothing', () => {
    const note = terminalReasonNote(ROGUE);
    expect(note.sentence).toContain(UNDESCRIBED_PREFIX);
    expect(note.sentence.trim().length).toBeGreaterThan(UNDESCRIBED_PREFIX.length);
  });

  it('says the checkable fact about it, and does not guess a cause', () => {
    const note = terminalReasonNote(ROGUE);
    expect(note.sentence).toContain('описания для него у этого клиента нет');
    expect(note.sentence).toContain('Ничего не опубликовано');
    // It must not borrow a neighbouring sentence: no catalog wording leaks in.
    expect(note.sentence).not.toContain('хранилище метаданных');
    expect(note.sentence).not.toContain('correlation id');
  });

  it('keeps the code the run recorded, so it can be quoted', () => {
    const note = terminalReasonNote(ROGUE);
    if (note.kind === 'absent') throw new Error('unreachable');
    expect(note.code).toBe(ROGUE);
  });
});

describe('a failed reading with no reason at all', () => {
  it('states that the contract obliges one, rather than inventing one', () => {
    for (const empty of [null, undefined, '']) {
      const note = terminalReasonNote(empty);
      expect(note.kind).toBe('absent');
      expect(note.sentence).toBe(ABSENT_SENTENCE);
    }
    expect(ABSENT_SENTENCE).toContain('обязан её записать');
  });
});
