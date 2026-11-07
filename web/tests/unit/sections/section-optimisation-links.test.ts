/**
 * `UI-A-53`: a section of the project structure, and a section of the dashboard, link to that section's optimisation
 * (`/section-optimisation`) with the section and the project in the address.
 *
 * What is held: the address is built in `routes` (so it carries the identity as given and encodes it), a link is drawn only
 * where there is a section with documents and a project to follow, and the link of the dashboard follows the section the
 * reader chose. What is NOT held, because it is not built yet: that «Оптимизация разделов» reads `?section=` and `?project=`
 * (`UI-B-20`, the `section-specification` widget); today the screen opens on its own default section. A test that
 * asserted it would pass only against a stub.
 */

import { createElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';

import type { SectionDocumentCount } from '@/shared/api';
import { routes } from '@/shared/lib';
import { PROJECT_SECTIONS } from '@/entities/project';
import { ProjectStructureView } from '@/widgets/project-sections';
import { SectionsPanel } from '@/widgets/dashboard/ui/sections-panel';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { auditCounts } from '../dashboard/audit-counts';
import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, version } from './fixtures';

describe('the address of a section’s optimisation', () => {
  it('carries the section, and the project when one is followed', () => {
    expect(routes.sectionOptimisation('OV')).toBe('/section-optimisation?section=OV');
    expect(routes.sectionOptimisation('OV', PROJECT_UID)).toBe(`/section-optimisation?section=OV&project=${PROJECT_UID}`);
  });

  it('encodes what it is given and invents no identity', () => {
    expect(routes.sectionOptimisation('A B', 'prj_x&y')).toBe('/section-optimisation?section=A%20B&project=prj_x%26y');
  });
});

describe('the project’s structure', () => {
  const AR = version({ classification: classification() });
  const KJ = otherVersion('C', { classification: classification({ project_stage: 'R', section_code: 'KJ' }) });
  const UNCLASSIFIED = otherVersion('D', { section: 'AI' });
  const markup = renderWith(
    newClient(),
    createElement(ProjectStructureView, { projectUid: PROJECT_UID, items: [AR, KJ, UNCLASSIFIED], hasNextPage: false }),
  );
  const links = [...markup.matchAll(/<a [^>]*data-section-optimisation-link="([A-Za-z]+)"[^>]*>/g)];

  it('links the optimisation of each section that holds documents, and only those', () => {
    expect(links.map((link) => link[1])).toEqual(['AR', 'KJ']);
  });

  it('puts the section and the project in the address (markup writes & as &amp;)', () => {
    const escaped = (code: string): string => routes.sectionOptimisation(code, PROJECT_UID).replace(/&/g, '&amp;');
    expect(links[0]?.[0]).toContain(`href="${escaped('AR')}"`);
    expect(links[1]?.[0]).toContain(`href="${escaped('KJ')}"`);
  });

  it('says it in words, beside the link to the section’s own page, and draws none for «Не классифицировано»', () => {
    expect(markup.match(/Оптимизация раздела/g) ?? []).toHaveLength(2);
    expect(markup.match(/Открыть раздел/g) ?? []).toHaveLength(2);
    const unclassified = markup.slice(markup.indexOf('data-section-group="unclassified"'));
    expect(unclassified).not.toContain('data-section-optimisation-link');
  });
});

describe('the dashboard’s sections panel', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const rows = [
    ...PROJECT_SECTIONS.map((section, index) => ({
      section: section.code,
      document_count: index,
      finding_count: 0,
      audit_counts: auditCounts(index),
    })),
    { document_count: 0, finding_count: 0, audit_counts: auditCounts(0) },
  ] as unknown as SectionDocumentCount[];

  /** A section row's button across all projects: its code and its name, as the panel draws them. */
  const buttonOf = (code: string): string => {
    const section = PROJECT_SECTIONS.find((candidate) => candidate.code === code);
    if (section === undefined) throw new Error(`no section ${code}`);
    return `${section.code}${section.name}`;
  };
  /** `UI-A-37`: with a project the row is a link, and the panel is opened by the toggle at the row's end. */
  const toggle = (view: LiveRender, code: string): Promise<boolean> => view.pressMarked('data-section-toggle', code);

  async function mountPanel(projectUid: string | null): Promise<LiveRender> {
    live = await mountLive(createElement(SectionsPanel, { rows, projectUid }));
    return live;
  }

  it('links the chosen section’s optimisation, with the project the dashboard follows', async () => {
    const view = await mountPanel(PROJECT_UID);
    expect(view.markup()).not.toContain('data-section-optimisation-link');
    expect(await toggle(view, 'AR')).toBe(true);
    const tag = view.markup().match(/<a [^>]*data-section-optimisation-link="AR"[^>]*>/)?.[0];
    expect(tag).toContain(`href="${routes.sectionOptimisation('AR', PROJECT_UID)}"`);
    expect(view.markup()).toContain('Оптимизация раздела');
  });

  it('follows the section the reader chose, not the first one', async () => {
    const view = await mountPanel(PROJECT_UID);
    await toggle(view, 'AR');
    await toggle(view, 'KJ');
    expect(view.markup()).toContain('data-section-optimisation-link="KJ"');
    expect(view.markup()).not.toContain('data-section-optimisation-link="AR"');
  });

  it('draws no link across all projects, where there is no one project to follow', async () => {
    const view = await mountPanel(null);
    await view.press(buttonOf('AR'));
    expect(view.markup()).toContain('data-selected-section="AR"');
    expect(view.markup()).not.toContain('data-section-optimisation-link');
    expect(view.markup()).toContain('Открыть проекты');
  });
});
