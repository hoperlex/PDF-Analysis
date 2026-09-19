/**
 * Criterion 6's arithmetic: the quotation as sent, the anchor as declared, and the pages
 * the observation actually cites.
 *
 * The `W12-WEB` sweep mutated every rule in `entities/finding-observation` and eleven of
 * them could not be told from a deleted rule. The existing evidence-viewer suite proves
 * byte-identity against trimming and whitespace collapse, but its fixtures never
 * distinguish:
 *
 *   - Unicode **normalization** from no transform at all — no fixture is in a decomposed
 *     form, so `quote.normalize('NFC')` was indistinguishable from `quote`;
 *   - a **code-point** count from a UTF-16 count — nothing reached
 *     `quotationCodePointLength`, so counting code units read the same;
 *   - `anchorMatchesQuotation` and `anchorLabel` from any constant — both are rendered by
 *     the viewer and neither was read by a test;
 *   - a **numeric** page sort from a lexicographic one — the only multi-page fixture is
 *     `[2, 7]`, which sorts the same either way;
 *   - `firstDeclaredPage`, `isDeclaredPage`, `evidenceOnPage`'s page filter and
 *     `orderedEvidence`'s page-then-ordinal key — all four survived being replaced.
 *
 * Every expected value here is a literal. Nothing is computed from the module under test,
 * and no input is derived from a constant this file asserts about. The two strings that
 * carry the point are written as `\u` escapes so that neither this file's encoding nor an
 * editor's normalization can quietly turn one into the other.
 */

import { describe, expect, it } from 'vitest';

import type { Evidence, FindingObservation } from '@/shared/api';
import {
  anchorLabel,
  anchorMatchesQuotation,
  declaredPages,
  evidenceOnPage,
  firstDeclaredPage,
  isDeclaredPage,
  observationProviderMode,
  orderedEvidence,
  quotationCodePointLength,
  quotationText,
} from '@/entities/finding-observation';
import { countGrouped, groupByCategory } from '@/entities/finding';

import { finding, observation, provenance } from './fixtures';

/**
 * An evidence item built here rather than by the shared builder.
 *
 * `fixtures.evidence()` recomputes `char_end` from the quotation's own code-point length,
 * which is exactly the property `anchorMatchesQuotation` exists to check: a test using it
 * could never produce a disagreeing anchor.
 */
function item(overrides: Partial<Evidence> & Pick<Evidence, 'quote'>): Evidence {
  return {
    evidence_ordinal: 1,
    page_number: 7,
    char_start: 1200,
    char_end: 1210,
    ...overrides,
  };
}

function observed(evidence: readonly Evidence[]): FindingObservation {
  return observation({ evidence: [...evidence] });
}

// ---------------------------------------------------------------------------------------
// The quotation is the API string: not normalized, and counted in code points
// ---------------------------------------------------------------------------------------

/** `cafe` + U+0301 COMBINING ACUTE ACCENT: five code points. */
const DECOMPOSED = 'cafe\u0301';
/** `caf` + U+00E9 LATIN SMALL LETTER E WITH ACUTE: four code points, NFC of the above. */
const PRECOMPOSED = 'caf\u00e9';

describe('the quotation is not normalized on the way to the screen', () => {
  it('leaves a decomposed sequence decomposed', () => {
    const text = quotationText(item({ quote: DECOMPOSED }));
    expect(text).toBe('cafe\u0301');
    expect(text).not.toBe('caf\u00e9');
    expect([...text]).toHaveLength(5);
  });

  it('leaves a precomposed sequence precomposed', () => {
    // The other direction, so a mutation to `normalize('NFD')` is caught as well.
    const text = quotationText(item({ quote: PRECOMPOSED }));
    expect(text).toBe('caf\u00e9');
    expect(text).not.toBe('cafe\u0301');
    expect([...text]).toHaveLength(4);
  });
});

describe('quotation length is counted the way the contract counts char_start and char_end', () => {
  it('counts an astral character once, not twice', () => {
    // U+1F5CE is one code point and two UTF-16 code units. `char_start`/`char_end` index
    // the prepared text layer in code points (`P02_SEAMS.md` §4), so a UTF-16 count is
    // wrong by one for every astral character.
    const quote = 'a\u{1F5CE}b';
    expect(quote.length).toBe(4);
    expect(quotationCodePointLength(item({ quote }))).toBe(3);
  });

  it('counts a combining mark as its own code point', () => {
    expect(quotationCodePointLength(item({ quote: DECOMPOSED }))).toBe(5);
    expect(quotationCodePointLength(item({ quote: PRECOMPOSED }))).toBe(4);
  });
});

// ---------------------------------------------------------------------------------------
// The anchor
// ---------------------------------------------------------------------------------------

