/**
 * The decision history and the knowledge base show a decision's severity beside its verdict
 * (`WEB-REVIEW-FOLLOWUPS-01`, item 1).
 *
 * The API serves `DecisionEvent.severity` and `DecisionRecord.severity` (the severity the
 * expert decided on an accept), and `REVIEW-V2-UI-01` made the review screen show it in the
 * decision panel and the finding list. The two widgets below still printed the verdict alone.
 * The cases pin three things, each red under a quoted mutation (see
 * `docs/program/WEB-REVIEW-FOLLOWUPS-01.md`):
 *
 *   - an event or record that carries a severity shows it with the existing `SeverityBadge`,
 *     in Russian, for every member of the closed set, after the verdict and before the time
 *     (history) or the event type (knowledge base);
 *   - an event or record WITHOUT one renders exactly the markup it rendered before, byte for
 *     byte (the legacy line is written out below, not derived from the widget);
 *   - no raw contract value is read as a word, and a value outside the closed set is shown as
 *     the badge's own fault, not as a blank and not as the raw string.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DecisionEvent, DecisionRecord, Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { CATEGORY_LABELS } from '@/entities/expert-decision';
import { SEVERITY_LABELS } from '@/entities/finding';
import { DecisionHistory } from '@/widgets/decision-history';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { decisionEvent, decisionId, render } from './fixtures';

// ------------------------------------------------------------------ what the reader sees

/** The text a browser shows: text nodes, plus `title`/`aria-label`/`placeholder`/`alt`. */
function visibleText(markup: string): string[] {
  const out: string[] = [];
  for (const match of markup.matchAll(/>([^<>]+)</g)) {
    const text = (match[1] ?? '').trim();
    if (text.length > 0) out.push(text);
  }
  for (const attribute of ['title', 'aria-label', 'placeholder', 'alt']) {
    for (const match of markup.matchAll(new RegExp(`\\s${attribute}="([^"]*)"`, 'g'))) {
      const text = (match[1] ?? '').trim();
      if (text.length > 0) out.push(text);
    }
  }
  return out;
}

/** The contract's severity values appearing as words a reviewer reads. */
function rawSeverityWords(markup: string): string[] {
  const text = visibleText(markup).join(' ');
  return SEVERITY_VALUES.filter((value) => new RegExp(`(?<![A-Za-z_])${value}(?![A-Za-z_])`).test(text));
}

// ------------------------------------------------------------------ fixtures

const ULID = '01M2545JSD15ETSNNV904X991F';
const AT = '2026-09-10T09:00:00.000Z';

function history(events: readonly DecisionEvent[]): string {
  return render(createElement(DecisionHistory, { events }));
}

