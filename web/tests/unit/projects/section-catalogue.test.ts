/**
 * The section catalogue's names and the project structure's order are the owner's
 * (`W59-SECTION-UI-01`).
 *
 * Poll answer `S-3` fixed the names — the legacy ones, which the backend's suggestion
 * catalogue carries in `src/auditmanager/sections/suggestion_patterns.json` — and `S-5` the
 * order the project structure lists sections in. Both are read here against their source,
 * not restated: the JSON is the backend's file, and the order is asserted as a permutation of
 * the contract's fifteen codes in the sequence the ruling gives.
 */

import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { PROJECT_SECTION_VALUES } from '@/shared/api';
import {
  PROJECT_SECTIONS,
  PROJECT_STRUCTURE_ORDER,
  UnknownProjectSectionError,
  projectSectionOf,
  sectionsInStructureOrder,
  structureRank,
} from '@/entities/project';

import { REPO_ROOT, readJson } from '../../guards/lib/repo';

interface SuggestionCatalogue {
  readonly sections: readonly { readonly code: string; readonly name: string }[];
}

const CATALOGUE = readJson<SuggestionCatalogue>(
  join(REPO_ROOT, 'src', 'auditmanager', 'sections', 'suggestion_patterns.json'),
);

describe('the names are the S-3 names the backend carries', () => {
  it('reads fifteen sections from the backend catalogue', () => {
    expect(CATALOGUE.sections).toHaveLength(15);
  });

  it('names every section exactly as the backend catalogue does', () => {
    const backend = new Map(CATALOGUE.sections.map((s) => [s.code, s.name]));
    for (const section of PROJECT_SECTIONS) {
      expect({ code: section.code, name: section.name }).toEqual({
        code: section.code,
        name: backend.get(section.code),
      });
    }
  });

  it('includes PS, the explanatory note, as ПЗ — distinct from ПБ', () => {
    expect(projectSectionOf('PS')).toMatchObject({ abbr: 'ПЗ', name: 'Пояснительная записка' });
    expect(projectSectionOf('PB')).toMatchObject({ abbr: 'ПБ', name: 'Пожарная безопасность' });
  });
});

describe('the project structure follows S-5', () => {
  it('is АР, then АИ → ПЗ, ПОС, ТХ → КЖ, КМ → ОВ, ВК, ПТ → ЭОМ, СС, ИТП → ГП → ПБ', () => {
    expect(sectionsInStructureOrder().map((s) => s.abbr)).toEqual([
      'АР', 'АИ', 'ПЗ', 'ПОС', 'ТХ', 'КЖ', 'КМ', 'ОВ', 'ВК', 'ПТ', 'ЭОМ', 'СС', 'ИТП', 'ГП', 'ПБ',
    ]);
  });

  it('is a permutation of the contract’s fifteen codes, each once', () => {
    expect([...PROJECT_STRUCTURE_ORDER].sort()).toEqual([...PROJECT_SECTION_VALUES].sort());
    expect(new Set(PROJECT_STRUCTURE_ORDER).size).toBe(PROJECT_SECTION_VALUES.length);
  });

  it('ranks by that order', () => {
    expect(structureRank('AR')).toBe(0);
    expect(structureRank('PB')).toBe(14);
    expect(structureRank('PS')).toBeLessThan(structureRank('KJ'));
  });
});

describe('every contract code resolves, and nothing else is guessed', () => {
  it('resolves each of the contract’s fifteen to a catalogue row', () => {
    for (const code of PROJECT_SECTION_VALUES) {
      expect(projectSectionOf(code).code).toBe(code);
    }
  });

  it('throws on a code outside the catalogue instead of labelling it', () => {
    expect(() => projectSectionOf('ZZ' as never)).toThrow(UnknownProjectSectionError);
  });
});
