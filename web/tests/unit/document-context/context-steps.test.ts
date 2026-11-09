/**
 * `UI-A-22`: the context strip of the document pages. Every step but the current one links; names that are
 * not known are the generic words, never invented ones.
 */
import { describe, expect, it } from 'vitest';

import { routes } from '@/shared/lib';
import { contextSteps, versionTabs } from '@/widgets/document-context';

const FACTS = {
  projectUid: 'prj_A',
  projectName: 'Школа',
  documentUid: 'doc_D',
  documentTitle: 'АР-1',
  versionUid: 'ver_V',
  versionOrdinal: 3,
  runId: 'run_R',
};

describe('contextSteps', () => {
  it('goes Проекты › Проект › Документ › Версия › Прогон › Разбор on the review', () => {
    const steps = contextSteps(FACTS, 'review');
    expect(steps.map((s) => s.label)).toEqual(['Проекты', 'Школа', 'АР-1', 'Версия 3', 'Прогон', 'Разбор']);
    expect(steps.at(-1)?.href).toBeNull();
    expect(steps.slice(0, -1).every((s) => s.href !== null)).toBe(true);
  });

  it('stops at the document on the document page, which is the current step', () => {
    const steps = contextSteps(FACTS, 'document');
    expect(steps.map((s) => s.key)).toEqual(['projects', 'project', 'document']);
    expect(steps.at(-1)?.href).toBeNull();
  });

  // Second UX pass: the version's comparison screen kept a copy of the strip; it is a level of the shared one now.
  it('ends the version comparison at «Сравнение», with the version a link back to the version page', () => {
    const steps = contextSteps(FACTS, 'comparison');
    expect(steps.map((s) => s.label)).toEqual(['Проекты', 'Школа', 'АР-1', 'Версия 3', 'Сравнение']);
    expect(steps.map((s) => s.key)).toEqual(['projects', 'project', 'document', 'version', 'comparison']);
    expect(steps.find((s) => s.key === 'version')?.href).toBe(routes.version('prj_A', 'ver_V'));
    expect(steps.at(-1)?.href).toBeNull();
    expect(steps.slice(0, -1).every((s) => s.href !== null)).toBe(true);
    // No run and no «Разбор» on the way, whatever the facts carry.
    expect(steps.map((s) => s.key)).not.toContain('run');
    expect(steps.map((s) => s.key)).not.toContain('review');
  });

  it('draws the comparison strip alone: the version’s tab row is not part of it', () => {
    // `blocks` is a tab and ends the strip too; `comparison` is a place under the version and has no tab.
    expect(contextSteps(FACTS, 'blocks').at(-1)?.key).toBe('blocks');
    expect(contextSteps(FACTS, 'comparison').at(-1)?.key).toBe('comparison');
    expect(versionTabs({ projectUid: 'prj_A', versionUid: 'ver_V', documentUid: 'doc_D', runs: [], current: 'version' }).map((t) => t.key))
      .not.toContain('comparison');
  });

  it('uses the generic words while names are unknown', () => {
    const steps = contextSteps({ projectUid: 'prj_A', documentUid: 'doc_D', versionUid: 'ver_V' }, 'version');
    expect(steps.map((s) => s.label)).toEqual(['Проекты', 'Проект', 'Документ', 'Версия']);
  });

  // `UI-A-23`: the original's strip opens «<код раздела> / <имя проекта>» and the section is a link to its page.
  it('puts the confirmed section between the project and the document, a link to the section page', () => {
    const steps = contextSteps({ ...FACTS, sectionCode: 'AR' }, 'version');
    expect(steps.map((s) => s.label)).toEqual(['Проекты', 'Школа', 'АР', 'АР-1', 'Версия 3']);
    const section = steps.find((s) => s.key === 'section');
    expect(section?.href).toBe(routes.projectSection('prj_A', 'AR'));
    expect(section?.title).toBe('АР Архитектурные решения');
  });

  it('draws no section step for a document with no confirmed section, an unknown code, or the section page itself', () => {
    expect(contextSteps(FACTS, 'version').map((s) => s.key)).not.toContain('section');
    expect(contextSteps({ ...FACTS, sectionCode: 'ZZ' }, 'version').map((s) => s.key)).not.toContain('section');
    const own = contextSteps({ ...FACTS, sectionCode: 'AR', sectionLabel: 'АР Архитектурные решения' }, 'section');
    expect(own.filter((s) => s.key === 'section')).toHaveLength(1);
    expect(own.find((s) => s.key === 'section')?.href).toBeNull();
  });

  it('keeps the section on every level under the document', () => {
    for (const level of ['document', 'version', 'blocks', 'comparison', 'run', 'review'] as const) {
      expect(contextSteps({ ...FACTS, sectionCode: 'KJ' }, level).map((s) => s.key)).toContain('section');
    }
  });
});