function record(over: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    decision_id: `dec_${ULID}`,
    finding_uid: `fnd_${ULID}`,
    finding_observation_id: `fobs_${ULID}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: null,
    author_label: 'проверяющий',
    recorded_at: AT,
    project_uid: `prj_${ULID}`,
    run_id: `run_${ULID}`,
    category: 'internal_contradiction',
    finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...over,
  };
}

function base(records: readonly DecisionRecord[]): string {
  return render(createElement(KnowledgeBase, { records }));
}

/** The line of one history event, up to and excluding its comment paragraph. */
function historyLine(markup: string): string {
  return /<p class="am-history__line">.*?<\/p>/.exec(markup)?.[0] ?? '';
}

/** The heading of one knowledge-base record. */
function kbHeading(markup: string): string {
  return /<p class="am-kb__heading">.*?<\/p>/.exec(markup)?.[0] ?? '';
}

// ------------------------------------------------------------------ the decision history

describe('the decision history shows the severity beside the verdict', () => {
  for (const severity of SEVERITY_VALUES) {
    it(`shows «${SEVERITY_LABELS[severity]}» with its badge for an accept that carries «${severity}»`, () => {
      const markup = history([decisionEvent({ severity })]);
      expect(markup).toContain(`data-severity="${severity}"`);
      expect(markup).toContain(`<span class="am-badge__label">${SEVERITY_LABELS[severity]}</span>`);
      expect(markup).toContain('am-badge');
    });
  }

  it('says whose severity it is, in words: the expert’s, decided with the verdict', () => {
    const markup = history([decisionEvent({ severity: 'economic' })]);
    expect(visibleText(markup)).toContain('важность');
    expect(markup).toContain('title="Важность, решённая экспертом"');
  });

  it('puts it after the verdict and before the time and the author', () => {
    const line = historyLine(history([decisionEvent({ severity: 'critical' })]));
    const verdictAt = line.indexOf('am-history__verdict');
    const severityAt = line.indexOf('data-severity="critical"');
    const timeAt = line.indexOf('am-history__at');
    const authorAt = line.indexOf('am-history__author');
    expect(verdictAt).toBeGreaterThan(-1);
    expect(severityAt).toBeGreaterThan(verdictAt);
    expect(timeAt).toBeGreaterThan(severityAt);
    expect(authorAt).toBeGreaterThan(timeAt);
  });

  it('keeps the verdict span and its contract value where they were', () => {
    const line = historyLine(history([decisionEvent({ severity: 'critical' })]));
    expect(line).toContain('<span class="am-history__verdict" data-verdict="accepted"> → принято</span>');
  });

  it('shows each event’s own severity, and nothing for the events that carry none', () => {
    const markup = history([
      decisionEvent({ decision_id: decisionId('A'), severity: 'critical', recorded_at: '2026-09-10T09:00:00.000Z' }),
      decisionEvent({
        decision_id: decisionId('B'),
        event_type: 'comment',
        verdict: null,
        comment: 'Уточнил у заказчика.',
        recorded_at: '2026-09-10T09:05:00.000Z',
      }),
      decisionEvent({
        decision_id: decisionId('C'),
        event_type: 'reject',
        verdict: 'rejected',
        recorded_at: '2026-09-10T09:10:00.000Z',
      }),
    ]);
    expect(markup.match(/data-severity=/g) ?? []).toHaveLength(1);
    const lines = markup.match(/<li class="am-history__event".*?<\/li>/g) ?? [];
    expect(lines).toHaveLength(3);
    expect(lines[0]).toContain('data-severity="critical"');
    expect(lines[1]).not.toContain('data-severity');
    expect(lines[2]).not.toContain('data-severity');
  });

  it('never prints a raw contract value as a word, for any severity', () => {
    for (const severity of SEVERITY_VALUES) {
      expect(rawSeverityWords(history([decisionEvent({ severity })]))).toEqual([]);
    }
  });

  it('shows a value outside the closed set as the badge’s fault, not as a blank or as a word', () => {
    const markup = history([
      decisionEvent({ severity: 'urgent' as Severity }),
      decisionEvent({ decision_id: decisionId('B'), recorded_at: '2026-09-10T09:05:00.000Z' }),
    ]);
    expect(markup).toContain('data-closed-vocabulary-fault="severity"');
    expect(markup).toContain('Неизвестная важность');
    // The machine value may sit on a `data-` attribute; no reader sees it there.
    expect(visibleText(markup).join(' ')).not.toContain('urgent');
    // The other event is still there: one bad severity does not hide the ledger.
    expect(markup).toContain('data-event-count="2"');
  });
});

describe('an event without a severity renders the markup it always rendered', () => {
  it('prints the legacy line for an accept with no severity key at all', () => {
    const line = historyLine(history([decisionEvent()]));
    expect(line).toBe(
      '<p class="am-history__line">' +
        '<span class="am-history__type">приём</span>' +
        '<span class="am-history__verdict" data-verdict="accepted"> → принято</span>' +
        `<span class="am-history__at"> ${formatInstant(AT)}</span>` +
        '<span class="am-history__author"> local-reviewer</span>' +
        '</p>',
    );
  });

  it('prints the legacy line for a comment (no verdict, no severity)', () => {
    const line = historyLine(
      history([decisionEvent({ event_type: 'comment', verdict: null, comment: 'Заметка.' })]),
    );
    expect(line).toBe(
      '<p class="am-history__line">' +
        '<span class="am-history__type">комментарий</span>' +
        `<span class="am-history__at"> ${formatInstant(AT)}</span>` +
        '<span class="am-history__author"> local-reviewer</span>' +
        '</p>',
    );
  });

  it('adds no badge, no label and no data attribute to the legacy markup', () => {
    const markup = history([decisionEvent()]);
    expect(markup).not.toContain('data-severity');
    expect(markup).not.toContain('data-decided-severity');
    expect(markup).not.toContain('важность');
    expect(markup).not.toContain('am-badge');
  });
});

// ------------------------------------------------------------------ the knowledge base

describe('the knowledge base shows the severity beside the verdict', () => {
  for (const severity of SEVERITY_VALUES) {
    it(`shows «${SEVERITY_LABELS[severity]}» with its badge for a record that carries «${severity}»`, () => {
      const markup = base([record({ severity })]);
      expect(markup).toContain(`data-severity="${severity}"`);
      expect(markup).toContain(`<span class="am-badge__label">${SEVERITY_LABELS[severity]}</span>`);
    });
  }

  it('says whose severity it is, in words', () => {
    const markup = base([record({ severity: 'operational' })]);
    expect(visibleText(markup)).toContain('важность');
    expect(markup).toContain('title="Важность, решённая экспертом"');
  });

  it('puts it in the heading, after the verdict and before the event type', () => {
    const heading = kbHeading(base([record({ severity: 'critical' })]));
    const verdictAt = heading.indexOf('am-kb__verdict');
    const severityAt = heading.indexOf('data-severity="critical"');
    const eventAt = heading.indexOf('am-kb__event');
    expect(verdictAt).toBeGreaterThan(-1);
    expect(severityAt).toBeGreaterThan(verdictAt);
    expect(eventAt).toBeGreaterThan(severityAt);
  });

  it('keeps the verdict span with the finding’s current verdict as it was', () => {
    const heading = kbHeading(base([record({ severity: 'critical', current_verdict: 'rejected' })]));
    expect(heading).toContain('<span class="am-kb__verdict" data-verdict="rejected">отклонено</span>');
  });

  it('shows each record’s own severity: the accept carries one, a later comment on it does not', () => {
    const markup = base([
      record({ decision_id: `dec_${ULID}`, event_type: 'comment', verdict: null, comment: 'Спорно.', decision_event_count: 2 }),
      record({ decision_id: 'dec_01M2545JSD15ETSNNV904X992A', severity: 'economic', decision_event_count: 2 }),
    ]);
    const rows = markup.match(/<li class="am-kb__record".*?<\/li>/g) ?? [];
    expect(rows).toHaveLength(2);
    expect(rows[0]).not.toContain('data-severity');
    expect(rows[1]).toContain('data-severity="economic"');
  });

  it('never prints a raw contract value as a word, for any severity', () => {
    for (const severity of SEVERITY_VALUES) {
      expect(rawSeverityWords(base([record({ severity })]))).toEqual([]);
    }
  });

  it('shows a value outside the closed set as the badge’s fault, not as a blank or as a word', () => {
    const markup = base([record({ severity: 'urgent' as Severity })]);
    expect(markup).toContain('data-closed-vocabulary-fault="severity"');
    expect(markup).toContain('Неизвестная важность');
    // The machine value may sit on a `data-` attribute; no reader sees it there.
    expect(visibleText(markup).join(' ')).not.toContain('urgent');
  });
});

describe('a record without a severity renders the markup it always rendered', () => {
  it('prints the legacy heading for an accept with no severity key at all', () => {
    const heading = kbHeading(base([record()]));
    expect(heading).toBe(
      '<p class="am-kb__heading">' +
        `<span class="am-kb__category">${CATEGORY_LABELS.internal_contradiction}</span>` +
        '<span class="am-kb__verdict" data-verdict="accepted">принято</span>' +
        '<span class="am-kb__event">приём</span>' +
        '</p>',
    );
  });

  it('adds no badge, no label and no data attribute to the legacy markup', () => {
    const markup = base([record()]);
    expect(markup).not.toContain('data-severity');
    expect(markup).not.toContain('важность');
    expect(markup).not.toContain('am-badge');
  });
});