describe('a stated anchor that disagrees with its quotation is reported, not asserted', () => {
  it('is true when the declared span equals the quotation length', () => {
    expect(
      anchorMatchesQuotation(item({ quote: 'thirty days', char_start: 1200, char_end: 1211 })),
    ).toBe(true);
  });

  it('is false when the declared span is one code point short', () => {
    expect(
      anchorMatchesQuotation(item({ quote: 'thirty days', char_start: 1200, char_end: 1210 })),
    ).toBe(false);
  });

  it('is false when the span was measured in UTF-16 code units', () => {
    // The exact disagreement an astral quotation produces if something upstream counted
    // code units: three code points, a declared span of four.
    expect(anchorMatchesQuotation(item({ quote: 'a\u{1F5CE}b', char_start: 0, char_end: 4 }))).toBe(
      false,
    );
    expect(anchorMatchesQuotation(item({ quote: 'a\u{1F5CE}b', char_start: 0, char_end: 3 }))).toBe(
      true,
    );
  });
});

describe('the anchor label states the page, the range, and which convention the range uses', () => {
  /**
   * `D-25`. The offsets are document-global (`Evidence` in the frozen contract), and the
   * defect was that the caption did not say so: beside the words "page 2", `chars 707-746`
   * reads as an offset into page 2. `W21-CERT` measured the real case — page 2 of that
   * document is 539 characters and the quotation sits at page-local 198-237 — so a reader
   * following the old caption looked 707 characters into a 539-character page.
   *
   * Every assertion below is written against that reader, not against the string: the
   * whole label, the convention clause, the page named twice, and the refusal to print a
   * page-local number anywhere.
   */
  const REAL_CASE = item({ quote: 'x', page_number: 2, char_start: 707, char_end: 746 });

  it('is exactly this string, for the case D-25 was found on', () => {
    // The full label, pinned. U+2013 EN DASH is an escape on purpose: a change to a hyphen
    // is a change to what the reviewer reads and should not pass unnoticed.
    expect(anchorLabel(REAL_CASE)).toBe(
      'page 2, characters 707–746 of the whole document, not of page 2',
    );
  });

  it('names the convention, so the reader needs nothing else to act on the number', () => {
    // The load-bearing clause. Without it the caption is D-25 again, whatever else it says.
    expect(anchorLabel(REAL_CASE)).toContain('of the whole document');
  });

  it('denies the page-local reading explicitly, naming the same page again', () => {
    // "not of page 2", not "not of the page": the page is named a second time so the
    // negation cannot be read as referring to some other page.
    expect(anchorLabel(REAL_CASE)).toContain('not of page 2');
    const other = item({ quote: 'x', page_number: 11, char_start: 5, char_end: 9 });
    expect(anchorLabel(other)).toContain('not of page 11');
    expect(anchorLabel(other)).not.toContain('not of page 2');
  });

  it('never prints the page-local offsets, which the browser cannot compute anyway', () => {
    // 198 and 237 are this quotation's page-local offsets. The browser holds neither the
    // prepared text layer nor the page's start in it, so a caption showing them could only
    // have guessed. Asserted because "convert it" is the obvious wrong repair.
    const label = anchorLabel(REAL_CASE);
    expect(label).not.toContain('198');
    expect(label).not.toContain('237');
  });

  it('uses the server page number unchanged', () => {
    const label = anchorLabel(item({ quote: 'x', page_number: 11, char_start: 0, char_end: 1 }));
    expect(label).toContain('page 11,');
    expect(label).not.toContain('page 12');
    expect(label).not.toContain('page 10');
  });

  it('carries both ends of the range, not only the start', () => {
    const label = anchorLabel(item({ quote: 'x', page_number: 3, char_start: 40, char_end: 95 }));
    expect(label).toContain('40');
    expect(label).toContain('95');
  });

  it('states the range in the order the server declares it, start before end', () => {
    const label = anchorLabel(item({ quote: 'x', page_number: 3, char_start: 40, char_end: 95 }));
    expect(label.indexOf('40')).toBeLessThan(label.indexOf('95'));
  });

  it('passes both offsets through unchanged, with no off-by-one adjustment', () => {
    // A well-meaning "+1 to make it 1-based" is exactly the class of edit this caption
    // must not acquire: the contract's offsets are what the grounding gate verified.
    expect(anchorLabel(item({ quote: 'x', page_number: 1, char_start: 0, char_end: 0 }))).toContain(
      'characters 0–0 ',
    );
  });
});

// ---------------------------------------------------------------------------------------
// The declared pages
// ---------------------------------------------------------------------------------------

