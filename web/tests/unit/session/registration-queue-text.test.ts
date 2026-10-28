/**
 * What the applicant reads when the registration door answers `queue_full`.
 *
 * `queue_full` is one closed value of the API's `conflict_reason` for two different causes: 100
 * requests are waiting, or 40 were pending or approved in the last 24 hours (`R-146ay`, no new
 * error code). The screen text must be true of both, so it names both and gives no number, no
 * identifier and no English.
 */

import { describe, expect, it } from 'vitest';

import { REGISTRATION_REFUSALS, registrationRefusalMessage } from '@/features/register/model/exchange';

describe('the queue_full text is true for a full queue and for a spent day', () => {
  it('names both causes in plain Russian and asks to try later', () => {
    expect(registrationRefusalMessage('queue_full')).toBe(
      'Очередь заявок заполнена или исчерпан лимит заявок на сутки. Попробуйте позже.',
    );
  });

  it('does not show the code, a number or Latin letters', () => {
    const text = registrationRefusalMessage('queue_full');
    expect(text).not.toMatch(/queue_full|[0-9]|[A-Za-z]/);
  });

  it('is still told apart from every other refusal', () => {
    const texts = REGISTRATION_REFUSALS.map((refusal) => registrationRefusalMessage(refusal));
    expect(new Set(texts).size).toBe(REGISTRATION_REFUSALS.length);
  });
});
