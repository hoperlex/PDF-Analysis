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
import type { KnowledgeBaseNarrowing } from '@/widgets/knowledge-base';

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
    document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    project_name: 'Школа',
    document_name: 'АР-1',
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
  it('links to «Разбор» on the finding through project_uid, run_id and finding_uid and nothing else (UI-B-38)', () => {
    const markup = render(createElement(KnowledgeBase, { records: [record()] }));
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}/review?finding=${FINDING_UID}"`);
    expect(markup).toContain('class="am-kb__link"');
    expect(markup).toContain('Открыть находку');
    expect(markup).not.toContain('Открыть прогон');
    expect(markup).toContain(`data-finding-uid="${FINDING_UID}"`);
  });

  it('can fail: a row built from a different identity renders a different address', () => {
    const markup = render(
      createElement(KnowledgeBase, {
        records: [record({ project_uid: 'prj_01M2545JSD15ETSNNV904X999Z' })],
      }),
    );
    expect(markup).not.toContain(`href="/projects/${PROJECT_UID}/runs/${RUN_ID}/review?finding=${FINDING_UID}"`);
  });

  it('can fail: a row of another finding addresses another finding', () => {
    const markup = render(
      createElement(KnowledgeBase, { records: [record({ finding_uid: 'fnd_01M2545JSD15ETSNNV904X999Z' })] }),
    );
    expect(markup).toContain(`/review?finding=fnd_01M2545JSD15ETSNNV904X999Z"`);
    expect(markup).not.toContain(`/review?finding=${FINDING_UID}"`);
  });
});

describe('a row says where it belongs: «Проект · Документ · Раздел» (UI-PARITY-P0A)', () => {
  function place(markup: string): string {
    const match = markup.match(/<p class="am-kb__meta" data-record-place="true">([^<]*)<\/p>/);
    if (match === null) throw new Error('no place line in the markup');
    return match[1]!;
  }

  it('joins the project, the document and the confirmed section’s catalogue name', () => {
    const markup = render(createElement(KnowledgeBase, { records: [record({ section: 'KM' })] }));
    expect(place(markup)).toBe('Школа · АР-1 · Конструкции металлические (КМ)');
  });

  it('carries the names the record carries, not an identity', () => {
    const markup = render(
      createElement(KnowledgeBase, { records: [record({ project_name: 'Больница', document_name: 'Том 3' })] }),
    );
    expect(place(markup)).toContain('Больница · Том 3');
    expect(place(markup)).not.toContain(PROJECT_UID);
  });

  it('omits the section part, and invents no label, when the record has no section', () => {
    const markup = render(createElement(KnowledgeBase, { records: [record()] }));
    expect(place(markup)).toBe('Школа · АР-1');
    expect(markup).not.toContain('Без раздела');
  });

  it('fails closed on a section code the catalogue does not hold', () => {
    const broken = { ...record(), section: 'ZZ' } as unknown as DecisionRecord;
    const markup = render(createElement(KnowledgeBase, { records: [broken] }));
    expect(markup).toContain('data-knowledge-base-fault="closed-vocabulary"');
    expect(markup).not.toContain('data-record-place');
    expect(markup).not.toContain('ZZ');
  });
});

describe('hostile-width reviewer text remains in a contained knowledge-base row', () => {
  it('renders an unbroken 400-character comment under the row containment class', () => {
    const unbroken = 'Ж'.repeat(400);
    const markup = render(
      createElement(KnowledgeBase, {
        records: [record({ event_type: 'comment', verdict: null, comment: unbroken })],
      }),
    );
    expect(unbroken).toHaveLength(400);
    expect(markup).toContain('class="am-kb__record"');
    expect(markup).toContain(`class="am-kb__comment">${unbroken}</p>`);
  });
});

