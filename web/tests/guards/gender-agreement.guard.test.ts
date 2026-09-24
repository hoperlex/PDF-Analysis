/**
 * `D-95`: a Russian determiner and the noun it is substituted next to must agree in gender.
 *
 * ## The defect, and why every existing guard was blind to it by construction
 *
 * `shared/lib/listing-failure.ts` substituted `PARENT_GENITIVE.version = 'версии'` — a
 * **feminine** noun — into sentences written around the masculine `проекта` / `документа`,
 * so a reviewer on a well-formed but absent version read:
 *
 * > Такого версии не существует. · На сервере нет этого версии, поэтому перечислять здесь
 * > нечего.
 *
 * `rendered-language.guard.test.ts` fails on **Latin** words a contract did not put there.
 * This is Cyrillic throughout and merely wrong. **A guard built to catch untranslated text
 * is structurally blind to badly translated text**, and no amount of widening its word
 * list would have changed that: there is no Latin here to find.
 *
 * `W43-JUDGE-B` found it by driving a stand. The module predates wave 43 — `run-list.tsx`
 * has passed `parent: 'version'` since it was written — so the defect is older than the
 * screen that exposed it, and wave 43 is simply the first time anybody read it.
 *
 * ## Two halves, because the class has two halves
 *
 * **The mechanism.** A gendered word hard-coded next to a substitution is a bet that every
 * value the substitution can take has that gender. The first half of this file forbids the
 * bet: `web/src` is scanned for a genitive determiner immediately followed by `${…}` in a
 * template literal, and a hit is red. After the repair the determiner is substituted from
 * the same table as the noun, so agreement is carried by the data rather than assumed by
 * the sentence, and the pattern is simply absent.
 *
 * **The output.** A mechanism rule alone would pass a table that declares the wrong gender,
 * so the second half reads the SENTENCES — every one the renderer that walks every screen
 * produces, plus every one `classifyListingFailure` produces over its own closed union,
 * with the union read out of the module's source so a fourth parent is exercised the day it
 * is added — and checks each determiner against the noun beside it.
 *
 * ## What the morphological rule decides, and what it does not
 *
 * It decides ONE axis, and it is the axis this substitution mechanism gets wrong: after a
 * genitive determiner, a singular noun ending in **-и / -ы** is feminine and one ending in
 * **-а / -я** is masculine or neuter. Anything else is not classified and produces no
 * verdict — an unclassified noun is reported as unjudged rather than as passing, because a
 * checker that silently declines is a checker whose silence reads as coverage.
 *
 * The one class this rule is wrong about is the heteroclitic neuters in `-мя` (`время`,
 * `имя`, …), whose genitive ends `-ени`. They are listed below, and their absence **from
 * the position this rule reads** — immediately after one of its determiners — is ASSERTED,
 * so the exception is checked rather than assumed. `OPERATING_CONSTRAINTS.md` §12: a
 * caveat is not a control.
 */

import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';
import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { classifyListingFailure } from '@/shared/lib';

import { CONTRACT_PATH, REPO_ROOT, readJson, readText, repoRelative, walkFiles } from './lib/repo';
import { join } from 'node:path';
import { renderedScreens, visibleText } from './rendered-language.guard.test';

// ======================================================================= the lexicon

/**
 * Determiners whose GENDER is unambiguous whatever case they are in.
 *
 * Deliberately not "every Russian determiner". `эта`/`этот`/`это` are nominative and the
 * noun beside them is nominative too, where `-а`/`-я` is feminine rather than masculine —
 * the opposite of the genitive reading below — so including them would make the rule
 * decide the wrong way round. Every word here is one whose feminine form differs from its
 * masculine/neuter form in every case it has, so the gender reading holds without the
 * checker having to know which case it is looking at.
 */
