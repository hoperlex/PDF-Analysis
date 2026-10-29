/**
 * `CMP-DEBT-261` (`D-261`): the five screens that pick a version or a set show the mark of a
 * version admitted for comparison only (`upload_kind` `comparison_pdf`, `Q-CMP-5`), the mark
 * `CMP-VERSION-MARK-01` introduced, and where the screen starts work over the chosen version or
 * set they do not offer such a version as a choice that would start it.
 *
 * | screen                                  | comparison-only version                                   |
 * | --------------------------------------- | --------------------------------------------------------- |
 * | `widgets/version-comparison`            | stays chosen and comparable; marked in its option and pair |
 * | `_pages/stage-comparison`               | marked, with what the version is for                       |
 * | `widgets/specification-prices` chooser  | listed, marked, a disabled option; never default, no read  |
 * | `widgets/optimisation-proposals` chooser| the same, and «Запустить проход» is never offered for it   |
 * | `_pages/blocks` document picker         | marked; «Показать блоки» disabled with the reason          |
 *
 * Rendered, not read from source (`D-53`): each state is rendered through the harness with the
 * field seeded as `comparison_pdf`, as `portal_bundle`, absent, and as a value this client does
 * not know. Only `comparison_pdf` changes anything, and a screen without it is byte for byte what
 * it was (the absent, the `portal_bundle` and the unknown-value markup are compared).
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { DocumentVersion, VersionClassification, VersionUploadKind } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import {
  COMPARISON_ONLY_DETAIL,
  COMPARISON_ONLY_MARK,
  COMPARISON_ONLY_START_NOTE,
  DOCUMENT_PAGE_LIMIT,
  VERSION_PAGE_LIMIT,
} from '@/entities/document-version';
import { SPECIFICATION_ROW_LIMIT } from '@/entities/specification-price';
import { StageComparisonPage } from '@/_pages/stage-comparison';
import { DocumentChooser } from '@/_pages/blocks';
import { VersionComparison } from '@/widgets/version-comparison';
import { OptimisationProposals, ProposalSetChooser } from '@/widgets/optimisation-proposals';
import { SpecificationPricesChooser, SpecificationPricesSection } from '@/widgets/specification-prices';

import { newClient, renderScreen } from '../screens/harness';

const ULID = '01M2545JSD15ETSNNV904X991J';
const PROJECT = `prj_${ULID}`;
const USER = `usr_${ULID}`;
const SHA = 'a'.repeat(64);

const MARK_TEXT = 'Загружено без пакета портала — только для сравнения';
/** The badge of the shared mark component; the option text says the same words without it. */
const BADGE = 'data-comparison-only-mark=""';

/** A kind this client has never been told about: it must read as an ordinary version. */
const FUTURE_KIND = 'portal_bundle_v2' as unknown as VersionUploadKind;

const countOf = (markup: string, needle: string): number => markup.split(needle).length - 1;

/** The identities of the sets all start like this, so a key naming any set contains it. */
const DOCUMENT_PREFIX = `doc_${ULID.slice(0, -1)}`;

const uid = (prefix: string, tail: string): string => `${prefix}_${ULID.slice(0, -1)}${tail}`;

function classification(versionUid: string, section = 'AR'): VersionClassification {
  return {
    version_uid: versionUid,
    project_stage: 'P',
    section_code: section as VersionClassification['section_code'],
    confirmed_by_user_uid: USER,
    confirmed_at: '2026-10-20T08:00:00Z',
    revision: 1,
  };
}

/** One version of one set: the tail letter makes both identities distinct. */
function version(tail: string, over: Partial<DocumentVersion> = {}): DocumentVersion {
  const versionUid = uid('ver', tail);
  return {
    version_uid: versionUid,
    document_uid: uid('doc', tail),
    project_uid: PROJECT,
    version_ordinal: 1,
    media_type: 'application/pdf',
    byte_size: 1,
    sha256: SHA,
    page_count: 3,
    published_at: '2026-10-20T08:00:00Z',
    input_manifest: [],
    display_title: `Комплект ${tail}`,
    classification: classification(versionUid),
    ...over,
  };
}

