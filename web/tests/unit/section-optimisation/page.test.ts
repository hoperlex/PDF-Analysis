/**
 * `UI-B-20`, `UI-B-22`: «Оптимизация разделов» opens on the section, the project and the tab its address names.
 *
 * Rendered, not read from source (`D-53`): the selects a reviewer would see and the reads the screen starts. The project
 * an address names has no unfiltered answer yet, so the project select must still offer it — from its own read, from the
 * narrowed answer, or by its identity — and never silently drop it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectUid } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { SectionOptimisationPage, readSectionOptimisationAddress } from '@/_pages/section-optimisation';

import { newClient, renderScreen } from '../screens/harness';
import { sectionAnswer } from '../section-specification/fixtures';
import { ACCEPTED_PROJECT_B, acceptedKey, projectRead, specificationKey } from './fixtures';

function selected(markup: string, value: string): boolean {
  const options = markup.match(/<option[^>]*>/g) ?? [];
  return options.some((tag) => tag.includes(`value="${value}"`) && tag.includes('selected=""'));
}

function text(markup: string): string {
  return markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
}

function page(query: { section?: string; project?: string; tab?: string }, client = newClient()): { markup: string; client: ReturnType<typeof newClient> } {
  const markup = renderScreen(
    client,
    createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress(query) }),
  );
  return { markup, client };
}

const keys = (client: ReturnType<typeof newClient>): readonly unknown[] =>
  client.getQueryCache().getAll().map((query) => query.queryKey);

describe('opening on the address', () => {
  it('opens on the section and the project the address names, and reads exactly that', () => {
    const { markup, client } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B });
    expect(selected(markup, 'KJ')).toBe(true);
    expect(selected(markup, 'AR')).toBe(false);
    expect(selected(markup, ACCEPTED_PROJECT_B)).toBe(true);
    expect(keys(client)).toContainEqual(specificationKey('KJ', ACCEPTED_PROJECT_B));
    expect(keys(client)).not.toContainEqual(specificationKey('AR', null));
  });

  it('offers the project of the address although no unfiltered answer lists it: by its identity first', () => {
    const { markup } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B });
    expect(markup).toContain('data-section-project-filter="1"');
    expect(text(markup)).toContain(ACCEPTED_PROJECT_B);
  });

  it('names that project from its own read', () => {
    const client = newClient();
    client.setQueryData(queryKeys.projects.detail(ACCEPTED_PROJECT_B as ProjectUid), projectRead(ACCEPTED_PROJECT_B, 'Детский сад'));
    const { markup } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B }, client);
    expect(selected(markup, ACCEPTED_PROJECT_B)).toBe(true);
    expect(text(markup)).toContain('Детский сад');
    expect(text(markup)).not.toContain(`${ACCEPTED_PROJECT_B}`);
  });

  it('names it from the narrowed answer once that lists it', () => {
    const client = newClient();
    client.setQueryData(
      specificationKey('AR', ACCEPTED_PROJECT_B),
      sectionAnswer({ project_filter: ACCEPTED_PROJECT_B as ProjectUid, projects: [{ ...sectionAnswer().projects[0]!, project_uid: ACCEPTED_PROJECT_B as ProjectUid, name: 'Больница' }] }),
    );
    const { markup } = page({ project: ACCEPTED_PROJECT_B }, client);
    expect(selected(markup, ACCEPTED_PROJECT_B)).toBe(true);
    expect(text(markup)).toContain('Больница');
  });

  it('keeps the old behaviour without an address: АР, every project', () => {
    const { markup, client } = page({});
    expect(selected(markup, 'AR')).toBe(true);
    expect(selected(markup, '')).toBe(true);
    expect(markup).toContain('data-section-project-filter="0"');
    expect(keys(client)).toContainEqual(specificationKey('AR', null));
    expect(markup).not.toContain('data-address-ignored');
  });

  it('sets aside what it cannot read and says so', () => {
    const { markup } = page({ section: 'ZZ', project: 'nope', tab: 'history' });
    expect(markup).toContain('data-address-ignored="section project tab"');
    expect(text(markup)).toContain('Из адреса не прочитано: раздел, проект, вкладка.');
    expect(selected(markup, 'AR')).toBe(true);
  });
});

describe('the tabs', () => {
  it('opens «Спецификация» by default and mounts nothing of «Принято», whose number is the only thing read for it', () => {
    const { markup, client } = page({});
    expect(markup).toContain('data-section-optimisation-panel="specification"');
    expect(markup).toMatch(/aria-selected="true"[^>]*data-section-optimisation-tab="specification"/);
    expect(markup).toContain('data-section-specification');
    expect(markup).not.toContain('data-section-accepted');
    // The tab's number (`UI-B-22`) is the accepted list's own first page: the key the open tab would read.
    expect(keys(client).filter((key) => (key as string[])[1] === 'accepted')).toEqual([acceptedKey({ sectionCode: 'AR' })]);
  });

  it('opens «Принято» on the section and project of the address; the specification is read for its number only', () => {
    const { markup, client } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B, tab: 'accepted' });
    expect(markup).toContain('data-section-optimisation-panel="accepted"');
    expect(markup).toContain('data-section-accepted');
    expect(markup).not.toContain('data-section-specification');
    expect(selected(markup, 'KJ')).toBe(true);
    expect(selected(markup, ACCEPTED_PROJECT_B)).toBe(true);
    expect(keys(client)).toContainEqual(acceptedKey({ sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B }));
    // The specification tab is not mounted, but its number is read under the key the tab itself would use (once, whichever
    // tab is open), for the section and project chosen and for no other.
    expect(keys(client)).toContainEqual(specificationKey('KJ', ACCEPTED_PROJECT_B));
    expect(keys(client).filter((key) => (key as string[])[1] === 'section-specification')).toHaveLength(1);
  });

  it('names both tabs', () => {
    const said = text(page({}).markup);
    expect(said).toContain('Спецификация');
    expect(said).toContain('Принято');
  });
});
