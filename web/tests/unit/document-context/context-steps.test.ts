/**
 * `UI-A-22`, `UIP-G-09`: the row of the document frame, «раздел › документ». Every step but the current one links; names that
 * are not known are the generic words, never invented ones; the version and its code are not in the row.
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
  it('goes Объект › Документ › Прогон › Разбор on the review of a document with no confirmed section', () => {
    const steps = contextSteps(FACTS, 'review');
    expect(steps.map((s) => s.label)).toEqual(['Школа', 'АР-1', 'Прогон', 'Разбор']);
    expect(steps.map((s) => s.key)).toEqual(['project', 'document', 'run', 'review']);
    expect(steps.at(-1)?.href).toBeNull();
    expect(steps.slice(0, -1).every((s) => s.href !== null)).toBe(true);
    expect(steps.find((s) => s.key === 'run')?.href).toBe(routes.run('prj_A', 'run_R'));
  });

  it('is «раздел › документ» on a version, its «Блоки» and the document\'s «Оптимизация»: no version and no code in the row', () => {
    for (const level of ['version', 'blocks', 'optimisation'] as const) {
      const steps = contextSteps({ ...FACTS, sectionCode: 'AR' }, level);
      expect(steps.map((s) => s.label), level).toEqual(['АР', 'АР-1']);
      expect(steps.map((s) => s.href), level).toEqual([routes.projectSection('prj_A', 'AR'), routes.document('prj_A', 'doc_D')]);
      expect(JSON.stringify(steps), level).not.toContain('ver_');
    }
  });

  it('stops at the document on the document page, which is the current step', () => {
    const steps = contextSteps(FACTS, 'document');
    expect(steps.map((s) => s.key)).toEqual(['project', 'document']);
    expect(steps.at(-1)?.href).toBeNull();
  });

  it('ends the run at «Прогон», the current step, and the log at the run it is the journal of', () => {
    const run = contextSteps({ ...FACTS, sectionCode: 'AR' }, 'run');
    expect(run.map((s) => s.label)).toEqual(['АР', 'АР-1', 'Прогон']);
    expect(run.at(-1)?.href).toBeNull();
    const log = contextSteps({ ...FACTS, sectionCode: 'AR' }, 'log');
    expect(log.map((s) => s.label)).toEqual(['АР', 'АР-1', 'Прогон']);
    expect(log.at(-1)?.href).toBe(routes.run('prj_A', 'run_R'));
  });

  // Second UX pass: the version's comparison screen kept a copy of the strip; it is a level of the shared one now.
  it('ends the version comparison at «Сравнение», with the version a link back to the version page', () => {
    const steps = contextSteps(FACTS, 'comparison');
    expect(steps.map((s) => s.label)).toEqual(['Школа', 'АР-1', 'Версия 3', 'Сравнение']);
    expect(steps.map((s) => s.key)).toEqual(['project', 'document', 'version', 'comparison']);
    expect(steps.find((s) => s.key === 'version')?.href).toBe(routes.version('prj_A', 'ver_V'));
    expect(steps.at(-1)?.href).toBeNull();
    expect(steps.slice(0, -1).every((s) => s.href !== null)).toBe(true);
    // No run and no «Разбор» on the way, whatever the facts carry.
    expect(steps.map((s) => s.key)).not.toContain('run');
    expect(steps.map((s) => s.key)).not.toContain('review');
  });

  it('draws the comparison row alone: the version’s tab row is not part of it', () => {
    // `blocks` is a tab and has no step of its own; `comparison` is a place under the version and has no tab.
    expect(contextSteps(FACTS, 'blocks').map((s) => s.key)).not.toContain('blocks');
    expect(contextSteps(FACTS, 'comparison').at(-1)?.key).toBe('comparison');
    expect(versionTabs({ projectUid: 'prj_A', versionUid: 'ver_V', documentUid: 'doc_D', runs: [], current: 'version' }).map((t) => t.key))
      .not.toContain('comparison');
  });

  it('uses the generic words while names are unknown', () => {
    const steps = contextSteps({ projectUid: 'prj_A', documentUid: 'doc_D', versionUid: 'ver_V' }, 'version');
    expect(steps.map((s) => s.label)).toEqual(['Объект', 'Документ']);
  });

  // `UI-A-23`: the original's strip opens «<код раздела> / <имя проекта>» and the section is a link to its page.
  it('opens with the confirmed section, a link to the section page, and the object only where there is no section', () => {
    const steps = contextSteps({ ...FACTS, sectionCode: 'AR' }, 'version');
    expect(steps.map((s) => s.label)).toEqual(['АР', 'АР-1']);
    const section = steps.find((s) => s.key === 'section');
    expect(section?.href).toBe(routes.projectSection('prj_A', 'AR'));
    expect(section?.title).toBe('АР Архитектурные решения');
    expect(steps.map((s) => s.key)).not.toContain('project');
    expect(contextSteps(FACTS, 'version')[0]).toMatchObject({ key: 'project', label: 'Школа', href: routes.project('prj_A') });
  });

  it('draws no section step for a document with no confirmed section, an unknown code, or the section page itself', () => {
    expect(contextSteps(FACTS, 'version').map((s) => s.key)).not.toContain('section');
    expect(contextSteps({ ...FACTS, sectionCode: 'ZZ' }, 'version').map((s) => s.key)).not.toContain('section');
    const own = contextSteps({ ...FACTS, sectionCode: 'AR', sectionLabel: 'АР Архитектурные решения' }, 'section');
    expect(own.map((s) => s.key)).toEqual(['project', 'section']);
    expect(own.find((s) => s.key === 'section')?.href).toBeNull();
  });

  it('keeps the section on every level under the document', () => {
    for (const level of ['document', 'optimisation', 'version', 'blocks', 'log', 'comparison', 'run', 'review'] as const) {
      expect(contextSteps({ ...FACTS, sectionCode: 'KJ' }, level).map((s) => s.key)).toContain('section');
    }
  });
});