const flagged = (tail: string, over: Partial<DocumentVersion> = {}): DocumentVersion =>
  version(tail, { upload_kind: 'comparison_pdf', ...over });

/** The three ways a version is NOT comparison-only: what the screens must draw as before. */
const NOT_COMPARISON_ONLY: readonly (readonly [string, Partial<DocumentVersion>])[] = [
  ['portal_bundle', { upload_kind: 'portal_bundle' }],
  ['no field', {}],
  ['an unknown future value', { upload_kind: FUTURE_KIND }],
];

/* ------------------------------------------------------------- version comparison */

describe('the version picker of the version comparison', () => {
  const CURRENT_TAIL = 'A';
  const SET_DOCUMENT = uid('doc', CURRENT_TAIL);

  /** One set of three versions; the version of the address is the first. */
  function setOf(second: Partial<DocumentVersion>, first: Partial<DocumentVersion> = {}) {
    const doc = { document_uid: SET_DOCUMENT };
    const v1 = version(CURRENT_TAIL, { ...doc, version_ordinal: 1, ...first });
    const v2 = version('B', { ...doc, version_ordinal: 2, ...second });
    const v3 = version('C', { ...doc, version_ordinal: 3 });
    return { v1, v2, v3 };
  }

  function render(items: readonly DocumentVersion[], current: DocumentVersion): string {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(current.version_uid), current);
    client.setQueryData(queryKeys.versions.list(SET_DOCUMENT, undefined, VERSION_PAGE_LIMIT), {
      items,
      page: { next_cursor: null },
    });
    return renderScreen(
      client,
      createElement(VersionComparison, { projectUid: PROJECT, versionUid: current.version_uid }),
    );
  }

  const optionOf = (markup: string, versionUid: string): string => {
    const start = markup.indexOf(`<option value="${versionUid}"`);
    expect(start, `no option for ${versionUid}`).toBeGreaterThan(-1);
    return markup.slice(start, markup.indexOf('</option>', start));
  };

  it('says the mark in the option of a comparison-only version and in no other option', () => {
    const { v1, v2, v3 } = setOf({ upload_kind: 'comparison_pdf' });
    const markup = render([v1, v2, v3], v1);
    expect(optionOf(markup, v2.version_uid)).toContain(`Версия 2 (${MARK_TEXT})`);
    expect(optionOf(markup, v3.version_uid)).not.toContain(MARK_TEXT);
    expect(optionOf(markup, v3.version_uid)).toContain('Версия 3');
  });

  it('keeps the comparison-only version chosen and comparable: no option is disabled', () => {
    const { v1, v2, v3 } = setOf({ upload_kind: 'comparison_pdf' });
    const markup = render([v1, v2, v3], v1);
    // The nearest newer version is the default when no older one exists: the comparison-only one.
    expect(markup).toMatch(new RegExp(`<option value="${v2.version_uid}"[^>]*selected`));
    expect(markup).not.toContain('disabled');
  });

  it('draws the mark badge beside the compared version, and not beside the other one', () => {
    const { v1, v2, v3 } = setOf({ upload_kind: 'comparison_pdf' });
    const markup = render([v1, v2, v3], v1);
    expect(countOf(markup, BADGE)).toBe(1);
    const pair = markup.slice(markup.indexOf('<p class="'), markup.indexOf('</p>'));
    expect(pair).toContain('Версия 1');
    expect(pair).toContain('Версия 2');
    // The badge stands after the target's name and its classification, not before the arrow.
    expect(pair.indexOf(BADGE)).toBeGreaterThan(pair.indexOf('Версия 2'));
  });

  it('marks the version of the address when it is the comparison-only one', () => {
    const { v1, v2, v3 } = setOf({}, { upload_kind: 'comparison_pdf' });
    const markup = render([v1, v2, v3], v1);
    expect(countOf(markup, BADGE)).toBe(1);
    const pair = markup.slice(markup.indexOf('<p class="'), markup.indexOf('</p>'));
    expect(pair.indexOf(BADGE)).toBeGreaterThan(pair.indexOf('Версия 1'));
    expect(pair.indexOf(BADGE)).toBeLessThan(pair.indexOf('→'));
  });

  for (const [name, over] of NOT_COMPARISON_ONLY) {
    it(`draws a set without comparison-only versions as before: ${name}`, () => {
      const { v1, v2, v3 } = setOf(over, over);
      const markup = render([v1, v2, v3], v1);
      expect(markup).not.toContain(MARK_TEXT);
      expect(markup).not.toContain(BADGE);
    });
  }

  it('draws the three not-comparison-only kinds byte for byte alike', () => {
    const drawn = NOT_COMPARISON_ONLY.map(([, over]) => {
      const { v1, v2, v3 } = setOf(over, over);
      return render([v1, v2, v3], v1);
    });
    expect(drawn[1]).toBe(drawn[0]);
    expect(drawn[2]).toBe(drawn[0]);
  });
});

