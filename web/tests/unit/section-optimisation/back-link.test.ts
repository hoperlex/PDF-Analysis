/**
 * The way back from «Оптимизация разделов»: the original's «←» leads to the section's projects.
 *
 * Here it leads where the reader came from. With a project in the address that is the project's section page (the
 * dashboard's «Оптимизация раздела» link and the section list's link both carry the project and the section); with none, it
 * is the dashboard, whose table of sections is the screen this one is a step below.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { SectionOptimisationPage, readSectionOptimisationAddress } from '@/_pages/section-optimisation';

import { newClient, renderScreen } from '../screens/harness';

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function page(query: Parameters<typeof readSectionOptimisationAddress>[0]): string {
  return renderScreen(newClient(), createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress(query) }));
}

describe('the link back', () => {
  it('leads to the project’s section page when the address names a project and a section', () => {
    const markup = page({ section: 'KJ', project: PROJECT });
    expect(markup).toContain('data-section-optimisation-back="section"');
    expect(markup).toContain(`<a href="/projects/${PROJECT}/sections/KJ">← К разделу проекта</a>`);
  });

  it('leads to the dashboard when it names no project', () => {
    const markup = page({ section: 'KJ' });
    expect(markup).toContain('data-section-optimisation-back="dashboard"');
    expect(markup).toContain('<a href="/dashboard">← К дашборду</a>');
    expect(markup).not.toContain('/sections/');
  });
});
