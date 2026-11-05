/**
 * `UI-A-22`: the context strip of the document pages. Every step but the current one links; names that are
 * not known are the generic words, never invented ones.
 */
import { describe, expect, it } from 'vitest';

import { contextSteps } from '@/widgets/document-context';

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

  it('uses the generic words while names are unknown', () => {
    const steps = contextSteps({ projectUid: 'prj_A', documentUid: 'doc_D', versionUid: 'ver_V' }, 'version');
    expect(steps.map((s) => s.label)).toEqual(['Проекты', 'Проект', 'Документ', 'Версия']);
  });
});
