/**
 * The section registry, held to the set `D-56` recorded and to one property of language.
 *
 * Two different things are checked here and they are worth separating. The **set** is
 * legacy's and is not this application's to change: fourteen codes, in that order, spelled
 * the way the legacy builder spells them, because the code is the machine value an
 * instrument addresses and a renamed code is a silent break. The **labels** are this
 * application's own, and the property that matters about them is that a reviewer never
 * reads a Latin code: `R-18` puts the alpha in Russian, and `АР` is what a designer writes
 * on a title block while `AR` is what a Python dictionary is keyed by.
 *
 * The registry deliberately carries no counts. There is no section field in the contract
 * to count over — `D-56`'s second half — so nothing here can be totalled per section, and
 * a test that expected a total would be asking for a number the server never sent.
 */

import { describe, expect, it } from 'vitest';

import {
  ANALYSED_SECTION_CODE,
  PROJECT_SECTIONS,
  findProjectSection,
  projectSectionTitle,
} from '@/entities/project';

/**
 * The legacy set, as `docs/program/DEBT_REGISTER.md` `D-56` records it, in its order.
 * Restated here rather than imported so that a change to the registry has to be a change
 * against legacy's list, made deliberately, and not a typo nobody notices.
 */
const LEGACY_CODES = [
  'AR', 'AI', 'KM', 'KJ', 'OV', 'EOM', 'VK', 'PT', 'PB', 'SS', 'ITP', 'GP', 'TX', 'POS',
] as const;

describe('the section set is legacy’s, unchanged', () => {
  it('carries the fourteen codes in the order legacy carries them', () => {
    expect(PROJECT_SECTIONS.map((section) => section.code)).toEqual([...LEGACY_CODES]);
  });

  it('gives every code exactly one row', () => {
    expect(new Set(PROJECT_SECTIONS.map((s) => s.code)).size).toBe(PROJECT_SECTIONS.length);
  });

  it('answers for a code it has and refuses one it does not, rather than guessing', () => {
    expect(findProjectSection('KJ')?.abbr).toBe('КЖ');
    expect(findProjectSection('АР')).toBeNull();
    expect(findProjectSection('')).toBeNull();
    expect(findProjectSection('ar')).toBeNull();
  });
});

describe('nothing a reviewer reads is Latin', () => {
  const latin = /[A-Za-z]/;

  it('spells every mark and every name in Cyrillic', () => {
    for (const section of PROJECT_SECTIONS) {
      expect({ code: section.code, abbr: section.abbr, latin: latin.test(section.abbr) })
        .toEqual({ code: section.code, abbr: section.abbr, latin: false });
      expect({ code: section.code, name: section.name, latin: latin.test(section.name) })
        .toEqual({ code: section.code, name: section.name, latin: false });
    }
  });

  it('titles a section by its name and its mark, never by its machine code', () => {
    const architecture = findProjectSection('AR');
    expect(architecture).not.toBeNull();
    expect(projectSectionTitle(architecture!)).toBe('Архитектурные решения (АР)');
    for (const section of PROJECT_SECTIONS) {
      expect(latin.test(projectSectionTitle(section))).toBe(false);
    }
  });

  it('gives every section a name that says something', () => {
    for (const section of PROJECT_SECTIONS) {
      expect({ code: section.code, long: section.name.length > 8 })
        .toEqual({ code: section.code, long: true });
    }
  });
});

describe('exactly one section is the one the analysis is built for', () => {
  it('marks AR and nothing else', () => {
    expect(PROJECT_SECTIONS.filter((section) => section.analysed).map((s) => s.code))
      .toEqual([ANALYSED_SECTION_CODE]);
    expect(ANALYSED_SECTION_CODE).toBe('AR');
  });

  it('keeps the analysed code in the registry, so the screen’s default is a real section', () => {
    expect(findProjectSection(ANALYSED_SECTION_CODE)?.analysed).toBe(true);
  });
});
