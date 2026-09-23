/**
 * Eight things the review screens render that nothing was reading.
 *
 * The `W12-WEB` sweep mutated every branch in the evidence viewer, the decision panel and
 * the decision history. These eight survived:
 *
 *   - the **anchor line** under each quotation can be emptied — criterion 6 asks for the
 *     finding to open at its exact quotation, and the anchor is how the reviewer knows
 *     which quotation this is;
 *   - the **span-mismatch alert** can be made unreachable, so an anchor that disagrees
 *     with the string beside it would be shown as if it agreed;
 *   - the `<object>` can drop the `#page=` fragment, so the PDF island opens on page 1
 *     whatever page the finding cited — the existing assertion looks for the fragment
 *     anywhere in the markup and `data-viewer-src` still carries it;
 *   - the **empty-comment refusal** can be made unreachable, so a refused comment would
 *     look like a comment that was sent;
 *   - the **current verdict** can be derived from the pending intent rather than from the
 *     server projection, which is the panel deciding a verdict from the button pressed;
 *   - an **empty history** can be rendered as an error rather than as not-applicable;
 *   - the history can stop rendering **comments** and stop rendering each event's
 *     **verdict**, which is most of what "a verdict recorded with visible history" means.
 *
 * Rendered to static markup with `renderToStaticMarkup`, as the rest of this suite does:
 * no DOM, no `jsdom`, no testing-library.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DecisionEvent, Evidence } from '@/shared/api';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { DecisionPanel } from '@/widgets/decision-panel';
import { COMMENT_REFUSALS, commentRefusalMessage } from '@/features/append-comment';
import { DecisionHistory } from '@/widgets/decision-history';

import { OBSERVATION_ID, decisionEvent, decisionId, observation, render } from './fixtures';

const OBJECT_URL = 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100';

/** An evidence item with an anchor stated independently of its quotation. */
function anchored(overrides: Partial<Evidence> & Pick<Evidence, 'quote'>): Evidence {
  const charStart = overrides.char_start ?? 1200;
  return {
    evidence_ordinal: 1,
    page_number: 7,
    ...overrides,
    char_start: charStart,
    // Derived last, so an override of `char_start` cannot leave the two disagreeing and
    // silently turn an agreeing-anchor case into a mismatch case.
    char_end: charStart + [...overrides.quote].length,
  };
}

function viewer(item: Evidence, activePage: number, documentUrl: string | null = OBJECT_URL) {
  return render(
    createElement(EvidenceViewer, {
      observation: observation({ evidence: [item] }),
      activePage,
      onPageChange: () => {},
      documentUrl,
    }),
  );
}

// ---------------------------------------------------------------------------------------
// The evidence viewer
// ---------------------------------------------------------------------------------------

describe('each quotation is shown with the anchor it was verified at', () => {
  it('states the page and the character range beside the quotation', () => {
    const markup = viewer(
      anchored({ quote: 'thirty days', page_number: 7, char_start: 1200 }),
      7,
    );
    expect(markup).toContain('am-quotation__anchor');
    expect(markup).toContain('стр. 7, символы 1200');
    expect(markup).toContain('1211');
  });

  it('states a different anchor for a different item', () => {
    const markup = viewer(
      anchored({ quote: 'forty-five days', page_number: 9, char_start: 40 }),
      9,
    );
    expect(markup).toContain('стр. 9, символы 40');
    expect(markup).toContain('55');
  });

  /**
   * `D-25`, asserted where the reviewer actually reads it.
   *
   * The unit test on `anchorLabel` constrains the helper; this constrains the *rendered
   * markup*, because the defect the row is about is what reaches the screen. A repair that
   * fixed the helper and left the widget printing something else would pass there and fail
   * here.
   */
  it('the rendered anchor says the range is the document\u2019s, not the page\u2019s', () => {
    const markup = viewer(
      anchored({ quote: 'thirty days', page_number: 2, char_start: 712 }),
      2,
    );
    expect(markup).toContain('стр. 2, символы 712\u2013723 по всему документу, а не по странице 2');
  });

  it('the rendered anchor never shows a bare \u201Cchars\u201D range with no convention', () => {
    // The exact pre-repair spelling. It is asserted absent rather than merely different,
    // because "chars 712-746" beside "page 2" is the wrong reading D-25 names.
    const markup = viewer(
      anchored({ quote: 'thirty days', page_number: 2, char_start: 712 }),
      2,
    );
    expect(markup).not.toContain('chars 712');
    expect(markup).toContain('по всему документу');
  });
});

describe('an anchor that disagrees with its quotation is said so, in the open', () => {
  it('renders the alert when the declared span is not the quotation length', () => {
    const markup = viewer(
      { evidence_ordinal: 1, page_number: 7, quote: 'thirty days', char_start: 1200, char_end: 1300 },
      7,
    );
    expect(markup).toContain('am-quotation__inconsistent');
    expect(markup).toContain('Заявленная длина фрагмента не совпадает с цитатой');
    expect(markup).toContain('role="alert"');
  });

  it('does not render it when the anchor agrees, so the alert means something', () => {
    const markup = viewer(anchored({ quote: 'thirty days' }), 7);
    expect(markup).not.toContain('am-quotation__inconsistent');
    expect(markup).not.toContain('Заявленная длина фрагмента не совпадает с цитатой');
  });
});

describe('the PDF island is pointed at the declared page', () => {
  it('addresses the fragment on the object element itself, not only on a data attribute', () => {
    const markup = viewer(anchored({ quote: 'on page eleven', page_number: 11 }), 11);
    // `data=` is what the browser follows. `data-viewer-src` is a test affordance, so
    // asserting the fragment appears "somewhere in the markup" is not the same claim.
    expect(markup).toContain(`data="${OBJECT_URL}#page=11"`);
  });

  it('never points the object at the bare blob URL', () => {
    // Without the fragment the browser opens page 1 of the document, silently showing the
    // reviewer text this finding did not cite.
    const markup = viewer(anchored({ quote: 'on page eleven', page_number: 11 }), 11);
    expect(markup).not.toContain(`data="${OBJECT_URL}"`);
  });
});