/* ------------------------------------------------------------- stage comparison page */

describe('the stage comparison page', () => {
  const current = (over: Partial<DocumentVersion>): DocumentVersion => version('A', over);

  function page(seed: DocumentVersion | null): string {
    const client = newClient();
    if (seed !== null) client.setQueryData(queryKeys.versions.detail(seed.version_uid), seed);
    return renderScreen(
      client,
      createElement(StageComparisonPage, { projectUid: PROJECT, versionUid: uid('ver', 'A') }),
    );
  }

  it('marks a comparison-only version and says what it is for, above the comparison', () => {
    const markup = page(current({ upload_kind: 'comparison_pdf' }));
    expect(markup).toContain('data-comparison-only-version=""');
    expect(countOf(markup, BADGE)).toBe(1);
    expect(markup).toContain(MARK_TEXT);
    expect(markup).toContain(COMPARISON_ONLY_DETAIL);
    expect(markup.indexOf('data-comparison-only-version')).toBeLessThan(markup.indexOf('Сравнение прогонов'));
  });

  for (const [name, over] of NOT_COMPARISON_ONLY) {
    it(`draws no note for ${name}`, () => {
      const markup = page(current(over));
      expect(markup).not.toContain('data-comparison-only-version');
      expect(markup).not.toContain(BADGE);
      expect(markup).not.toContain(COMPARISON_ONLY_DETAIL);
    });
  }

  it('draws a portal version and a version without the field byte for byte alike', () => {
    expect(page(current({ upload_kind: 'portal_bundle' }))).toBe(page(current({})));
    expect(page(current({ upload_kind: FUTURE_KIND }))).toBe(page(current({})));
  });

  it('draws nothing of the kind while the version has not been read', () => {
    const markup = page(null);
    expect(markup).not.toContain('data-comparison-only-version');
    expect(markup).not.toContain(BADGE);
  });
});

/* ------------------------------------------------------------- the two set choosers */

interface ChooserCase {
  readonly name: string;
  readonly attribute: string;
  readonly draw: (sets: readonly DocumentVersion[], selected: string | null) => string;
}

const CHOOSERS: readonly ChooserCase[] = [
  {
    name: 'specification-prices',
    attribute: 'data-spec-chooser',
    draw: (sets, selected) =>
      renderToStaticMarkup(
        createElement(SpecificationPricesChooser, {
          sets,
          selected: selected as never,
          onSelect: () => undefined,
          partial: false,
        }),
      ),
  },
  {
    name: 'optimisation-proposals',
    attribute: 'data-proposal-set-chooser',
    draw: (sets, selected) =>
      renderToStaticMarkup(
        createElement(ProposalSetChooser, {
          sets,
          selected: selected as never,
          onSelect: () => undefined,
          partial: false,
        }),
      ),
  },
];

