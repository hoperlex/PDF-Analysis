/**
 * `UI-B-20`: the address of «Оптимизация разделов» — `?section=<code>&project=<project_uid>&tab=accepted`.
 *
 * Read, not guessed: a section code outside the fifteen, a project that is not shaped like an identity and a tab the
 * page does not have are set aside by name, and the page opens on its defaults. What is written back reopens the same
 * view.
 */

import { describe, expect, it } from 'vitest';

import {
  DEFAULT_SECTION_OPTIMISATION_ADDRESS,
  SECTION_OPTIMISATION_TABS,
  readSectionOptimisationAddress,
  sectionOptimisationSearch,
} from '@/_pages/section-optimisation';
import { PROJECT_STRUCTURE_ORDER } from '@/entities/project';

import { ACCEPTED_PROJECT_B } from './fixtures';

describe('reading the address', () => {
  it('opens on АР, every project, the specification, when the address names nothing', () => {
    expect(readSectionOptimisationAddress({})).toEqual(DEFAULT_SECTION_OPTIMISATION_ADDRESS);
    expect(DEFAULT_SECTION_OPTIMISATION_ADDRESS).toMatchObject({ tab: 'specification', sectionCode: 'AR', projectUid: null });
    expect(readSectionOptimisationAddress({ section: '', project: '', tab: '' }).ignored).toEqual([]);
  });

  it('reads the section, the project and the tab it names', () => {
    expect(readSectionOptimisationAddress({ section: 'KJ', project: ACCEPTED_PROJECT_B, tab: 'accepted' })).toEqual({
      tab: 'accepted',
      sectionCode: 'KJ',
      projectUid: ACCEPTED_PROJECT_B,
      ignored: [],
    });
  });

  it('reads each of the fifteen sections, and only them', () => {
    for (const code of PROJECT_STRUCTURE_ORDER) {
      expect(readSectionOptimisationAddress({ section: code })).toMatchObject({ sectionCode: code, ignored: [] });
    }
    expect(readSectionOptimisationAddress({ section: 'ar' }).ignored).toEqual(['section']);
  });

  it('sets aside what it cannot read, names it, and keeps the rest', () => {
    const read = readSectionOptimisationAddress({ section: 'ZZ', project: 'prj_nope', tab: 'history' });
    expect(read).toEqual({ ...DEFAULT_SECTION_OPTIMISATION_ADDRESS, ignored: ['section', 'project', 'tab'] });
    expect(readSectionOptimisationAddress({ section: 'ZZ', project: ACCEPTED_PROJECT_B })).toMatchObject({
      sectionCode: 'AR',
      projectUid: ACCEPTED_PROJECT_B,
      ignored: ['section'],
    });
  });
});

describe('writing the address', () => {
  it('always names the section, and the project and the tab only when they are not the default', () => {
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: null })).toBe('?section=AR');
    expect(sectionOptimisationSearch({ tab: 'accepted', sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B })).toBe(
      `?section=KJ&project=${ACCEPTED_PROJECT_B}&tab=accepted`,
    );
  });

  it('reopens the view it was written for', () => {
    for (const tab of SECTION_OPTIMISATION_TABS) {
      for (const projectUid of [null, ACCEPTED_PROJECT_B]) {
        const view = { tab, sectionCode: 'OV' as const, projectUid };
        const params = new URLSearchParams(sectionOptimisationSearch(view));
        const read = readSectionOptimisationAddress({
          section: params.get('section') ?? undefined,
          project: params.get('project') ?? undefined,
          tab: params.get('tab') ?? undefined,
        });
        expect(read).toEqual({ ...view, ignored: [] });
      }
    }
  });
});
