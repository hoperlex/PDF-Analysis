/**
 * «Нормативные ссылки» on the run page (`NORM-REFS-RUN-01`): the normative documents a run's
 * text cites, each against the norms snapshot the run pinned. Read-only, no finding.
 *
 * Rendered, not read from source (`D-53`): every assertion is on markup a reviewer would see.
 * The subject is the five outcomes — each worded once, none judged — the page each citation
 * occurs on, the pages that could not be read, the true count when the server keeps ten
 * occurrences, and the corpus documents whose designation cannot be read.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { NormReferenceItem, RunNormReferences } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  NORM_REFERENCE_OUTCOME_LABELS,
  NORM_REFERENCE_OUTCOME_MEANINGS,
  NORM_REFERENCE_OUTCOME_ORDER,
  NORM_REFERENCE_STATE_MESSAGES,
  UNKNOWN_VALUE_LABEL,
  citationPlaces,
  normReferenceOutcomeLabel,
  runNormReferencesQueryOptions,
} from '@/entities/norm-reference';
import { NormReferencesAnswer, NormReferencesSection } from '@/widgets/norm-references';

import { newClient, renderScreen, seedError } from '../screens/harness';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const RUN = `run_${ULID}`;
const VERSION = `ver_${ULID}`;
const SNAPSHOT = `ns_${ULID}`;
const DOC_A = `ndoc_${ULID}`;
const DOC_B = 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const DOC_C = 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8H';

function anchor(page: number, start = 10): NormReferenceItem['anchors'][number] {
  return { page_number: page, char_start: start, char_end: start + 16, quote: 'СП 54.13330.2011' };
}

function matched(over: Partial<NormReferenceItem>): NormReferenceItem {
  return {
    cited: 'СП 54.13330.2022', outcome: 'in_corpus', occurrence_count: 1, anchors: [anchor(3)],
    matched_norm_document_id: DOC_A, matched_designation: 'СП 54.13330.2022',
    matched_title: 'Свод правил. Здания жилые', ...over,
  };
}

/** An item that points at no corpus document: the matched properties are absent, not null. */
function unmatched(
  over: Pick<NormReferenceItem, 'cited' | 'outcome' | 'anchors'> & Partial<NormReferenceItem>,
): NormReferenceItem {
  return { occurrence_count: 1, ...over };
}

function answer(over: Partial<RunNormReferences> = {}): RunNormReferences {
  // The corpus document has no title after its designation: the property is absent, not null.
  const olderOnly: NormReferenceItem = {
    cited: 'ГОСТ 21.101-2021', outcome: 'older_edition_only', occurrence_count: 1, anchors: [anchor(4)],
    matched_norm_document_id: DOC_C, matched_designation: 'ГОСТ 21.101-2020',
  };
  const items: NormReferenceItem[] = [
    matched({}),
    matched({
      cited: 'СП 54.13330.2011', outcome: 'newer_edition', occurrence_count: 2,
      anchors: [anchor(1), anchor(7)], matched_norm_document_id: DOC_B,
      matched_designation: 'СП 54.13330.2024',
    }),
    olderOnly,
    unmatched({ cited: 'ГОСТ Р 99999-2020', outcome: 'not_in_corpus', anchors: [anchor(5)] }),
    unmatched({ cited: 'СП 54.13330', outcome: 'not_recognised', anchors: [anchor(6)] }),
  ];
  return {
    run_id: RUN, version_uid: VERSION, state: 'ready', page_count: 8, norms_snapshot_id: SNAPSHOT,
    text_layer_sha256: 'e'.repeat(64), snapshot_document_count: 674,
    counts: { in_corpus: 1, newer_edition: 1, older_edition_only: 1, not_in_corpus: 1, not_recognised: 1 },
    occurrence_count: 6, unread_pages: [2], items,
    unrecognised: [{ norm_document_id: DOC_C, slug: 'МДС_12-24_2006', designation: 'МДС 12-24.2006', title: 'Устройство обычных' }],
    ...over,
  };
}

function render(value: RunNormReferences): string {
  return renderToStaticMarkup(createElement(NormReferencesAnswer, { answer: value }));
}

function rowOf(markup: string, citedText: string): string {
  const start = markup.indexOf(`data-norm-reference="${citedText}"`);
  expect(start, citedText).toBeGreaterThan(-1);
  return markup.slice(start, markup.indexOf('</tr>', start));
}

function text(markup: string): string {
  return markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
}

describe('the five outcomes', () => {
  const markup = render(answer());

  it('are worded once each, in the order they are listed and counted', () => {
    expect(NORM_REFERENCE_OUTCOME_ORDER).toEqual([
      'in_corpus', 'newer_edition', 'older_edition_only', 'not_in_corpus', 'not_recognised',
    ]);
    expect(NORM_REFERENCE_OUTCOME_ORDER.map(normReferenceOutcomeLabel)).toEqual([
      'есть в корпусе', 'в корпусе есть более новая редакция', 'в корпусе только более ранняя редакция',
      'нет в корпусе', 'не распознано',
    ]);
    expect(new Set(Object.values(NORM_REFERENCE_OUTCOME_LABELS)).size).toBe(5);
    expect(Object.keys(NORM_REFERENCE_OUTCOME_MEANINGS)).toEqual(Object.keys(NORM_REFERENCE_OUTCOME_LABELS));
  });

  it('each row carries its own outcome, and the counts carry all five', () => {
    for (const [citedText, outcome] of [
      ['СП 54.13330.2022', 'in_corpus'], ['СП 54.13330.2011', 'newer_edition'],
      ['ГОСТ 21.101-2021', 'older_edition_only'], ['ГОСТ Р 99999-2020', 'not_in_corpus'],
      ['СП 54.13330', 'not_recognised'],
    ] as const) {
      const row = rowOf(markup, citedText);
      expect(row).toContain(`data-norm-reference-outcome="${outcome}"`);
      expect(text(row)).toContain(NORM_REFERENCE_OUTCOME_LABELS[outcome]);
    }
    expect([...markup.matchAll(/data-norm-reference-count="([a-z_]+)"/g)].map((match) => match[1])).toEqual(
      NORM_REFERENCE_OUTCOME_ORDER,
    );
  });

  it('explain the earlier-only edition as a stale corpus, not a project error', () => {
    const legend = text(markup.slice(markup.indexOf('data-norm-reference-legend')));
    expect(legend).toContain('в корпусе только более ранняя редакция');
    expect(legend).toContain('база не обновлена');
    expect(legend).toContain('ошибкой проекта это не считается');
  });

  it('never claim a finding or a severity', () => {
    expect(text(markup)).not.toMatch(/замечани[ея]\s+(созда|добав)|серьёзност/i);
  });
});

