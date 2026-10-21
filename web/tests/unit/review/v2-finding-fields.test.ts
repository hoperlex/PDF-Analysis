/**
 * What a reviewer sees of the v2 finding fields (`REVIEW-V2-UI-01`).
 *
 * The API serves `proposed_severity`, `decided_severity`, `merged_observations`,
 * `norm_citations`, `required_value` and `stated_value`. These cases pin what the review
 * screen does with each, and the one thing that must not change: a finding without them
 * renders and behaves as it did. Each case goes red under a named mutation, quoted in
 * `docs/program/REVIEW-V2-UI-01.md`.
 *
 * Every string the data supplies here is Cyrillic, as `rendered-language.guard.test.ts`
 * seeds its screens, so any Latin word left in the visible text is chrome the application
 * wrote. The visible-text reader below is that guard's own reading (text nodes plus the
 * attributes a browser shows as text); the contract values stay on `data-` attributes and
 * `value=` attributes, which are not read.
 *
 * Rendered to static markup, as the rest of this suite does: no DOM, no `jsdom`.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type {
  Finding,
  FindingDetail,
  FindingObservation,
  NormCitation,
  Severity,
} from '@/shared/api';
import { SEVERITY_VALUES, queryKeys } from '@/shared/api';
import {
  NORM_CITATION_STATE_LABELS,
  SEVERITY_LABELS,
  SeverityBadge,
  groupByCategory,
  normCitationStateLabel,
} from '@/entities/finding';
import { ReviewPage } from '@/_pages/review';
import { DecisionPanel } from '@/widgets/decision-panel';
import { chosenSeverity, draftFromControl } from '@/widgets/decision-panel/model/severity-draft';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { FindingList } from '@/widgets/finding-list';
import { VERDICT_REFUSALS, verdictRefusalMessage } from '@/features/record-verdict';

import {
  FINDING_UID,
  OBSERVATION_ID,
  PROJECT_UID,
  RUN_ID,
  evidence,
  finding,
  findingDetail,
  observation,
  render,
  runStatus,
} from './fixtures';
import { newClient, renderScreen } from '../screens/harness';

// ------------------------------------------------------------------ what the reader sees

/** The text a browser shows: text nodes, plus `title`/`aria-label`/`placeholder`/`alt`. */
function visibleText(markup: string): string[] {
  const out: string[] = [];
  const body = markup.replace(/<style\b[^>]*>[\s\S]*?<\/style>/g, '');
  for (const match of body.matchAll(/>([^<>]+)</g)) {
    const text = (match[1] ?? '').trim();
    if (text.length > 0) out.push(text);
  }
  for (const attribute of ['title', 'aria-label', 'placeholder', 'alt']) {
    for (const match of body.matchAll(new RegExp(`\\s${attribute}="([^"]*)"`, 'g'))) {
      const text = (match[1] ?? '').trim();
      if (text.length > 0) out.push(text);
    }
  }
  return out;
}

/**
 * Latin words in the visible text. Anything here is chrome, because the data is Cyrillic.
 * `PDF` is the one name the viewer's existing chrome carries and the language guard permits
 * (its `NOT_DERIVABLE`: the document format, a proper noun in Russian too).
 */