for (const chooser of CHOOSERS) {
  describe(`the set chooser of ${chooser.name}`, () => {
    const PORTAL = version('P', { display_title: 'Комплект портала' });
    const FLAGGED = flagged('Q', { display_title: 'Только для сравнения' });
    const optionOf = (markup: string, set: DocumentVersion): string => {
      const start = markup.indexOf(`<option value="${set.document_uid}"`);
      expect(start, `no option for ${set.document_uid}`).toBeGreaterThan(-1);
      return markup.slice(start, markup.indexOf('</option>', start));
    };

    it('lists a comparison-only set as a disabled option that says the mark', () => {
      const markup = chooser.draw([PORTAL, FLAGGED], PORTAL.document_uid);
      expect(optionOf(markup, FLAGGED)).toContain('disabled=""');
      expect(optionOf(markup, FLAGGED)).toContain(`(${MARK_TEXT})`);
      expect(optionOf(markup, PORTAL)).not.toContain('disabled');
      expect(optionOf(markup, PORTAL)).not.toContain(MARK_TEXT);
      expect(markup).toContain(`${chooser.attribute}="2"`);
    });

    it('draws the shared mark badge for the comparison-only set, once, and the reason once', () => {
      const markup = chooser.draw([PORTAL, FLAGGED], PORTAL.document_uid);
      expect(countOf(markup, BADGE)).toBe(1);
      expect(markup).toContain('data-comparison-only-sets="1"');
      expect(countOf(markup, COMPARISON_ONLY_START_NOTE)).toBe(1);
      const list = markup.slice(markup.indexOf('<ul>'), markup.indexOf('</ul>'));
      expect(list).toContain('Только для сравнения');
      expect(list).not.toContain('Комплект портала');
    });

    it('points the select at the reason', () => {
      const markup = chooser.draw([PORTAL, FLAGGED], PORTAL.document_uid);
      const describedBy = /<select[^>]*aria-describedby="([^"]+)"/.exec(markup);
      expect(describedBy).not.toBeNull();
      expect(markup).toContain(`<p class="am-note" id="${describedBy![1]}">${COMPARISON_ONLY_START_NOTE}</p>`);
    });

    it('counts every set it lists, comparison-only ones included', () => {
      const another = flagged('R', { display_title: 'Ещё один' });
      const markup = chooser.draw([FLAGGED, PORTAL, another], PORTAL.document_uid);
      expect(markup).toContain(`${chooser.attribute}="3"`);
      expect(markup).toContain('data-comparison-only-sets="2"');
      expect(countOf(markup, BADGE)).toBe(2);
      expect(countOf(markup, COMPARISON_ONLY_START_NOTE)).toBe(1);
    });

    it('is a chooser with every option disabled when every set is comparison-only', () => {
      const markup = chooser.draw([FLAGGED], null);
      expect(markup).toContain(`${chooser.attribute}="1"`);
      expect(optionOf(markup, FLAGGED)).toContain('disabled=""');
      expect(markup).not.toContain('selected');
      expect(countOf(markup, COMPARISON_ONLY_START_NOTE)).toBe(1);
    });

    for (const [name, over] of NOT_COMPARISON_ONLY) {
      it(`draws a chooser of ordinary sets as before: ${name}`, () => {
        const markup = chooser.draw([version('P', over), version('S', over)], uid('doc', 'P'));
        expect(markup).not.toContain(MARK_TEXT);
        expect(markup).not.toContain('disabled');
        expect(markup).not.toContain('aria-describedby');
        expect(markup).not.toContain('data-comparison-only-sets');
        expect(markup).not.toContain(COMPARISON_ONLY_START_NOTE);
      });
    }

    it('draws the three not-comparison-only kinds byte for byte alike', () => {
      const drawn = NOT_COMPARISON_ONLY.map(([, over]) =>
        chooser.draw([version('P', over), version('S', over)], uid('doc', 'P')),
      );
      expect(drawn[1]).toBe(drawn[0]);
      expect(drawn[2]).toBe(drawn[0]);
    });
  });
}

