/**
 * The admission gate refuses a grounding diagnostic on the presence of the key, not on its
 * value, and it looks for both keys.
 *
 * `P02_SEAMS.md` §5.1 retains a rejected observation as a diagnostic row carrying
 * `grounded = false`, a non-null `ungrounded_reason` and no `finding_uid`. The existing
 * suite builds its diagnostic fixture with **all three** of those at once, so it cannot
 * distinguish which of the three refusals fired — and the `W12-WEB` sweep confirmed it:
 * removing either name from `DIAGNOSTIC_FIELDS`, and ignoring `grounded: true`, all three
 * left the suite green, because the fixture still had no `finding_uid` and was refused as
 * `not_a_finding` instead.
 *
 * So every payload below carries a **valid** `finding_uid` and a non-empty evidence array.
 * The only thing wrong with it is the diagnostic field, which makes the assertion on
 * `refusal` an assertion about which rule refused rather than that something did.
 */

import { describe, expect, it } from 'vitest';

import type { Finding } from '@/shared/api';
import { admitFinding, admitFindings } from '@/entities/finding';

import { finding } from './fixtures';

/** A well-formed finding with one extra key that only a diagnostic row ever carries. */
function withExtraKey(extra: Record<string, unknown>): Finding {
  return { ...finding(), ...extra } as unknown as Finding;
}

describe('a payload that is otherwise a perfectly good finding', () => {
  it('is admitted when it carries no diagnostic field at all', () => {
    // The control. Without it every assertion below could be passing for the wrong reason.
    expect(admitFinding(finding())).toEqual({ kind: 'admitted', finding: finding() });
  });
});

describe('the diagnostic refusal fires on the key, whichever key it is', () => {
  it('refuses a payload carrying `ungrounded_reason` and nothing else wrong', () => {
    expect(admitFinding(withExtraKey({ ungrounded_reason: 'quotation_absent' }))).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('refuses a payload carrying `grounded: false` and nothing else wrong', () => {
    expect(admitFinding(withExtraKey({ grounded: false }))).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('refuses a payload carrying `grounded: true`, because the key is the signal', () => {
    // `grounded: true` looks reassuring and is not. `Finding` is a closed schema declaring
    // no such property, so its presence means something handed this UI a row from the
    // diagnostic side of the grounding gate, whatever that row then claims about itself.
    expect(admitFinding(withExtraKey({ grounded: true }))).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('refuses a payload carrying `ungrounded_reason: null`, for the same reason', () => {
    expect(admitFinding(withExtraKey({ ungrounded_reason: null }))).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('refuses the diagnostic before it complains about anything else', () => {
    // A row that is both a diagnostic and has no `finding_uid` is refused as a diagnostic.
    // Stated so that the order of the three checks is a fact rather than an accident.
    expect(admitFinding(withExtraKey({ grounded: false, finding_uid: '' }))).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });
});

describe('a diagnostic row never reaches the list, and is not reported as a fault', () => {
  it('is counted as refused and produces no integrity fault', () => {
    const admitted = admitFindings([
      finding(),
      withExtraKey({ ungrounded_reason: 'span_length_mismatch' }),
      withExtraKey({ grounded: true }),
    ]);

    expect(admitted.findings).toHaveLength(1);
    expect(admitted.refusedCount).toBe(2);
    // An ungrounded item is a run diagnostic, not something to put in front of a reviewer.
    expect(admitted.integrityFaults).toEqual([]);
  });
});
