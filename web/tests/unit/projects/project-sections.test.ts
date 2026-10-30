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
 * The registry itself still carries no counts. `getDashboardSummary` now counts published
 * documents per section, server-side — `D-56`'s second half is answered, but by a
 * different read (`widgets/dashboard`'s sections panel), not by this registry. A count
 * invented here, from a list this module does not read, would be a number this module
 * never asked the server for.
 */

import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  ANALYSED_SECTION_CODE,
  PROJECT_SECTIONS,
  findProjectSection,
  projectSectionTitle,
} from '@/entities/project';

import { REPO_ROOT, readJson } from '../../guards/lib/repo';

/**
 * The legacy set, as `docs/program/DEBT_REGISTER.md` `D-56` records it, in its order.
 * Restated here rather than imported so that a change to the registry has to be a change
 * against legacy's list, made deliberately, and not a typo nobody notices.
 */
const LEGACY_CODES = [
  'AR', 'AI', 'KM', 'KJ', 'OV', 'EOM', 'VK', 'PT', 'PB', 'SS', 'ITP', 'GP', 'TX', 'POS',
] as const;

/**
 * `W59-SECTION-SEAL-01`: the current set is legacy's fourteen, in legacy's order, then `PS`
 * (the explanatory note), which the contract's `ProjectSection` gained. `PS` is not `PB`.
 */
const CURRENT_CODES = [...LEGACY_CODES, 'PS'] as const;

describe('the section set is legacy’s fourteen plus PS', () => {
  it('carries the legacy fourteen in legacy order, then PS', () => {
    expect(LEGACY_CODES).toHaveLength(14);
    expect(PROJECT_SECTIONS.map((section) => section.code)).toEqual([...CURRENT_CODES]);
    expect(findProjectSection('PS')?.abbr).toBe('ПЗ');
    expect(findProjectSection('PB')?.abbr).toBe('ПБ');
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

/**
 * `WEB-SECTION-COPY-01`. Until this lane the registry said that exactly one section, АР, was
 * «analysed». That described the original АР-only text prompt; after `W59-SECTION-SEAL-01` and
 * all fifteen sections, including АР, have a text profile. The registry records
 * the route of every section, and the fifteen are held to the packages the server loads, so
 * that a package added or removed without the catalogue changing fails here and not on a screen.
 */
const PROFILES_DIRECTORY = join(REPO_ROOT, 'src', 'auditmanager', 'analysis', 'text', 'profiles');

interface ProfilePackage {
  readonly section_code: string;
}

/** The `section_code` of every text-profile package the server loads, sorted. */
function packagedSectionCodes(): string[] {
  return readdirSync(PROFILES_DIRECTORY, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith('_'))
    .map((entry) => readJson<ProfilePackage>(join(PROFILES_DIRECTORY, entry.name, 'profile.json')).section_code)
    .sort();
}

function codesAnalysedBy(route: 'text_profile'): string[] {
  return PROJECT_SECTIONS.filter((section) => section.analysedBy === route).map((s) => s.code);
}

describe('every section is analysed by its own text profile', () => {
  it('routes all fifteen sections, including АР, to their text profile', () => {
    expect(codesAnalysedBy('text_profile')).toHaveLength(15);
    expect(codesAnalysedBy('text_profile')).toContain('AR');
    expect(codesAnalysedBy('text_profile').length).toBe(PROJECT_SECTIONS.length);
  });

  it('holds the text-profile sections to the packages the server loads, in both directions', () => {
    const packaged = packagedSectionCodes();
    expect(codesAnalysedBy('text_profile').sort()).toEqual(packaged);
    expect(packaged).toContain('AR');
  });

  it('keeps the section pickers’ default a real section', () => {
    expect(ANALYSED_SECTION_CODE).toBe('AR');
    expect(findProjectSection(ANALYSED_SECTION_CODE))
      .toMatchObject({ code: 'AR', analysedBy: 'text_profile' });
  });
});