describe('the three states a read can end in are all explicit', () => {
  it('an empty journal is an emptiness, not a silence and not a failure', () => {
    const markup = render(createElement(KnowledgeBase, { records: [] }));
    expect(markup).toContain('Решений пока нет');
    expect(markup).not.toContain('am-kb__record');
  });

  it('the whole journal being empty is the only place that says the installation has taken no decision', () => {
    const markup = render(createElement(KnowledgeBase, { records: [] }));
    expect(markup).toContain('data-knowledge-base-empty="installation"');
    expect(markup).toContain('В этой установке ещё не принято ни одного решения');
    expect(markup).not.toContain('По выбранному отбору');
    expect(markup).not.toContain('Сбросить категорию и вердикт');
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

describe('an empty page under a category, a verdict or a project is about that selection (D-313)', () => {
  const both = { onResetFilters: () => {}, allProjectsHref: '/knowledge-base?foo=bar' };
  const empty = (narrowing: KnowledgeBaseNarrowing) =>
    render(createElement(KnowledgeBase, { records: [], narrowing }));

  it('says nothing about the installation, only that nothing fits the selection', () => {
    const markup = empty(both);
    expect(markup).toContain('data-knowledge-base-empty="narrowed"');
    expect(markup).toContain('По выбранному отбору решений нет');
    expect(markup).not.toContain('ещё не принято ни одного решения');
    expect(markup).not.toContain('Решений пока нет');
    expect(markup).not.toContain('data-knowledge-base-empty="installation"');
  });

  it('offers both ways back when a filter and a project are on: the reset button and «Все проекты»', () => {
    const markup = empty(both);
    expect(markup).toMatch(/<button [^>]*class="am-button am-button--quiet"[^>]*>Сбросить категорию и вердикт<\/button>/);
    expect(markup).toMatch(/<a [^>]*class="am-button am-button--quiet"[^>]*href="\/knowledge-base\?foo=bar"[^>]*>Все проекты<\/a>|<a [^>]*href="\/knowledge-base\?foo=bar"[^>]*class="am-button am-button--quiet"[^>]*>Все проекты<\/a>/);
  });

  it('offers only the reset when only a filter is on, and only «Все проекты» when only a project is', () => {
    const filterOnly = empty({ onResetFilters: () => {} });
    expect(filterOnly).toContain('Сбросить категорию и вердикт');
    expect(filterOnly).not.toContain('Все проекты');
    const projectOnly = empty({ allProjectsHref: '/knowledge-base' });
    expect(projectOnly).toContain('>Все проекты<');
    expect(projectOnly).not.toContain('Сбросить категорию и вердикт');
    expect(projectOnly).not.toContain('<button');
  });

  it('is only for an empty page: a narrowed list that has records shows them, and a read in flight is not an empty one', () => {
    const rows = render(createElement(KnowledgeBase, { records: [record()], narrowing: both }));
    expect(rows).toContain('class="am-kb__record"');
    expect(rows).not.toContain('По выбранному отбору');
    const loading = render(createElement(KnowledgeBase, { records: [], isLoading: true, narrowing: both }));
    expect(loading).not.toContain('По выбранному отбору');
    expect(loading).not.toContain('data-knowledge-base-empty');
  });
});

describe('closed transport vocabulary fails closed', () => {
  const cases = [
    ['current_verdict', { current_verdict: 'guessed' }],
    ['category', { category: 'guessed' }],
    ['event_type', { event_type: 'guessed' }],
    ['event verdict', { verdict: 'guessed' }],
  ] as const;

  for (const [name, mutation] of cases) {
    it(`shows one typed fault for an unknown ${name}`, () => {
      const broken = { ...record(), ...mutation } as unknown as DecisionRecord;
      const markup = render(createElement(KnowledgeBase, { records: [broken] }));
      expect(markup).toContain('data-knowledge-base-fault="closed-vocabulary"');
      expect(markup).toContain('Запись решения содержит неизвестное значение.');
      expect(markup).not.toContain('class="am-kb__record"');
      expect(markup).not.toContain('guessed');
    });
  }
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
