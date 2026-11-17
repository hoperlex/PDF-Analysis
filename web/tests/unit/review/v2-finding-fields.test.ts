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

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type {
  Finding,
  FindingDetail,
  FindingObservation,
  NormCitation,
  Severity,
} from '@/shared/api';
import { NORM_CITATION_STATE_VALUES, SEVERITY_VALUES, queryKeys } from '@/shared/api';
import {
  NORM_CITATION_STATE_LABELS,
  SEVERITY_LABELS,
  SeverityBadge,
  groupByCategory,
  normCitationStateLabel,
  severityTone,
} from '@/entities/finding';
import type { SeverityTone } from '@/entities/finding';
import { severityTone as tileSeverityTone } from '@/widgets/portal-blocks';
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
import { THEMES, palette, parseRules, scopedPalettes, splitSelectorList } from '../styles/contrast';
import type { Theme, TokenName } from '../styles/contrast';

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

  it('gives each severity its own tone, so the list can be read at a glance', () => {
    // It said so for a while with two severities on one grey («Рекомендация» and «Проверить смежный раздел»): the table below
    // was written to match the code, and the count of distinct tones in it was never asked. Five severities are five tones.
    const tones: Record<Severity, string> = {
      critical: 'am-badge--failed',
      economic: 'am-badge--degraded',
      operational: 'am-badge--active',
      recommendation: 'am-badge--ok',
      check_adjacent: 'am-badge--inert',
    };
    for (const severity of SEVERITY_VALUES) {
      expect(render(createElement(SeverityBadge, { severity }))).toContain(`class="am-badge ${tones[severity]}"`);
    }
    const drawn = SEVERITY_VALUES.map((severity) => /class="am-badge (am-badge--\w+)"/.exec(render(createElement(SeverityBadge, { severity })))?.[1]);
    expect(new Set(drawn).size).toBe(SEVERITY_VALUES.length);
  });

  it('computes the tone in one place: the badge, the tile of a block and `severityTone` say the same', () => {
    expect(tileSeverityTone).toBe(severityTone);
    for (const severity of SEVERITY_VALUES) {
      expect(render(createElement(SeverityBadge, { severity }))).toContain(`class="am-badge am-badge--${severityTone(severity)}"`);
    }
    expect(severityTone(null)).toBe('inert');
  });

  it('shows a value outside the closed set as a fault, not as a blank and not as itself', () => {
    const markup = render(createElement(SeverityBadge, { severity: 'urgent' as Severity }));
    expect(markup).toContain('data-closed-vocabulary-fault="severity"');
    expect(markup).toContain('Неизвестная критичность');
    expect(markup).not.toContain('urgent');
  });

  it('puts a tooltip on a badge that is given one, in Russian', () => {
    const markup = render(
      createElement(SeverityBadge, { severity: 'critical', title: 'Критичность, предложенная моделью' }),
    );
    expect(markup).toContain('title="Критичность, предложенная моделью"');
  });
});

// ------------------------------------------------------------------ the five tones, told apart

const GLOBALS = fileURLToPath(new URL('../../../src/app/globals.css', import.meta.url));
const GLOBALS_CSS = readFileSync(GLOBALS, 'utf8');
const GLOBAL_RULES = parseRules(GLOBALS_CSS, 'globals.css');

/**
 * Two colours closer than this are not two colours: twice the OKLab distance of about 0.02 that is taken as the smallest visible
 * step (the same floor `section-palette.test.ts` holds the section colours to).
 */
const MIN_APART = 0.04;