describe('the set chosen by specification-prices', () => {
  const FLAGGED = flagged('Q');
  const PORTAL = version('P');

  function section(items: readonly DocumentVersion[]) {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT, undefined, DOCUMENT_PAGE_LIMIT), {
      items,
      page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(SpecificationPricesSection, { projectUid: PROJECT }));
    return { markup, asked: askedKeys(client) };
  }

  it('never defaults to a comparison-only set listed first, and asks for the next one', () => {
    const { markup, asked } = section([FLAGGED, PORTAL]);
    expect(markup).toMatch(new RegExp(`<option value="${PORTAL.document_uid}"[^>]*selected`));
    expect(markup).not.toMatch(new RegExp(`<option value="${FLAGGED.document_uid}"[^>]*selected`));
    expect(markup).toContain('Загрузка: спецификации и цен…');
    expect(asked.some((key) => key.includes(PORTAL.document_uid))).toBe(true);
    expect(asked.some((key) => key.includes(FLAGGED.document_uid))).toBe(false);
  });

  it('asks the server nothing when every set is comparison-only, and says why', () => {
    const { markup, asked } = section([FLAGGED, flagged('R')]);
    expect(markup).not.toContain('Загрузка: спецификации и цен…');
    expect(markup).not.toContain('data-spec-state');
    expect(asked.some((key) => key.includes('specification-prices') && key.includes(DOCUMENT_PREFIX))).toBe(false);
    expect(countOf(markup, COMPARISON_ONLY_START_NOTE)).toBe(1);
    expect(countOf(markup, BADGE)).toBe(2);
  });

  it('keeps «Обновить» disabled while nothing is chosen', () => {
    const { markup } = section([FLAGGED]);
    expect(markup).toContain('disabled=""');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Обновить<\/button>/);
  });
});

/** The keys of every query the render built, as strings: what the screen asked the server for. */
function askedKeys(client: ReturnType<typeof newClient>): string[] {
  return client
    .getQueryCache()
    .getAll()
    .map((query) => JSON.stringify(query.queryKey));
}

describe('the set chosen by optimisation-proposals', () => {
  const FLAGGED = flagged('Q');
  const PORTAL = version('P');
  const START_ENABLED = '<button type="button" class="am-button">Запустить проход</button>';
  const START_DISABLED = '<button type="button" class="am-button" disabled="">Запустить проход</button>';

  function section(items: readonly DocumentVersion[], roles: ('expert' | 'admin')[] = ['expert']) {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT, undefined, 50), {
      items,
      page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(OptimisationProposals, { projectUid: PROJECT, roles }));
    return { markup, asked: askedKeys(client) };
  }

  it('never defaults to a comparison-only set listed first: the pass start is for the next one', () => {
    const { markup, asked } = section([FLAGGED, PORTAL]);
    expect(markup).toMatch(new RegExp(`<option value="${PORTAL.document_uid}"[^>]*selected`));
    expect(markup).toContain(START_ENABLED);
    expect(asked.some((key) => key.includes(PORTAL.document_uid))).toBe(true);
    expect(asked.some((key) => key.includes(FLAGGED.document_uid))).toBe(false);
  });

  it('offers «Запустить проход» for no set when every set is comparison-only, and asks for no pass', () => {
    const { markup, asked } = section([FLAGGED, flagged('R')]);
    expect(markup).toContain(START_DISABLED);
    expect(markup).not.toContain(START_ENABLED);
    expect(asked.some((key) => key.includes(DOCUMENT_PREFIX) && key.includes('passes'))).toBe(false);
    expect(countOf(markup, COMPARISON_ONLY_START_NOTE)).toBe(1);
    expect(countOf(markup, BADGE)).toBe(2);
  });

  it('shows the reader who cannot start only the sentence it showed, over the same chooser', () => {
    const { markup } = section([FLAGGED, PORTAL], ['admin']);
    expect(markup).toContain('data-start-pass="readonly"');
    expect(markup).not.toContain(START_ENABLED);
    expect(countOf(markup, BADGE)).toBe(1);
  });
});

/* ------------------------------------------------------------- the blocks document picker */