const DETERMINERS: readonly { readonly word: string; readonly feminine: boolean }[] = [
  { word: 'такого', feminine: false },
  { word: 'такой', feminine: true },
  { word: 'этого', feminine: false },
  { word: 'этой', feminine: true },
  { word: 'того', feminine: false },
  { word: 'той', feminine: true },
  { word: 'одного', feminine: false },
  { word: 'одной', feminine: true },
  { word: 'каждого', feminine: false },
  { word: 'каждой', feminine: true },
  { word: 'никакого', feminine: false },
  { word: 'никакой', feminine: true },
  { word: 'самого', feminine: false },
  { word: 'самой', feminine: true },
];

/** The nouns whose genitive ends `-ени` and which this rule would read as feminine. */
const HETEROCLITIC = [
  'времени', 'имени', 'племени', 'семени', 'знамени', 'пламени',
  'бремени', 'стремени', 'темени', 'вымени', 'темени',
] as const;

type Reading = 'feminine' | 'masculine-or-neuter' | 'unclassified';

/** The gender a singular noun's ending states, on the one axis this rule decides. */
export function genderOf(noun: string): Reading {
  const word = noun.toLowerCase();
  if ((HETEROCLITIC as readonly string[]).includes(word)) return 'unclassified';
  if (/[иы]$/.test(word)) return 'feminine';
  if (/[ая]$/.test(word)) return 'masculine-or-neuter';
  return 'unclassified';
}

export interface Disagreement {
  readonly determiner: string;
  readonly noun: string;
  readonly phrase: string;
}

/** Every `<determiner> <noun>` pair in one string whose two halves disagree. */
export function disagreements(text: string): Disagreement[] {
  const out: Disagreement[] = [];
  for (const { word, feminine } of DETERMINERS) {
    const pattern = new RegExp(`(^|[^а-яёА-ЯЁ])(${word})\\s+([а-яё]+)`, 'gi');
    for (const match of text.matchAll(pattern)) {
      const determiner = match[2] as string;
      const noun = match[3] as string;
      const reading = genderOf(noun);
      if (reading === 'unclassified') continue;
      if ((reading === 'feminine') !== feminine) {
        out.push({ determiner, noun, phrase: `${determiner} ${noun}` });
      }
    }
  }
  return out;
}

describe('the rule can tell agreement from disagreement, and says which it cannot decide', () => {
  it('calls the defect a disagreement', () => {
    // `D-95`'s own two sentences, as a reviewer read them.
    expect(disagreements('Такого версии не существует.').map((d) => d.phrase)).toEqual([
      'Такого версии',
    ]);
    expect(
      disagreements('На сервере нет этого версии, поэтому перечислять здесь нечего.').map(
        (d) => d.phrase,
      ),
    ).toEqual(['этого версии']);
  });

  it('calls the repaired sentence agreement, and the other two nouns too', () => {
    expect(disagreements('Такой версии не существует.')).toEqual([]);
    expect(disagreements('Такого проекта не существует.')).toEqual([]);
    expect(disagreements('Такого документа не существует.')).toEqual([]);
    expect(disagreements('На сервере нет этой версии, поэтому перечислять здесь нечего.'))
      .toEqual([]);
  });

  it('declines rather than guesses, and the decline is visible', () => {
    // An ending this axis does not decide. It must produce NO verdict — neither a pass
    // nor a failure — and `unjudged` below is what makes the decline countable.
    expect(genderOf('загрузке')).toBe('unclassified');
    expect(genderOf('учётной')).toBe('unclassified');
    expect(genderOf('ничего')).toBe('unclassified');
    expect(disagreements('нужная этой загрузке')).toEqual([]);
    // And the known exception really is excluded rather than silently misread.
    expect(genderOf('времени')).toBe('unclassified');
    expect(genderOf('версии')).toBe('feminine');
    expect(genderOf('проекта')).toBe('masculine-or-neuter');
  });
});

// ============================================== the mechanism: no bet on a substitution

