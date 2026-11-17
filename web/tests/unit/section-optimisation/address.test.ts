/**
 * `UI-B-20`, `UIP-S11-06`: the address of «Оптимизация раздела» —
 * `?section=<code>&project=<project_uid>&document=<document_uid>&tab=accepted`.
 *
 * Read, not guessed: a section code outside the fifteen, a project or a document that is not shaped like an identity and a tab the
 * page does not have are set aside by name, and the page opens on its defaults. What is written back reopens the same
 * view.
 */

import { describe, expect, it } from 'vitest';

import {
  DEFAULT_SECTION_OPTIMISATION_ADDRESS,
  SECTION_OPTIMISATION_TABS,
  readDocumentParam,
  readSectionOptimisationAddress,
  sectionOptimisationSearch,
} from '@/_pages/section-optimisation';
import { PROJECT_STRUCTURE_ORDER } from '@/entities/project';

import { ACCEPTED_DOCUMENT, ACCEPTED_PROJECT_B } from './fixtures';

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

describe('the document of the scope (`UIP-S11-06`)', () => {
  it('reads `?document=` when it is shaped like a document identity, and names no document otherwise', () => {
    const read = readSectionOptimisationAddress({ section: 'KJ', project: ACCEPTED_PROJECT_B, document: ACCEPTED_DOCUMENT });
    expect(read).toEqual({ tab: 'specification', sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B, documentUid: ACCEPTED_DOCUMENT, ignored: [] });
    // An address that says nothing of it reads exactly as it always did: no key, not even an empty one.
    expect(readSectionOptimisationAddress({ section: 'KJ' })).not.toHaveProperty('documentUid');
    expect(readSectionOptimisationAddress({ document: '' })).toEqual(DEFAULT_SECTION_OPTIMISATION_ADDRESS);
    expect(readSectionOptimisationAddress({})).toEqual(DEFAULT_SECTION_OPTIMISATION_ADDRESS);
  });

  it('sets aside a value that is not a document identity, by name, and keeps the rest', () => {
    const read = readSectionOptimisationAddress({ section: 'KJ', project: ACCEPTED_PROJECT_B, document: 'doc_nope' });
    expect(read).toEqual({ tab: 'specification', sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B, ignored: ['document'] });
    // A project uid is not a document's, whatever else it looks like.
    expect(readSectionOptimisationAddress({ document: ACCEPTED_PROJECT_B }).ignored).toEqual(['document']);
  });

  it('reads the parameter by itself, for the live address (`readDocumentParam`)', () => {
    expect(readDocumentParam(ACCEPTED_DOCUMENT)).toEqual({ documentUid: ACCEPTED_DOCUMENT, ignored: false });
    expect(readDocumentParam(null)).toEqual({ documentUid: null, ignored: false });
    expect(readDocumentParam(undefined)).toEqual({ documentUid: null, ignored: false });
    expect(readDocumentParam('')).toEqual({ documentUid: null, ignored: false });
    expect(readDocumentParam('x')).toEqual({ documentUid: null, ignored: true });
  });

  it('writes it after the object and before the tab, and only when one is chosen', () => {
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: null, documentUid: null })).toBe('?section=AR');
    expect(sectionOptimisationSearch({ tab: 'accepted', sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B, documentUid: ACCEPTED_DOCUMENT })).toBe(
      `?section=KJ&project=${ACCEPTED_PROJECT_B}&document=${ACCEPTED_DOCUMENT}&tab=accepted`,
    );
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: null, allProjects: true, documentUid: ACCEPTED_DOCUMENT })).toBe(
      `?section=AR&project=all&document=${ACCEPTED_DOCUMENT}`,
    );
  });

  it('reopens the view it was written for, the document included', () => {
    for (const tab of SECTION_OPTIMISATION_TABS) {
      for (const documentUid of [null, ACCEPTED_DOCUMENT]) {
        const view = { tab, sectionCode: 'OV' as const, projectUid: ACCEPTED_PROJECT_B, documentUid };
        const params = new URLSearchParams(sectionOptimisationSearch(view));
        const read = readSectionOptimisationAddress({
          section: params.get('section') ?? undefined,
          project: params.get('project') ?? undefined,
          document: params.get('document') ?? undefined,
          tab: params.get('tab') ?? undefined,
        });
        expect(read.documentUid ?? null).toBe(documentUid);
        expect(read).toMatchObject({ tab, sectionCode: 'OV', projectUid: ACCEPTED_PROJECT_B, ignored: [] });
      }
    }
  });
});