/** A six-digit hex as OKLab (Ottosson's matrices), the space the distances are measured in. */
function oklab(hex: string): readonly [number, number, number] {
  const linear = (pair: string): number => {
    const channel = parseInt(pair, 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  };
  const r = linear(hex.slice(1, 3));
  const g = linear(hex.slice(3, 5));
  const b = linear(hex.slice(5, 7));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

function distance(a: string, b: string): number {
  const [al, aa, ab] = oklab(a);
  const [bl, ba, bb] = oklab(b);
  return Math.hypot(al - bl, aa - ba, ab - bb);
}

/** The ink token a tone's badge reads, from the declaration in `globals.css` (`.am-badge--<tone> { color: var(--am-…) }`). */
function inkTokenOf(tone: SeverityTone): TokenName {
  const rule = GLOBAL_RULES.find((one) => splitSelectorList(one.selector).includes(`.am-badge--${tone}`) && one.declarations.has('color'));
  const reference = /^var\((--am-[\w-]+)\)$/.exec((rule?.declarations.get('color') ?? '').trim());
  if (reference === null) throw new Error(`.am-badge--${tone} reads no colour token in globals.css`);
  return reference[1] as TokenName;
}

/**
 * The colour a tone's ink really has in a palette: inside the application frame (`.am-app__main`, where every screen is drawn)
 * the accent is the showcase accent, so «Эксплуатационное» is teal there and blue only outside it.
 */
function inkOf(tone: SeverityTone, theme: Theme, framed: boolean): string {
  const tokens = palette(GLOBALS_CSS, theme);
  let token = inkTokenOf(tone);
  if (framed) {
    const scope = scopedPalettes(GLOBAL_RULES).find((one) => one.selectors.includes('.am-app__main'));
    token = scope?.alias.get(token) ?? token;
  }
  const hex = tokens.get(token);
  if (hex === undefined || !/^#[0-9a-f]{6}$/i.test(hex)) throw new Error(`${token} is not a six-digit colour in the ${theme} palette`);
  return hex;
}

/** The two tones of a list that are the nearest to each other, and how far apart their inks are. */
function closestPair(tones: readonly SeverityTone[], theme: Theme, framed: boolean): { readonly pair: readonly [number, number]; readonly apart: number } {
  let best = { pair: [0, 1] as readonly [number, number], apart: Number.POSITIVE_INFINITY };
  tones.forEach((a, i) => {
    tones.forEach((b, j) => {
      if (j <= i) return;
      const apart = distance(inkOf(a, theme, framed), inkOf(b, theme, framed));
      if (apart < best.apart) best = { pair: [i, j], apart };
    });
  });
  return best;
}

describe('the five severities are told apart by colour, in both palettes', () => {
  const tones = SEVERITY_VALUES.map((severity) => severityTone(severity));

  it('puts every two of the five tones at least 0.04 apart in OKLab, inside the application frame and outside it', () => {
    for (const theme of THEMES) {
      for (const framed of [false, true]) {
        const { pair, apart } = closestPair(tones, theme, framed);
        const where = `${theme} palette ${framed ? 'inside' : 'outside'} the frame: ${SEVERITY_VALUES[pair[0]]} and ${SEVERITY_VALUES[pair[1]]}`;
        expect(apart, `${where} are ${apart.toFixed(3)} apart`).toBeGreaterThanOrEqual(MIN_APART);
      }
    }
  });

  it('would have caught the old table: two severities on one grey are 0 apart', () => {
    const old: readonly SeverityTone[] = ['failed', 'degraded', 'active', 'inert', 'inert'];
    for (const theme of THEMES) expect(closestPair(old, theme, true).apart).toBe(0);
  });

  it('reads the teal of «Эксплуатационное» from the frame’s accent, which is what makes it a colour apart from the green', () => {
    // Inside the frame the accent is the showcase accent; outside it is the blue. The two tones that sit next to each other
    // in hue (operational teal, recommendation green) are the nearest pair of the five, which is why they are measured.
    for (const theme of THEMES) {
      expect(inkOf('active', theme, true)).not.toBe(inkOf('active', theme, false));
      expect(distance(inkOf('active', theme, true), inkOf('ok', theme, true))).toBeGreaterThanOrEqual(MIN_APART);
    }
  });
});

// ------------------------------------------------------------------ the model's proposed severity

describe('a proposed severity is the same pill, apart from a decision', () => {
  const proposed = (severity: Severity): string => render(createElement(SeverityBadge, { severity, proposed: true }));

  for (const severity of SEVERITY_VALUES) {
    it(`draws «${severity}» as a proposal: its own attribute, never the decision's, the word and the tooltip`, () => {
      const markup = proposed(severity);
      expect(markup).toContain(`data-proposed-severity="${severity}"`);
      expect(markup).not.toContain('data-severity=');
      expect(markup).toContain('title="Предложение модели, не решение эксперта"');
      expect(markup).toContain(`>${SEVERITY_LABELS[severity]}<`);
      expect(markup).toContain('>предложено<');
      expect(rawSeverityWords(markup)).toEqual([]);
      expect(latinWords(markup)).toEqual([]);
    });

    it(`keeps the tone of «${severity}» and adds only the dashed edge`, () => {
      const decided = render(createElement(SeverityBadge, { severity }));
      const tone = /am-badge--\w+/.exec(decided)?.[0];
      expect(tone).toBeDefined();
      expect(proposed(severity)).toMatch(new RegExp(`class="am-badge ${tone} [^"]*proposed[^"]*"`));
      // The decision's pill has neither the word nor the dashed class.
      expect(decided).not.toContain('предложено');
      expect(decided).not.toMatch(/class="[^"]*proposed/);
    });
  }

  it('does not take a tooltip of its own: the one it has is the guard, and no screen can word a proposal as a decision', () => {
    const markup = render(createElement(SeverityBadge, { severity: 'critical', proposed: true }));
    expect(markup.match(/title="/g)).toHaveLength(1);
  });

  it('shows a value outside the closed set as a fault, proposed or not', () => {
    const markup = render(createElement(SeverityBadge, { severity: 'urgent' as Severity, proposed: true }));
    expect(markup).toContain('data-closed-vocabulary-fault="severity"');
    expect(markup).not.toContain('data-proposed-severity');
    expect(markup).not.toContain('urgent');
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
      ['', 'Выберите критичность'],
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
      expect(markup).toContain('title="Критичность, решённая экспертом"');
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
    expect(markup).toContain('title="Критичность, решённая экспертом"');
    expect(rawSeverityWords(markup)).toEqual([]);
    expect(latinWords(markup)).toEqual([]);
  });

  it('shows the decided severity and not the proposed one when the two differ', () => {
    const markup = list([
      cyrillicFinding(
        { current_verdict: 'accepted', decided_severity: 'recommendation' },
        { proposed_severity: 'critical' },
      ),
    ]);
    expect(markup).toContain('data-severity="recommendation"');
    expect(markup).not.toContain('data-severity="critical"');
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

describe('the citation states have Russian words, one per state', () => {
  it('labels exactly the contract’s closed set, each once, in Cyrillic with no Latin', () => {
    expect(Object.keys(NORM_CITATION_STATE_LABELS).sort()).toEqual([...NORM_CITATION_STATE_VALUES].sort());
    expect(new Set(Object.values(NORM_CITATION_STATE_LABELS)).size).toBe(NORM_CITATION_STATE_VALUES.length);
    for (const state of NORM_CITATION_STATE_VALUES) {
      expect(NORM_CITATION_STATE_LABELS[state]).toMatch(/^[А-Яа-яЁё ]+$/);
      expect(normCitationStateLabel(state)).toBe(NORM_CITATION_STATE_LABELS[state]);
    }
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
    expect(markup).toContain('подтверждена');
    expect(markup).toContain('am-badge--ok');
    expect(markup).toContain('Источник текста: КонсультантПлюс');
    expect(markup).toContain(`href="/norms/document?id=${NORM_DOC}&amp;page=12"`);
    expect(latinWords(markup)).toEqual([]);
  });

  it('says a rebound citation is rebound, and a citation with no clause number has no clause', () => {
    const markup = viewer(
      cyrillic({ norm_citations: [citation({ state: 'rebound', clause_number: null })] }),
    );
    expect(markup).toContain('data-norm-citation-state="rebound"');
    expect(markup).toContain('перепривязана');
    // A rebound citation is a confirmed one, told apart from a verified one by tone alone.
    expect(markup).toContain('am-badge--active');
    expect(markup).not.toContain('am-badge--ok');
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
    const markup = viewer(canonical, [plain]);
    expect(markup).not.toContain('data-proposed-severity');
    expect(markup).not.toContain('Предложение модели');
    expect(markup).not.toContain('Неизвестная критичность');
  });

  it('shows no merged block at all when there is nothing merged, even beside other fields', () => {
    const markup = viewer(cyrillic({ required_value: 'не менее 0,8 м' }), []);
    expect(markup).toContain('data-finding-values');
    expect(markup).not.toContain('data-merged-observations');
    expect(markup).not.toContain('Объединённые наблюдения');
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
