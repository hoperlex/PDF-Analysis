/**
 * The ledger is append-only, and appending a comment does not overwrite a verdict.
 *
 * This is the gate condition for this session and the third clause of `PROTOTYPE_PROFILE.md`
 * §8: a reviewer must be able to accept one finding, reject another, and append a later
 * comment **without overwriting history**.
 *
 * The property has two halves and both are tested here:
 *
 *   - the *verdict* survives — a comment carries `verdict: null`, so the most recent
 *     verdict-bearing event is still the accept that came before it (`P02_SEAMS.md` §5.4);
 *   - the *events* survive — the earlier accept is still in the list, unmodified, and the
 *     list only grew.
 *
 * `PD-01` is the same rule seen from the other side: a revocation moves the projection to
 * `pending` and restores no earlier verdict. There is no stack to pop, because nothing was
 * ever replaced.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  appendEvent,
  isVerdictBearing,
  orderEvents,
  projectVerdict,
  reconcile,
} from '@/entities/expert-decision';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';

import { OBSERVATION_ID, decisionEvent, decisionId, render } from '../review/fixtures';

const ACCEPT = decisionEvent({
  decision_id: decisionId('A'),
  event_type: 'accept',
  verdict: 'accepted',
  recorded_at: '2026-09-10T09:00:00.000Z',
});

const COMMENT = decisionEvent({
  decision_id: decisionId('B'),
  event_type: 'comment',
  verdict: null,
  comment: 'Checked against the signed annex; the 45-day term is the operative one.',
  recorded_at: '2026-09-10T10:00:00.000Z',
});

describe('appending a comment after a verdict', () => {
  it('leaves the verdict standing', () => {
    const after = appendEvent([ACCEPT], COMMENT);
    expect(projectVerdict(after).current_verdict).toBe('accepted');
    expect(projectVerdict(after).latest_verdict_decision_id).toBe(ACCEPT.decision_id);
  });

  it('leaves the earlier event intact and byte-identical', () => {
    const before = [ACCEPT];
    const after = appendEvent(before, COMMENT);

    // The original list is untouched: `appendEvent` returns a new array.
    expect(before).toEqual([ACCEPT]);
    expect(before).toHaveLength(1);

    // The accept is still there, and is the same object content it was.
    const retained = after.find((event) => event.decision_id === ACCEPT.decision_id);
    expect(retained).toEqual(ACCEPT);

    // The list only grew.
    expect(after).toHaveLength(2);
    expect(after.map((event) => event.decision_id)).toEqual([
      ACCEPT.decision_id,
      COMMENT.decision_id,
    ]);
  });

  it('moves latest_comment and decision_recorded_at, and only those', () => {
    const before = projectVerdict([ACCEPT]);
    const after = projectVerdict(appendEvent([ACCEPT], COMMENT));

    expect(before.current_verdict).toBe('accepted');
    expect(after.current_verdict).toBe('accepted');
    expect(after.latest_verdict_decision_id).toBe(before.latest_verdict_decision_id);

    // §5.4: `decision_recorded_at` is the newest event of *any* type, "so appending a
    // comment moves it".
    expect(before.decision_recorded_at).toBe(ACCEPT.recorded_at);
    expect(after.decision_recorded_at).toBe(COMMENT.recorded_at);
    expect(after.latest_decision_id).toBe(COMMENT.decision_id);
    expect(after.latest_comment).toBe(COMMENT.comment);
    expect(after.decision_event_count).toBe(2);
  });

  it('still shows the verdict in the panel and both events in the history', () => {
    const after = appendEvent([ACCEPT], COMMENT);
    const projection = projectVerdict(after);

    const panel = render(
      createElement(DecisionPanel, {
        currentVerdict: projection.current_verdict,
        observationId: OBSERVATION_ID,
        onAccept: () => {},
        onReject: () => {},
        onComment: () => {},
      }),
    );
    expect(panel).toContain('data-verdict="accepted"');

    const history = render(createElement(DecisionHistory, { events: after }));
    expect(history).toContain('data-event-count="2"');
    expect(history).toContain(`data-decision-id="${ACCEPT.decision_id}"`);
    expect(history).toContain(`data-decision-id="${COMMENT.decision_id}"`);
    // Nothing is collapsed behind "show older": seeing the accept still sitting under the
    // newer comment is the entire point of an append-only ledger.
    expect(history.indexOf(ACCEPT.decision_id)).toBeLessThan(history.indexOf(COMMENT.decision_id));
  });

  it('survives several comments after the verdict', () => {
    const second = decisionEvent({
      decision_id: decisionId('C'),
      event_type: 'comment',
      verdict: null,
      comment: 'Second thought, recorded later.',
      recorded_at: '2026-09-10T11:00:00.000Z',
    });

    const after = appendEvent(appendEvent([ACCEPT], COMMENT), second);
    const projection = projectVerdict(after);

    expect(projection.current_verdict).toBe('accepted');
    expect(projection.latest_comment).toBe(second.comment);
    expect(projection.decision_event_count).toBe(3);
    expect(after.map((event) => event.decision_id)).toEqual([
      ACCEPT.decision_id,
      COMMENT.decision_id,
      second.decision_id,
    ]);
  });
});

describe('the projection', () => {
  it('is pending when nothing has judged the finding', () => {
    expect(projectVerdict([])).toEqual({
      current_verdict: 'pending',
      latest_verdict_decision_id: null,
      latest_comment: null,
      latest_decision_id: null,
      decision_recorded_at: null,
      decision_event_count: 0,
    });
  });

  it('takes the most recent verdict-bearing event', () => {
    const reject = decisionEvent({
      decision_id: decisionId('D'),
      event_type: 'reject',
      verdict: 'rejected',
      recorded_at: '2026-09-10T12:00:00.000Z',
    });
    expect(projectVerdict([ACCEPT, reject]).current_verdict).toBe('rejected');
  });

  it('takes latest_comment from the most recent event carrying one, whatever its type', () => {
    // §5.4 says "whatever its `event_type`" — an accept carrying a comment counts.
    const acceptWithComment = decisionEvent({
      decision_id: decisionId('E'),
      event_type: 'accept',
      verdict: 'accepted',
      comment: 'Accepted with a note.',
      recorded_at: '2026-09-10T13:00:00.000Z',
    });
    const projection = projectVerdict([COMMENT, acceptWithComment]);
    expect(projection.latest_comment).toBe('Accepted with a note.');
    expect(projection.current_verdict).toBe('accepted');
  });

  it('classifies verdict-bearing events by the verdict field, not the event type', () => {
    expect(isVerdictBearing(ACCEPT)).toBe(true);
    expect(isVerdictBearing(COMMENT)).toBe(false);
  });

  it('prefers the server projection when one is supplied', () => {
    // The server holds the single definition (`finding_current_verdict`). A client that
    // preferred its own recomputation would be a second source of truth.
    const after = appendEvent([ACCEPT], COMMENT);
    expect(reconcile(after, 'needs_manual_review').current_verdict).toBe('needs_manual_review');
    expect(reconcile(after, undefined).current_verdict).toBe('accepted');
  });
});

describe('PD-01 revocation', () => {
  const REVOKE = decisionEvent({
    decision_id: decisionId('F'),
    event_type: 'revoke',
    verdict: 'pending',
    recorded_at: '2026-09-10T14:00:00.000Z',
  });

  it('moves the projection to pending', () => {
    expect(projectVerdict([ACCEPT, REVOKE]).current_verdict).toBe('pending');
  });

  it('restores no earlier verdict', () => {
    // An accept, a reject, then a revoke. A "pop the stack" implementation would show
    // `accepted` here. The projection shows `pending`, and the earlier verdicts remain in
    // the history as the events they were.
    const reject = decisionEvent({
      decision_id: decisionId('G'),
      event_type: 'reject',
      verdict: 'rejected',
      recorded_at: '2026-09-10T13:30:00.000Z',
    });

    const events = [ACCEPT, reject, REVOKE];
    const projection = projectVerdict(events);

    expect(projection.current_verdict).toBe('pending');
    expect(projection.latest_verdict_decision_id).toBe(REVOKE.decision_id);
    expect(projection.decision_event_count).toBe(3);
    expect(events).toHaveLength(3);
  });
});

describe('ordering and idempotent replay', () => {
  it('orders by (recorded_at, decision_id)', () => {
    const sameInstantB = decisionEvent({
      decision_id: decisionId('Z'),
      recorded_at: '2026-09-10T09:00:00.000Z',
    });
    const sameInstantA = decisionEvent({
      decision_id: decisionId('A'),
      recorded_at: '2026-09-10T09:00:00.000Z',
    });

    // Same instant: `decision_id` is the tiebreaker, because the server's `sequence_no` is
    // never returned and never embedded in a cursor.
    expect(orderEvents([sameInstantB, sameInstantA]).map((e) => e.decision_id)).toEqual([
      sameInstantA.decision_id,
      sameInstantB.decision_id,
    ]);
  });

  it('never mutates the array it is given', () => {
    const events = [COMMENT, ACCEPT];
    const snapshot = [...events];
    orderEvents(events);
    projectVerdict(events);
    appendEvent(events, decisionEvent({ decision_id: decisionId('H') }));
    expect(events).toEqual(snapshot);
  });

  it('treats re-appending the same decision_id as a no-op, not a duplicate row', () => {
    // Replaying an idempotent write's response must not double the ledger.
    const after = appendEvent(appendEvent([ACCEPT], COMMENT), COMMENT);
    expect(after).toHaveLength(2);
    expect(projectVerdict(after).decision_event_count).toBe(2);
  });
});

describe('the decision panel offers no way to overwrite', () => {
  it('has exactly three controls and no revoke, undo or clear', () => {
    const markup = render(
      createElement(DecisionPanel, {
        currentVerdict: 'accepted',
        observationId: OBSERVATION_ID,
        onAccept: () => {},
        onReject: () => {},
        onComment: () => {},
      }),
    );

    expect(markup.match(/data-intent="[a-z]+"/g)).toEqual([
      'data-intent="accept"',
      'data-intent="reject"',
      'data-intent="comment"',
    ]);
    // `revoke` is in the contract's event union and has no PC-01 client (seam §10).
    expect(markup).not.toContain('revoke');
    expect(markup).not.toContain('Undo');
    expect(markup).not.toContain('Change verdict');
  });

  it('renders the not-applicable state for a finding nobody has judged', () => {
    const markup = render(createElement(DecisionHistory, { events: [] }));
    // shared/ui names this exact case as the not-applicable one: the question has not been
    // asked yet, which is different from the answer being none.
    expect(markup).toContain('Решений пока нет');
  });
});
