/**
 * The knowledge base screen, and what it may not become.
 *
 * `tests/guards/rendered-language.guard.test.ts` renders this screen in every cache state
 * and judges its language. This file covers what that guard cannot see, and every case
 * here exists because the opposite behaviour would be plausible:
 *
 * * **it derives nothing.** `ADR-0012` makes the knowledge base a projection the server
 *   computes. A screen that counted, grouped or re-projected would be a second answer to a
 *   question the server already answers, and the first thing a second answer does is
 *   disagree. Asserted against the source text, because it is a property of the file.
 * * **it addresses a finding by `finding_uid`, `project_uid` and `run_id`** — `ADR-0010`.
 *   A link built from anything else is the identity defect, and it renders identically.
 * * **a comment event shows no verdict of its own** while the finding's current verdict is
 *   on the same row. Those two values differ exactly when the record is most interesting,
 *   and a widget that printed one where the other belongs looks right in every other case.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import type { DecisionRecord } from '@/shared/api';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { WEB_ROOT } from '../../guards/lib/repo';
import { render } from '../review/fixtures';

const ULID = '01M2545JSD15ETSNNV904X991F';
const PROJECT_UID = `prj_${ULID}`;
const RUN_ID = `run_${ULID}`;
const FINDING_UID = `fnd_${ULID}`;

function record(over: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    decision_id: `dec_${ULID}`,
    finding_uid: FINDING_UID,
    finding_observation_id: `fobs_${ULID}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: null,
    author_label: 'проверяющий',
    recorded_at: '2026-09-10T09:00:00.000Z',
    project_uid: PROJECT_UID,
    run_id: RUN_ID,
    category: 'internal_contradiction',
    finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...over,
  };
}

describe('the knowledge base shows events, not findings', () => {
  it('renders one row per event, so a finding decided twice appears twice', () => {
    const markup = render(
      createElement(KnowledgeBase, {
        records: [
          record({ decision_id: `dec_${ULID}`, event_type: 'comment', verdict: null, comment: 'Спорно.', decision_event_count: 2 }),
          record({ decision_id: 'dec_01M2545JSD15ETSNNV904X992A', decision_event_count: 2 }),
        ],
      }),
    );
    expect(markup.match(/class="am-kb__record"/g) ?? []).toHaveLength(2);
    expect(markup).toContain('data-record-count="2"');
  });

  it('keeps the event verdict and the finding verdict apart on the same row', () => {
    const markup = render(
      createElement(KnowledgeBase, {
        records: [record({ event_type: 'comment', verdict: null, comment: 'Спорно.' })],
      }),
    );
    // The event carried no verdict; the finding stands accepted. Both facts, both visible.
    expect(markup).toContain('data-verdict="none"');
    expect(markup).toContain('data-current-verdict="accepted"');
  });

  it('says how many decisions the finding carries, in words that decline', () => {
    const one = render(createElement(KnowledgeBase, { records: [record()] }));
    const many = render(
      createElement(KnowledgeBase, { records: [record({ decision_event_count: 3 })] }),
    );
    expect(one).toContain('одно решение по находке');
    expect(many).toContain('решений по находке: 3');
  });
});

describe('a row addresses its finding by the identities the record carries', () => {
  it('links to the run through project_uid and run_id and nothing else', () => {
    const markup = render(createElement(KnowledgeBase, { records: [record()] }));
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}/review"`);
    expect(markup).toContain(`data-finding-uid="${FINDING_UID}"`);
  });

  it('can fail: a row built from a different identity renders a different address', () => {
    const markup = render(
      createElement(KnowledgeBase, {
        records: [record({ project_uid: 'prj_01M2545JSD15ETSNNV904X999Z' })],
      }),
    );
    expect(markup).not.toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}/review"`);
  });
});

describe('the three states a read can end in are all explicit', () => {
  it('an empty journal is an emptiness, not a silence and not a failure', () => {
    const markup = render(createElement(KnowledgeBase, { records: [] }));
    expect(markup).toContain('Решений пока нет');
    expect(markup).not.toContain('am-kb__record');
  });

  it('a failure renders the refusal it was given, with its correlation id', () => {
    const markup = render(
      createElement(KnowledgeBase, {
        records: [],
        error: { title: 'База знаний не открылась.', correlationId: 'c-1' },
      }),
    );
    expect(markup).toContain('База знаний не открылась.');
    expect(markup).toContain('c-1');
  });

  it('a read in flight is a loading state and never an empty one', () => {
    const markup = render(createElement(KnowledgeBase, { records: [], isLoading: true }));
    expect(markup).not.toContain('Решений пока нет');
  });
});

describe('the screen computes no projection of its own', () => {
  const SLICE = [
    'src/widgets/knowledge-base/ui/knowledge-base.tsx',
    'src/_pages/knowledge-base/ui/knowledge-base-page.tsx',
  ];

  it('never folds, counts or sorts the records it was given', () => {
    /*
     * `ADR-0012` puts the knowledge-base view on the server. The server orders the journal
     * newest first and counts the events per finding; a client that re-derived either would
     * be a second source of truth, and it would go on rendering plausibly after the
     * server's own answer changed.
     *
     * A source check rather than a behavioural one because the defect is invisible in the
     * markup: a client-side sort of an already-sorted page produces identical output.
     */
    const offenders: string[] = [];
    for (const file of SLICE) {
      const source = readFileSync(join(WEB_ROOT, file), 'utf8');
      const body = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
      for (const forbidden of ['.sort(', '.reduce(', '.filter(', 'projectVerdict', 'orderEvents']) {
        if (body.includes(forbidden)) offenders.push(`${file}: ${forbidden}`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('can fail: the same check over a module that does fold', () => {
    const source = readFileSync(join(WEB_ROOT, 'src/entities/expert-decision/model/ledger.ts'), 'utf8');
    expect(source.includes('.sort(')).toBe(true);
  });
});