// ---------------------------------------------------------------------------------------
// The decision panel
// ---------------------------------------------------------------------------------------

function panel(props: Partial<Parameters<typeof DecisionPanel>[0]> = {}): string {
  return render(
    createElement(DecisionPanel, {
      currentVerdict: 'pending',
      observationId: OBSERVATION_ID,
      onAccept: () => {},
      onReject: () => {},
      onComment: () => {},
      ...props,
    }),
  );
}

describe('a comment the browser refused to send says so', () => {
  it('renders the refusal when the comment was empty', () => {
    const markup = panel({ refusal: 'empty' });
    expect(markup).toContain('am-decision__refusal');
    expect(markup).toContain('Событию комментария нужен текст. Ничего не отправлено.');
  });

  it('renders nothing of the kind when there was no refusal', () => {
    expect(panel()).not.toContain('am-decision__refusal');
    expect(panel({ refusal: null })).not.toContain('am-decision__refusal');
  });

  /**
   * EVERY member of the union, derived from the union rather than listed here.
   *
   * `D-84`: the panel declared `refusal?: string` and rendered on `refusal === 'empty'`.
   * With one member that screen was correct, which is exactly why nothing caught it — and
   * a test naming `'empty'` is a second copy of the same assumption, so it could not catch
   * it either. This one iterates `COMMENT_REFUSALS`, so a member added to the feature
   * fails HERE at run time as well as in `tsc`, and the two failures say different things:
   * the compiler says the sentence is missing, this says the screen is silent.
   */
  it('renders a sentence and the machine value for every refusal the feature can produce', () => {
    expect(COMMENT_REFUSALS.length).toBeGreaterThan(0);
    for (const refusal of COMMENT_REFUSALS) {
      const markup = panel({ refusal });
      expect({ refusal, block: markup.includes('am-decision__refusal') })
        .toEqual({ refusal, block: true });
      expect({ refusal, machine: markup.includes(`data-comment-refusal="${refusal}"`) })
        .toEqual({ refusal, machine: true });
      expect({ refusal, sentence: markup.includes(commentRefusalMessage(refusal)) })
        .toEqual({ refusal, sentence: true });
      // And the sentence is a sentence, not the machine value leaking onto the screen.
      expect({ refusal, russian: /[а-яё]/i.test(commentRefusalMessage(refusal)) })
        .toEqual({ refusal, russian: true });
    }
  });
});

describe('the verdict on the panel is the server projection, not the button pressed', () => {
  it('still reads pending while an accept is in flight', () => {
    // The panel showing `accepted` before the server has recorded it is the panel deciding
    // a verdict. The append is not a verdict until the ledger has the event.
    const markup = panel({ currentVerdict: 'pending', pendingIntent: 'accept' });
    expect(markup).toContain('data-verdict="pending"');
    expect(markup).not.toContain('data-verdict="accepted"');
  });

  it('still reads rejected while a comment is in flight', () => {
    const markup = panel({ currentVerdict: 'rejected', pendingIntent: 'comment' });
    expect(markup).toContain('data-verdict="rejected"');
  });
});

// ---------------------------------------------------------------------------------------
// The decision history
// ---------------------------------------------------------------------------------------

describe('a finding nobody has judged has an unasked question, not an error', () => {
  it('renders the neutral not-applicable block', () => {
    const markup = render(createElement(DecisionHistory, { events: [] }));
    expect(markup).toContain('Решений пока нет');
    // `NotApplicableState` is neutral and carries `role="status"`. An error block is
    // `am-state--error` with `role="alert"`, and says something went wrong when nothing did.
    expect(markup).toContain('am-state--neutral');
    expect(markup).not.toContain('am-state--error');
    expect(markup).not.toContain('role="alert"');
  });
});

describe('the history shows every event, with its verdict and its comment', () => {
  const events: readonly DecisionEvent[] = [
    decisionEvent({
      decision_id: decisionId('A'),
      event_type: 'accept',
      verdict: 'accepted',
      comment: null,
      recorded_at: '2026-09-10T09:00:00.000Z',
    }),
    decisionEvent({
      decision_id: decisionId('B'),
      event_type: 'comment',
      verdict: null,
      comment: 'the 45-day term is operative',
      recorded_at: '2026-09-10T09:05:00.000Z',
    }),
  ];

  it('renders the verdict of the event that carries one', () => {
    const markup = render(createElement(DecisionHistory, { events: [...events] }));
    expect(markup).toContain('am-history__verdict');
    expect(markup).toContain('accepted');
  });

  it('renders the comment text of the event that carries one', () => {
    const markup = render(createElement(DecisionHistory, { events: [...events] }));
    expect(markup).toContain('am-history__comment');
    expect(markup).toContain('the 45-day term is operative');
  });

  it('renders no verdict element for an event that carries none', () => {
    const markup = render(
      createElement(DecisionHistory, {
        events: [
          decisionEvent({ event_type: 'comment', verdict: null, comment: 'just a note' }),
        ],
      }),
    );
    expect(markup).not.toContain('am-history__verdict');
    expect(markup).toContain('just a note');
  });

  it('renders no comment element for an event that carries none', () => {
    const markup = render(
      createElement(DecisionHistory, {
        events: [decisionEvent({ event_type: 'accept', verdict: 'accepted', comment: null })],
      }),
    );
    expect(markup).not.toContain('am-history__comment');
  });
});