describe('D-95: no sentence hard-codes a gendered word next to a substituted noun', () => {
  const SOURCES = walkFiles(
    join(REPO_ROOT, 'web', 'src'),
    (path) => path.endsWith('.ts') || path.endsWith('.tsx'),
  ).filter((path) => !path.includes('/shared/api/generated/'));

  it('reads web/src at all', () => {
    expect(SOURCES.length, 'no source file was walked').toBeGreaterThan(50);
  });

  it('finds no determiner adjacent to a `${…}`, in any module', () => {
    const pattern = new RegExp(
      `(${DETERMINERS.map((d) => d.word).join('|')})\\s+\\$\\{`,
      'gi',
    );
    const hits: string[] = [];
    for (const file of SOURCES) {
      const source = readText(file);
      for (const match of source.matchAll(pattern)) {
        const at = source.slice(0, match.index ?? 0).split('\n').length;
        hits.push(`${repoRelative(file)}:${at}  ${(match[0] ?? '').replace(/\s+/g, ' ')}`);
      }
    }
    expect(
      hits.sort(),
      'a gendered Russian word is written immediately before a substitution, which bets ' +
        'that every value the substitution can take has that gender. `D-95` is what the bet ' +
        'costs: `PARENT_GENITIVE.version` is feminine and the sentence around it was written ' +
        'for masculine `проекта`, so a reviewer read «Такого версии не существует». Carry ' +
        'the determiner in the same table as the noun so agreement is data rather than an ' +
        'assumption.',
    ).toEqual([]);
  });

  it('would catch the defect it was written for', () => {
    // Anti-vacuity, and the shape `prepared-sections.guard.test.ts` uses: the scan is run
    // once against a deliberately broken input, so a pattern that stopped matching is red
    // here rather than merely quiet over the tree.
    const broken = 'const t = `Такого ${parent} не существует.`;';
    const pattern = new RegExp(`(${DETERMINERS.map((d) => d.word).join('|')})\\s+\\$\\{`, 'gi');
    expect([...broken.matchAll(pattern)].length).toBe(1);
  });
});

// ================================================== the output: the sentences themselves

/**
 * `ListingParent`'s members, read out of the module rather than written down here.
 *
 * A fourth parent is exercised the day it is added, which is the half `W30-LISTS` is
 * about. Reading the type is not the same query as reading the noun table — the defect was
 * a table whose values disagreed with the sentences, and this enumerates the CALLERS' side.
 */
function listingParents(): readonly string[] {
  const source = readText(join(REPO_ROOT, 'web', 'src', 'shared', 'lib', 'listing-failure.ts'));
  const declaration = /export type ListingParent =([^;]+);/.exec(source);
  if (declaration === null) {
    throw new Error(
      'ListingParent is no longer declared as a union in listing-failure.ts, so this guard ' +
        'cannot enumerate the parents it must exercise. Say what replaced it.',
    );
  }
  return [...(declaration[1] as string).matchAll(/'([a-z_]+)'/g)].map((m) => m[1] as string);
}

function contractErrorCodes(): readonly string[] {
  const openapi = readJson<{
    components: { schemas: Record<string, { enum?: readonly string[] }> };
  }>(CONTRACT_PATH);
  return openapi.components.schemas['ErrorCode']?.enum ?? [];
}

function envelope(code: ErrorCode): ApiError {
  const body: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'Сообщение об отказе.',
    correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
    retryable: false,
  };
  return new ApiError(404, body, '0f0e9d8c-7b6a-4948-b726-150413021100');
}

/** Every sentence the listing classifier can put on a screen, over its whole surface. */
function listingSentences(): readonly { readonly where: string; readonly text: string }[] {
  const out: { where: string; text: string }[] = [];
  const collections: Record<string, string> = {
    project: 'документы этого проекта',
    document: 'версии этого документа',
    version: 'прогоны этой версии',
  };
  for (const parent of listingParents()) {
    for (const code of contractErrorCodes()) {
      const failure = classifyListingFailure(envelope(code as ErrorCode), {
        collection: collections[parent] ?? 'список',
        parent: parent as 'project' | 'document' | 'version',
      });
      out.push({ where: `listing-failure ${parent} ${code} title`, text: failure.title });
      out.push({ where: `listing-failure ${parent} ${code} detail`, text: failure.detail });
    }
  }
  return out;
}