describe('the document picker of the blocks page', () => {
  const PORTAL = version('P', { display_title: 'Комплект портала' });
  const FLAGGED = flagged('Q', { display_title: 'Только для сравнения' });
  const SHOW = '<button type="button" class="am-button">Показать блоки</button>';

  function picker(items: readonly DocumentVersion[]): string {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT, undefined, DOCUMENT_PAGE_LIMIT), {
      items,
      page: { next_cursor: null },
    });
    return renderScreen(
      client,
      createElement(DocumentChooser, { projectUid: PROJECT, onChooseVersion: () => undefined }),
    );
  }

  /** The `<li>` of one document, found by the version identity it prints. */
  function rowOf(markup: string, set: DocumentVersion): string {
    const start = markup.indexOf(set.version_uid);
    expect(start, `no row for ${set.version_uid}`).toBeGreaterThan(-1);
    const from = markup.lastIndexOf('<li', start);
    return markup.slice(from, markup.indexOf('</li>', start));
  }

  it('marks the comparison-only document and draws its «Показать блоки» disabled', () => {
    const markup = picker([PORTAL, FLAGGED]);
    const row = rowOf(markup, FLAGGED);
    expect(row).toContain(BADGE);
    expect(row).toContain(MARK_TEXT);
    expect(row).toMatch(/<button type="button" class="am-button" disabled="" aria-describedby="[^"]+">Показать блоки<\/button>/);
  });

  it('leaves the portal document exactly as it was: the same button, no mark', () => {
    const markup = picker([PORTAL, FLAGGED]);
    const row = rowOf(markup, PORTAL);
    expect(row).toContain(SHOW);
    expect(row).not.toContain(BADGE);
    expect(row).not.toContain('disabled');
  });

  it('says the reason once and points the disabled button at it', () => {
    const markup = picker([PORTAL, FLAGGED, flagged('R')]);
    expect(countOf(markup, COMPARISON_ONLY_START_NOTE)).toBe(1);
    const id = /<p class="am-note" id="([^"]+)" data-comparison-only-note="">/.exec(markup);
    expect(id).not.toBeNull();
    expect(countOf(markup, `aria-describedby="${id![1]}"`)).toBe(2);
    expect(countOf(markup, BADGE)).toBe(2);
  });

  it('keeps the comparison-only document listed', () => {
    const markup = picker([FLAGGED]);
    expect(markup).toContain('Только для сравнения');
    expect(markup).toContain(FLAGGED.version_uid);
  });

  for (const [name, over] of NOT_COMPARISON_ONLY) {
    it(`draws the picker as before for ${name}: no mark, no note, every button enabled`, () => {
      const markup = picker([version('P', over), version('S', over)]);
      expect(markup).not.toContain(MARK_TEXT);
      expect(markup).not.toContain('data-comparison-only-note');
      expect(markup).not.toContain('aria-describedby');
      expect(markup).not.toContain('disabled');
      expect(countOf(markup, SHOW)).toBe(2);
    });
  }

  it('draws the three not-comparison-only kinds byte for byte alike', () => {
    const drawn = NOT_COMPARISON_ONLY.map(([, over]) => picker([version('P', over), version('S', over)]));
    expect(drawn[1]).toBe(drawn[0]);
    expect(drawn[2]).toBe(drawn[0]);
  });
});

/* ------------------------------------------------------------- the shared words */

describe('the words the five screens say', () => {
  it('are the entity sentences, in Russian and without a Latin letter (the file format PDF aside)', () => {
    expect(COMPARISON_ONLY_MARK).toBe(MARK_TEXT);
    for (const sentence of [COMPARISON_ONLY_MARK, COMPARISON_ONLY_DETAIL, COMPARISON_ONLY_START_NOTE]) {
      expect(/[A-Za-z]/.test(sentence.replaceAll('PDF', ''))).toBe(false);
      expect(sentence).toMatch(/[Ѐ-ӿ]/);
    }
  });

  it('keep the row limit the section reads under (the keys these tests seed)', () => {
    expect(SPECIFICATION_ROW_LIMIT).toBe(50);
    expect(DOCUMENT_PAGE_LIMIT).toBe(50);
  });
});