/**
 * Pages chosen so a numeric sort and a lexicographic one give different answers:
 * `[2, 7, 10]` against `['10', '2', '7']`. The existing suite's `[2, 7]` cannot tell them
 * apart. The ordinals deliberately disagree with the page order.
 */
const PAGES_OUT_OF_ORDER: readonly Evidence[] = [
  { evidence_ordinal: 1, page_number: 10, quote: 'on page ten', char_start: 0, char_end: 11 },
  { evidence_ordinal: 2, page_number: 2, quote: 'on page two', char_start: 20, char_end: 31 },
  { evidence_ordinal: 3, page_number: 7, quote: 'on page seven', char_start: 40, char_end: 53 },
  { evidence_ordinal: 4, page_number: 7, quote: 'also page seven', char_start: 60, char_end: 75 },
];

describe('the declared pages are the pages the observation cites, ascending', () => {
  it('sorts numerically, not lexicographically', () => {
    expect(declaredPages(observed(PAGES_OUT_OF_ORDER))).toEqual([2, 7, 10]);
  });

  it('opens on the lowest declared page, not the last one', () => {
    expect(firstDeclaredPage(observed(PAGES_OUT_OF_ORDER))).toBe(2);
  });

  it('has no page to open when the observation cites none', () => {
    expect(firstDeclaredPage(observed([]))).toBeNull();
  });

  it('refuses a page the observation never cited', () => {
    // Not cosmetic: page 3 is a page of the same PDF that this finding did not quote.
    // Offering it invites a reviewer to decide against text the finding never cited.
    expect(isDeclaredPage(observed(PAGES_OUT_OF_ORDER), 3)).toBe(false);
    expect(isDeclaredPage(observed(PAGES_OUT_OF_ORDER), 1)).toBe(false);
    expect(isDeclaredPage(observed(PAGES_OUT_OF_ORDER), 11)).toBe(false);
  });

  it('accepts each page the observation did cite', () => {
    expect(isDeclaredPage(observed(PAGES_OUT_OF_ORDER), 2)).toBe(true);
    expect(isDeclaredPage(observed(PAGES_OUT_OF_ORDER), 7)).toBe(true);
    expect(isDeclaredPage(observed(PAGES_OUT_OF_ORDER), 10)).toBe(true);
  });
});

describe('the quotations of a page are that page and nothing else', () => {
  it('returns only the items whose page_number is the page asked for', () => {
    const onSeven = evidenceOnPage(observed(PAGES_OUT_OF_ORDER), 7);
    expect(onSeven.map((entry) => entry.page_number)).toEqual([7, 7]);
    expect(onSeven.map((entry) => entry.quote)).toEqual(['on page seven', 'also page seven']);
  });

  it('returns nothing for a page with no quotation on it', () => {
    expect(evidenceOnPage(observed(PAGES_OUT_OF_ORDER), 3)).toEqual([]);
  });

  it('orders one page by ascending evidence_ordinal', () => {
    const onSeven = evidenceOnPage(observed(PAGES_OUT_OF_ORDER), 7);
    expect(onSeven.map((entry) => entry.evidence_ordinal)).toEqual([3, 4]);
  });
});

describe('the whole evidence list is ordered by page, then by ordinal', () => {
  it('sorts by page first, so the screen order is the CSV row order', () => {
    const ordered = orderedEvidence(observed(PAGES_OUT_OF_ORDER));
    expect(ordered.map((entry) => entry.page_number)).toEqual([2, 7, 7, 10]);
    // Ordinal 1 sits on the last page: a sort on the ordinal alone would put it first.
    expect(ordered.map((entry) => entry.evidence_ordinal)).toEqual([2, 3, 4, 1]);
  });
});

describe('the provenance rendered beside the evidence is the observation own', () => {
  it('reports the observation recorded mode rather than a constant', () => {
    expect(
      observationProviderMode(observation({ provenance: provenance({ provider_mode: 'recorded' }) })),
    ).toBe('recorded');
    expect(
      observationProviderMode(observation({ provenance: provenance({ provider_mode: 'live' }) })),
    ).toBe('live');
  });
});

// ---------------------------------------------------------------------------------------
// The group total
// ---------------------------------------------------------------------------------------

describe('the finding-list header counts findings, not groups', () => {
  it('adds the findings across the groups', () => {
    const groups = groupByCategory([
      finding({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', category: 'internal_contradiction' }),
      finding({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', category: 'internal_contradiction' }),
      finding({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', category: 'explicit_placeholder' }),
    ]);
    expect(groups).toHaveLength(2);
    expect(countGrouped(groups)).toBe(3);
  });

  it('is zero for no groups at all', () => {
    expect(countGrouped([])).toBe(0);
  });
});