function latinWords(markup: string): string[] {
  const words = visibleText(markup).join(' ').match(/[A-Za-z][A-Za-z'’]*/g) ?? [];
  return [...new Set(words)].filter((word) => word !== 'PDF');
}

/** The contract's severity values appearing as words a reviewer reads. */
function rawSeverityWords(markup: string): string[] {
  const text = visibleText(markup).join(' ');
  return SEVERITY_VALUES.filter((value) => new RegExp(`(?<![A-Za-z_])${value}(?![A-Za-z_])`).test(text));
}

// ------------------------------------------------------------------ Cyrillic fixtures

const NORM_DOC = 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const NORM_PAR = 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const SNAPSHOT = 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function citation(overrides: Partial<NormCitation> = {}): NormCitation {
  return {
    clause_number: '7.1.4',
    designation: 'СП 1.13130.2020',
    norm_document_id: NORM_DOC,
    norm_paragraph_id: NORM_PAR,
    norms_snapshot_id: SNAPSHOT,
    page_label: 12,
    quote: 'Ширина эвакуационного выхода должна быть не менее 0,8 м.',
    source_attribution: 'consultant_plus',
    state: 'verified',
    title: 'Системы противопожарной защиты. Эвакуационные пути и выходы',
    ...overrides,
  };
}

function cyrillic(overrides: Partial<FindingObservation> = {}): FindingObservation {
  return observation({
    finding_text: 'Ширина выхода указана как 0,7 м.',
    recommendation_text: 'Привести ширину выхода в соответствие с нормой.',
    evidence: [evidence({ quote: 'Ширина выхода — 0,7 м', page_number: 3 })],
    ...overrides,
  });
}

function cyrillicFinding(overrides: Partial<Finding> = {}, observationOverrides: Partial<FindingObservation> = {}): Finding {
  return finding({ observation: cyrillic(observationOverrides), ...overrides });
}

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

function viewer(
  observationValue: FindingObservation,
  mergedObservations?: readonly FindingObservation[],
): string {
  return render(
    createElement(EvidenceViewer, {
      observation: observationValue,
      ...(mergedObservations === undefined ? {} : { mergedObservations }),
      activePage: 3,
      onPageChange: () => {},
      documentUrl: 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100',
    }),
  );
}

function list(items: readonly Finding[]): string {
  return render(
    createElement(FindingList, {
      groups: groupByCategory([...items]),
      selectedFindingUid: null,
      onSelect: () => {},
    }),
  );
}

// ------------------------------------------------------------------ the five labels

describe('the five severities have Russian labels and render as them', () => {
  it('labels exactly the contract’s closed set, each once, in Cyrillic', () => {
    expect(Object.keys(SEVERITY_LABELS).sort()).toEqual([...SEVERITY_VALUES].sort());
    expect(new Set(Object.values(SEVERITY_LABELS)).size).toBe(SEVERITY_VALUES.length);
    for (const value of SEVERITY_VALUES) {
      expect(SEVERITY_LABELS[value]).toMatch(/^[А-Яа-яЁё ]+$/);
    }
  });

  for (const severity of SEVERITY_VALUES) {
    it(`renders «${severity}» as its label, with the contract value on a data attribute only`, () => {
      const markup = render(createElement(SeverityBadge, { severity }));
      expect(markup).toContain(`>${SEVERITY_LABELS[severity]}<`);
      expect(markup).toContain(`data-severity="${severity}"`);
      expect(rawSeverityWords(markup)).toEqual([]);
      expect(latinWords(markup)).toEqual([]);
    });
  }

  it('shows a value outside the closed set as a fault, not as a blank and not as itself', () => {
    const markup = render(createElement(SeverityBadge, { severity: 'urgent' as Severity }));
    expect(markup).toContain('data-closed-vocabulary-fault="severity"');
    expect(markup).toContain('Неизвестная важность');
    expect(markup).not.toContain('urgent');
  });

  it('puts a tooltip on a badge that is given one, in Russian', () => {
    const markup = render(
      createElement(SeverityBadge, { severity: 'critical', title: 'Важность, предложенная моделью' }),
    );
    expect(markup).toContain('title="Важность, предложенная моделью"');
  });
});

// ------------------------------------------------------------------ the decision panel

describe('the severity choice is offered only when the finding has a proposal', () => {
  it('a finding without a proposed severity gets no choice and no mention of severity', () => {
    const markup = panel();
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('data-severity-control');
    expect(markup).not.toContain('data-proposed-severity');
    expect(markup).not.toContain('data-decided-severity');
    expect(markup).not.toContain('Предложение модели');
  });

  it('a finding with one gets a select of the five labels and an empty first option', () => {
    const markup = panel({ proposedSeverity: 'economic' });
    expect(markup).toContain('data-severity-control="accept"');
    expect(markup).toContain('<select');
    const options = [...markup.matchAll(/<option value="([^"]*)"[^>]*>([^<]*)<\/option>/g)].map(
      (m) => [m[1], m[2]],
    );
    expect(options).toEqual([
      ['', 'Выберите важность'],
      ...SEVERITY_VALUES.map((value) => [value, SEVERITY_LABELS[value]]),
    ]);
  });

  it('does not select the model’s proposal for the expert', () => {
    for (const proposedSeverity of SEVERITY_VALUES) {
      const markup = panel({ proposedSeverity });
      // The placeholder is the one selected option; none of the five severities is.
      const selected = [...markup.matchAll(/<option value="([^"]*)"[^>]*selected/g)].map((m) => m[1]);
      expect(selected).toEqual(['']);
    }
  });

  it('shows the proposal as the model’s, in Russian', () => {
    const markup = panel({ proposedSeverity: 'critical' });
    expect(markup).toContain('data-proposed-severity="critical"');
    expect(markup).toContain('Предложение модели:');
    expect(markup).toContain(`>${SEVERITY_LABELS.critical}<`);
    expect(rawSeverityWords(markup)).toEqual([]);
    expect(latinWords(markup)).toEqual([]);
  });

  it('keeps the select out of the way of a pending press', () => {
    expect(panel({ proposedSeverity: 'critical', pendingIntent: 'accept' })).toMatch(/<select[^>]*disabled/);
  });
});

describe('the decided severity is shown beside the verdict', () => {
  for (const decidedSeverity of SEVERITY_VALUES) {
    it(`shows «${decidedSeverity}» as its label`, () => {
      const markup = panel({ currentVerdict: 'accepted', decidedSeverity });
      expect(markup).toContain(`data-decided-severity="${decidedSeverity}"`);
      expect(markup).toContain(`>${SEVERITY_LABELS[decidedSeverity]}<`);
      expect(markup).toContain('title="Важность, решённая экспертом"');
      expect(rawSeverityWords(markup)).toEqual([]);
      expect(latinWords(markup)).toEqual([]);
    });
  }

  it('says nothing about severity when the server sent none', () => {
    expect(panel({ currentVerdict: 'accepted' })).not.toContain('data-decided-severity');
  });

  it('shows the decided one and the proposed one apart when they differ', () => {
    const markup = panel({
      currentVerdict: 'accepted',
      proposedSeverity: 'critical',
      decidedSeverity: 'recommendation',
    });
    expect(markup).toContain('data-proposed-severity="critical"');
    expect(markup).toContain('data-decided-severity="recommendation"');
  });
});

describe('an accept the browser refused for want of a severity says so', () => {
  it('renders the sentence for every refusal there is, as an alert', () => {
    for (const refusal of VERDICT_REFUSALS) {
      const markup = panel({ proposedSeverity: 'critical', severityRefusal: refusal });
      expect(markup).toContain(`data-severity-refusal="${refusal}"`);
      expect(markup).toContain('role="alert"');
      expect(markup).toContain(verdictRefusalMessage(refusal));
      expect(latinWords(markup)).toEqual([]);
    }
  });

  it('renders no refusal when there is none', () => {
    expect(panel({ proposedSeverity: 'critical', severityRefusal: null })).not.toContain(
      'data-severity-refusal',
    );
  });
});

describe('the choice belongs to the observation it was made for', () => {
  const OTHER = 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';

  it('is read back for the same observation and for no other', () => {
    const draft = draftFromControl('economic', OBSERVATION_ID);
    expect(chosenSeverity(draft, OBSERVATION_ID)).toBe('economic');
    expect(chosenSeverity(draft, OTHER)).toBeUndefined();
    expect(chosenSeverity(null, OBSERVATION_ID)).toBeUndefined();
  });

  it('reads each of the five select values as itself', () => {
    for (const value of SEVERITY_VALUES) {
      expect(draftFromControl(value, OBSERVATION_ID)).toEqual({
        observationId: OBSERVATION_ID,
        severity: value,
      });
    }
  });

  it('reads the empty option and anything outside the set as no choice', () => {
    for (const value of ['', 'urgent', 'CRITICAL', ' critical']) {
      expect(draftFromControl(value, OBSERVATION_ID)).toBeNull();
    }
  });
});

// ------------------------------------------------------------------ the finding list

describe('a finding row shows the decided severity beside the verdict', () => {
  it('shows it, as its label, when the finding has one', () => {
    const markup = list([
      cyrillicFinding({ current_verdict: 'accepted', decided_severity: 'operational' }),
    ]);
    expect(markup).toContain('data-decided-severity="operational"');
    expect(markup).toContain(`>${SEVERITY_LABELS.operational}<`);
    expect(markup).toContain('title="Важность, решённая экспертом"');
    expect(rawSeverityWords(markup)).toEqual([]);
    expect(latinWords(markup)).toEqual([]);
  });

  it('shows the model’s proposal nowhere in the list: the row is the expert’s decision', () => {
    const markup = list([cyrillicFinding({ current_verdict: 'pending' }, { proposed_severity: 'critical' })]);
    expect(markup).not.toContain('data-severity=');
    expect(markup).not.toContain('data-decided-severity');
  });

  it('is the row it always was when the finding has no decided severity', () => {
    const markup = list([cyrillicFinding()]);
    expect(markup).not.toContain('data-decided-severity');
    expect(markup).not.toContain('data-severity=');
  });
});

// ------------------------------------------------------------------ the evidence view

describe('a finding without v2 fields shows nothing more in the evidence view', () => {
  it('renders no basis block', () => {
    const markup = viewer(cyrillic());
    expect(markup).not.toContain('data-finding-basis');
    expect(markup).not.toContain('Нормативные ссылки');
    expect(markup).not.toContain('Объединённые наблюдения');
    expect(markup).not.toContain('Требуется по норме');
  });

  it('renders none for an empty list of merged observations either', () => {
    expect(viewer(cyrillic(), [])).not.toContain('data-finding-basis');
  });
});

describe('the required and stated values are printed as served', () => {
  it('prints both, whole, under their labels', () => {
    const markup = viewer(
      cyrillic({ required_value: 'не менее 0,8 м', stated_value: '0,7 м  (в осях А–Б)' }),
    );
    expect(markup).toContain('data-finding-values');
    expect(markup).toContain('Требуется по норме');
    expect(markup).toContain('Указано в документе');
    expect(markup).toContain('<dd data-required-value="">не менее 0,8 м</dd>');
    expect(markup).toContain('<dd data-stated-value="">0,7 м  (в осях А–Б)</dd>');
    expect(latinWords(markup)).toEqual([]);
  });

  it('prints the one that is there and nothing for the other', () => {
    const onlyRequired = viewer(cyrillic({ required_value: 'не менее 0,8 м' }));
    expect(onlyRequired).toContain('data-required-value');
    expect(onlyRequired).not.toContain('data-stated-value');
    expect(onlyRequired).not.toContain('Указано в документе');

    const onlyStated = viewer(cyrillic({ stated_value: '0,7 м' }));
    expect(onlyStated).toContain('data-stated-value');
    expect(onlyStated).not.toContain('data-required-value');
    expect(onlyStated).not.toContain('Требуется по норме');
  });
});

describe('the norm citations keep their three states apart', () => {
  it('absent: says nothing, and in particular not «0»', () => {
    const markup = viewer(cyrillic());
    expect(markup).not.toContain('data-norm-citations');
  });

  it('empty: says the check ran and found none', () => {
    const markup = viewer(cyrillic({ norm_citations: [] }));
    expect(markup).toContain('data-norm-citations="0"');
    expect(markup).toContain('Проверка нормативных ссылок выполнена');
    expect(markup).not.toContain('data-norm-citation=');
  });

  it('listed: shows designation, title, clause, page, quotation, state, source and a link to the page', () => {
    const markup = viewer(cyrillic({ norm_citations: [citation()] }));
    expect(markup).toContain('data-norm-citations="1"');
    expect(markup).toContain(`data-norm-citation="${NORM_PAR}"`);
    expect(markup).toContain('<strong>СП 1.13130.2020</strong>');
    expect(markup).toContain('Системы противопожарной защиты. Эвакуационные пути и выходы');
    expect(markup).toContain('п. 7.1.4');
    expect(markup).toContain('стр. 12');
    expect(markup).toContain('Ширина эвакуационного выхода должна быть не менее 0,8 м.');
    expect(markup).toContain(NORM_CITATION_STATE_LABELS.verified);
    expect(markup).toContain('Источник текста: КонсультантПлюс');
    expect(markup).toContain(`href="/norms/document?id=${NORM_DOC}&amp;page=12"`);
    expect(latinWords(markup)).toEqual([]);
  });

  it('says a rebound citation is rebound, and a citation with no clause number has no clause', () => {
    const markup = viewer(
      cyrillic({ norm_citations: [citation({ state: 'rebound', clause_number: null })] }),
    );
    expect(markup).toContain('data-norm-citation-state="rebound"');
    expect(markup).toContain(NORM_CITATION_STATE_LABELS.rebound);
    expect(markup).not.toContain('п. ');
  });

  it('lists every citation it is given, in the order given', () => {
    const second = citation({
      norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
      designation: 'СП 54.13330.2022',
    });
    const markup = viewer(cyrillic({ norm_citations: [citation(), second] }));
    expect(markup).toContain('data-norm-citations="2"');
    expect(markup.indexOf('СП 1.13130.2020')).toBeLessThan(markup.indexOf('СП 54.13330.2022'));
  });

  it('names a state it does not know instead of rendering the raw value', () => {
    expect(normCitationStateLabel('stale')).toBe('состояние вне набора, известного этому приложению');
    const markup = viewer(
      cyrillic({ norm_citations: [citation({ state: 'stale' as NormCitation['state'] })] }),
    );
    expect(markup).toContain('состояние вне набора, известного этому приложению');
    expect(visibleText(markup).join(' ')).not.toMatch(/\bstale\b/);
  });
});

describe('the merged observations are listed as served', () => {
  const canonical = cyrillic({ proposed_severity: 'critical' });
  const sibling = observation({
    finding_observation_id: 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
    finding_text: 'Ширина выхода в плане 1-го этажа — 0,75 м.',
    proposed_severity: 'economic',
    evidence: [
      evidence({ evidence_ordinal: 2, quote: 'ширина 0,75 м', page_number: 5 }),
      evidence({ evidence_ordinal: 1, quote: 'выход № 2', page_number: 4 }),
    ],
  });

  it('lists every observation, the canonical one marked rather than dropped', () => {
    const markup = viewer(canonical, [canonical, sibling]);
    expect(markup).toContain('data-merged-observations="2"');
    expect(markup).toContain('Объединённые наблюдения: 2');
    expect(markup).toContain(`data-merged-observation="${canonical.finding_observation_id}"`);
    expect(markup).toContain(`data-merged-observation="${sibling.finding_observation_id}"`);
    expect(markup.match(/>основное</g)).toHaveLength(1);
  });

  it('shows each one’s proposed severity as the model’s, in Russian', () => {
    const markup = viewer(canonical, [canonical, sibling]);
    expect(markup).toContain('data-proposed-severity="critical"');
    expect(markup).toContain('data-proposed-severity="economic"');
    expect(markup).toContain(`>${SEVERITY_LABELS.economic}<`);
    expect(rawSeverityWords(markup)).toEqual([]);
  });

  it('prints each quotation as served, with its page, in page then ordinal order', () => {
    const markup = viewer(canonical, [sibling]);
    expect(markup).toContain('data-merged-quote="выход № 2"');
    expect(markup).toContain('data-merged-quote="ширина 0,75 м"');
    expect(markup.indexOf('выход № 2')).toBeLessThan(markup.indexOf('ширина 0,75 м'));
    expect(markup).toContain('стр. 4, 5');
  });

  it('marks nothing as canonical when the canonical one is not in the list', () => {
    expect(viewer(canonical, [sibling])).not.toContain('>основное<');
  });

  it('prints no proposed severity for an observation that has none', () => {
    const plain = observation({
      finding_observation_id: 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
      finding_text: 'Ширина выхода указана без единицы.',
    });
    expect(viewer(canonical, [plain])).not.toContain('data-proposed-severity');
  });

  it('is Russian throughout', () => {
    expect(latinWords(viewer(canonical, [canonical, sibling]))).toEqual([]);
  });
});

// ------------------------------------------------------------------ the page wires them

/**
 * The review screen over a cache that holds one run, its one finding and that finding's
 * detail: what `useQuery` serves on a first pass, with no network.
 */
function reviewPage(detail: FindingDetail): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
  // The detail is the list item plus two properties the page never reads from the list.
  client.setQueryData(queryKeys.runs.findings(RUN_ID), {
    data: { items: [detail], page: { next_cursor: null } },
  });
  client.setQueryData(queryKeys.findings.detail(detail.finding_uid), { data: detail });
  client.setQueryData(queryKeys.findings.decisions(detail.finding_uid), {
    data: { items: [], page: { next_cursor: null } },
  });
  return renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

describe('the review screen hands the fields to the widgets', () => {
  const fixturesDetail = (overrides: Partial<FindingDetail> = {}, observationOverrides: Partial<FindingObservation> = {}) =>
    findingDetail({ observation: cyrillic(observationOverrides), ...overrides });

  it('a finding without the fields renders the screen it always did', () => {
    const markup = reviewPage(fixturesDetail());
    expect(markup).toContain(`data-finding-uid="${FINDING_UID}"`);
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('data-finding-basis');
    expect(markup).not.toContain('data-decided-severity');
  });

  it('a finding with them shows the choice, the decided severity, the merged observations and the basis', () => {
    const canonical = cyrillic({
      proposed_severity: 'critical',
      required_value: 'не менее 0,8 м',
      stated_value: '0,7 м',
      norm_citations: [citation()],
    });
    const markup = reviewPage(
      fixturesDetail(
        {
          decided_severity: 'economic',
          current_verdict: 'accepted',
          merged_observations: [canonical],
        },
        canonical,
      ),
    );
    expect(markup).toContain('data-severity-control="accept"');
    expect(markup).toContain('data-proposed-severity="critical"');
    expect(markup).toContain('data-decided-severity="economic"');
    expect(markup).toContain('data-merged-observations="1"');
    expect(markup).toContain('data-finding-values');
    expect(markup).toContain('data-norm-citations="1"');
  });
});