describe('D-95: every sentence a reviewer can read agrees with itself', () => {
  it('exercises the whole listing surface, derived from the module and the contract', () => {
    const parents = listingParents();
    expect(parents.length, 'no ListingParent was parsed').toBeGreaterThan(2);
    expect(parents).toContain('version');
    expect(contractErrorCodes().length, 'no ErrorCode was read from the contract')
      .toBeGreaterThan(15);
    expect(listingSentences().length).toBe(parents.length * contractErrorCodes().length * 2);
  });

  it('finds no disagreement in anything the listing classifier produces', () => {
    const offences = listingSentences()
      .flatMap(({ where, text }) =>
        disagreements(text).map((d) => `«${d.phrase}»  (${where})  ${text}`),
      )
      .sort();
    expect(
      offences,
      'this sentence puts a determiner of one gender next to a noun of another, so a ' +
        'reviewer reads Russian that is well-formed word by word and wrong as a sentence. ' +
        '`D-95`.',
    ).toEqual([]);
  });

  it('finds no disagreement on any rendered screen', () => {
    // The renderer that walks every screen already exists; it looked for the wrong thing.
    const offences = renderedScreens()
      .flatMap((screen) =>
        visibleText(screen.markup).flatMap((text) =>
          disagreements(text).map((d) => `«${d.phrase}»  (${screen.where})`),
        ),
      )
      .sort();
    expect([...new Set(offences)], 'a rendered screen disagrees with itself').toEqual([]);
  });

  it('judges enough text to be worth calling a check, and says what it declined', () => {
    // Anti-vacuity. A rule that classified nothing would satisfy both cases above by
    // finding no pairs at all, which is the failure mode every census in this repository
    // has had at least once.
    const all = [
      ...listingSentences().map((s) => s.text),
      ...renderedScreens().flatMap((screen) => visibleText(screen.markup)),
    ];
    let judged = 0;
    let unjudged = 0;
    const pattern = new RegExp(
      `(^|[^а-яёА-ЯЁ])(${DETERMINERS.map((d) => d.word).join('|')})\\s+([а-яё]+)`,
      'gi',
    );
    for (const text of all) {
      for (const match of text.matchAll(pattern)) {
        if (genderOf(match[3] as string) === 'unclassified') unjudged += 1;
        else judged += 1;
      }
    }
    expect(judged, 'the rule classified no determiner-noun pair at all').toBeGreaterThan(20);
    // The decline is reported rather than hidden: a rule that suddenly declined everything
    // would keep passing, and this is the line that stops it.
    expect(judged / (judged + unjudged), 'the rule now declines most of what it reads')
      .toBeGreaterThan(0.5);
    /*
     * And the known exception is checked rather than carried as a caveat.
     *
     * It is checked WHERE IT MATTERS — after one of these determiners — and not across the
     * whole corpus, because the first version of this line did the latter and went red on
     * `пара имени и пароля`, an ordinary genitive of `имя` in the sign-in screen's prose
     * that no determiner precedes and that this rule never looks at. A check that fails on
     * text it does not judge teaches the next reader to weaken it.
     */
    const adjacent = new RegExp(
      `(${DETERMINERS.map((d) => d.word).join('|')})\\s+(${HETEROCLITIC.join('|')})`,
      'gi',
    );
    expect(
      all.flatMap((text) => [...text.matchAll(adjacent)].map((m) => m[0] as string)),
      'a noun this rule cannot read now sits beside a determiner it does judge. Its ' +
        'genitive ends `-ени` and the rule would call it feminine. Teach the rule before ' +
        'trusting it here.',
    ).toEqual([]);
  });
});