describe('where a citation occurs', () => {
  it('names the pages, ascending and distinct, and says how many more the server did not keep', () => {
    expect(citationPlaces([anchor(7), anchor(1), anchor(7)], 3)).toBe('с. 1, 7');
    expect(citationPlaces([anchor(3)], 1)).toBe('с. 3');
    const ten = Array.from({ length: 10 }, (_, index) => anchor(index + 1));
    expect(citationPlaces(ten, 12)).toBe('с. 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 и ещё 2');
  });

  it('shows them in the row, with «Открыть норму» pointing at the matched norm only', () => {
    const markup = render(answer());
    expect(text(rowOf(markup, 'СП 54.13330.2011'))).toContain('с. 1, 7');
    expect(rowOf(markup, 'СП 54.13330.2011')).toContain(`href="/norms/document?id=${DOC_B}"`);
    expect(rowOf(markup, 'СП 54.13330.2011')).toContain('Открыть норму');
    for (const unmatched of ['ГОСТ Р 99999-2020', 'СП 54.13330']) {
      expect(rowOf(markup, unmatched)).not.toContain('Открыть норму');
    }
  });

  it('names the pages with no text layer and says their citations were not found', () => {
    const markup = text(render(answer({ unread_pages: [2, 5] })));
    expect(markup).toContain('Страницы без текстового слоя: 2, 5. Ссылки на них не найдены.');
    expect(text(render(answer({ unread_pages: [] })))).not.toContain('без текстового слоя');
  });
});

describe('the corpus documents whose designation cannot be read', () => {
  it('are listed explicitly, each with a way to open it', () => {
    const markup = render(answer());
    expect(text(markup)).toContain('Документы корпуса с нераспознанным обозначением: 1');
    expect(markup).toContain(`data-norm-unrecognised-document="${DOC_C}"`);
    expect(markup).toContain(`href="/norms/document?id=${DOC_C}"`);
  });

  it('are not announced when there are none', () => {
    expect(render(answer({ unrecognised: [] }))).not.toContain('data-norm-unrecognised=');
  });
});

describe('a state is said, never shown as an empty list', () => {
  for (const state of ['snapshot_not_pinned', 'text_unavailable', 'too_many_citations'] as const) {
    it(`${state} is one sentence`, () => {
      const markup = render({
        run_id: RUN, version_uid: VERSION, state, page_count: 8,
      });
      expect(markup).toContain(`data-norm-references-state="${state}"`);
      expect(text(markup)).toContain(NORM_REFERENCE_STATE_MESSAGES[state]);
      expect(markup).not.toContain('<table');
    });
  }

  it('a ready answer with no citation says so, with zero counts', () => {
    const markup = render(answer({
      items: [], occurrence_count: 0,
      counts: { in_corpus: 0, newer_edition: 0, older_edition_only: 0, not_in_corpus: 0, not_recognised: 0 },
    }));
    expect(text(markup)).toContain('В тексте проекта не найдено ссылок на нормативные документы.');
    expect(markup).not.toContain('<table');
  });

  it('a value outside the known sets is reported as such, never guessed', () => {
    expect(normReferenceOutcomeLabel('from_the_future')).toBe(UNKNOWN_VALUE_LABEL);
  });
});

describe('the section', () => {
  it('reads through the shared query key', () => {
    expect(runNormReferencesQueryOptions(RUN).queryKey).toEqual(queryKeys.runs.normReferences(RUN));
    expect(queryKeys.runs.normReferences(RUN)).toEqual(['runs', 'norm-references', RUN]);
  });

  it('renders its heading and the read-only rule', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.normReferences(RUN), answer());
    const markup = renderScreen(client, createElement(NormReferencesSection, { runId: RUN }));
    expect(markup).toContain('Нормативные ссылки');
    expect(text(markup)).toContain('она не создаёт замечаний');
  });

  it('says a failure with its correlation id and a retry', () => {
    const client = newClient();
    seedError(
      client,
      queryKeys.runs.normReferences(RUN),
      new ApiError(404, {
        contract_version: '1.3.0', error_code: 'not_found', message: 'Нет такого прогона.',
        correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: false,
      }, '0f0e9d8c-7b6a-4948-b726-150413021100'),
    );
    const markup = renderScreen(client, createElement(NormReferencesSection, { runId: RUN }));
    expect(markup).toContain('Нормативные ссылки не прочитаны');
    expect(markup).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
    expect(markup).not.toContain('data-norm-references-state');
  });
});
