/**
 * `UI-A-22`, `R-151m`: the version's tabs, «Версия · Блоки · Разбор · Оптимизация», the original's strip
 * «Инфо · Блоки · Замечания · Оптимизация» in our nouns.
 *
 * What is held: the open tab is text and not a link; «Разбор» opens the version's newest run that published a result
 * and carries that run's finding count, and with no such run it is not a link and says why; a failed or cancelled run
 * is not a result; «Оптимизация» is the document's own tab; the page strip draws the tabs on a version and on its
 * «Блоки», and the tabs read the version's runs under the key the run list already uses.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { RunState } from '@/shared/api';
import { routes } from '@/shared/lib';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { VERSION_PAGE_LIMIT } from '@/entities/document-version';
import { DocumentContext, VersionTabsView, latestResultRun, versionTabs } from '@/widgets/document-context';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import { DOCUMENT_UID, PROJECT_UID, RUN_ID, VERSION_UID, runStatus } from '../review/fixtures';
import { classification, page, version } from '../sections/fixtures';

const FACTS = { projectUid: PROJECT_UID, versionUid: VERSION_UID, documentUid: DOCUMENT_UID } as const;
const run = (id: string, state: RunState, findings = 0) =>
  runStatus({ run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}`, state, published_finding_count: findings });

describe('versionTabs', () => {
  it('names the four tabs in the order of the original’s strip', () => {
    expect(versionTabs({ ...FACTS, current: 'version', runs: [] }).map((tab) => tab.label)).toEqual([
      'Версия', 'Блоки', 'Разбор', 'Оптимизация',
    ]);
  });

  it('makes the open tab text and every other reachable tab a link built by routes', () => {
    const tabs = versionTabs({ ...FACTS, current: 'blocks', runs: [run('A', 'published', 3)] });
    expect(tabs.find((tab) => tab.current)?.key).toBe('blocks');
    expect(tabs.find((tab) => tab.key === 'blocks')?.href).toBeNull();
    expect(tabs.find((tab) => tab.key === 'version')?.href).toBe(routes.version(PROJECT_UID, VERSION_UID));
    expect(tabs.find((tab) => tab.key === 'optimisation')?.href).toBe(`${routes.document(PROJECT_UID, DOCUMENT_UID)}?tab=optimisation`);
  });

  it('opens «Разбор» at the newest run that published a result, with its finding count', () => {
    const runs = [run('C', 'running'), run('B', 'published', 7), run('A', 'published', 1)];
    expect(latestResultRun(runs)?.run_id).toBe(runs[1]?.run_id);
    const review = versionTabs({ ...FACTS, current: 'version', runs }).find((tab) => tab.key === 'review');
    expect(review?.href).toBe(routes.review(PROJECT_UID, runs[1]?.run_id as string));
    expect(review?.count).toBe(7);
  });

  it('takes a failed or cancelled run for no result, and says so instead of linking to nowhere', () => {
    const runs = [run('B', 'failed'), run('A', 'cancelled')];
    expect(latestResultRun(runs)).toBeNull();
    const review = versionTabs({ ...FACTS, current: 'version', runs }).find((tab) => tab.key === 'review');
    expect(review?.href).toBeNull();
    expect(review?.title).toBe('У версии ещё нет прогона с результатом');
  });

  it('says nothing about the result while the runs are not known', () => {
    const review = versionTabs({ ...FACTS, current: 'version', runs: undefined }).find((tab) => tab.key === 'review');
    expect(review?.href).toBeNull();
    expect(review?.title).toBeNull();
  });

  it('leaves the document’s tab out when the document is not known yet', () => {
    expect(versionTabs({ ...FACTS, documentUid: undefined, current: 'version', runs: [] }).map((tab) => tab.key)).not.toContain('optimisation');
  });
});

describe('the tabs under the version', () => {
  const runs = [run('B', 'published', 7)];

  it('keep their place on a run, which opens none of them', () => {
    const tabs = versionTabs({ ...FACTS, current: 'run', runs });
    expect(tabs.some((tab) => tab.current)).toBe(false);
    expect(tabs.find((tab) => tab.key === 'version')?.href).toBe(routes.version(PROJECT_UID, VERSION_UID));
    expect(tabs.find((tab) => tab.key === 'review')?.href).toBe(routes.review(PROJECT_UID, runs[0]?.run_id as string));
  });

  it('make «Разбор» the open tab on the review, as text with its count', () => {
    const tabs = versionTabs({ ...FACTS, current: 'review', runs });
    const review = tabs.find((tab) => tab.key === 'review');
    expect(review?.current).toBe(true);
    expect(review?.href).toBeNull();
    expect(review?.count).toBe(7);
    expect(tabs.filter((tab) => tab.current)).toHaveLength(1);
  });
});

describe('VersionTabsView', () => {
  it('draws the open tab with aria-current, a link with its count, and a tab that is not a link', () => {
    const open = renderWith(newClient(), createElement(VersionTabsView, {
      tabs: versionTabs({ ...FACTS, current: 'version', runs: [run('A', 'published', 7)] }),
    }));
    expect(open).toContain('aria-label="Разделы версии"');
    expect(open).toMatch(/aria-current="page"[^>]*data-version-tab="version"/);
    expect(open).toContain(`href="${routes.versionBlocks(PROJECT_UID, VERSION_UID)}"`);
    expect(open).toMatch(/Разбор <span[^>]*>7<\/span>/);
    const none = renderWith(newClient(), createElement(VersionTabsView, {
      tabs: versionTabs({ ...FACTS, current: 'blocks', runs: [] }),
    }));
    expect(none).toContain('data-version-tab-off');
    expect(none).toContain('title="У версии ещё нет прогона с результатом"');
  });
});

describe('the page strip', () => {
  const client = () => {
    const seeded = newClient();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
    seeded.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), page([]));
    return seeded;
  };

  it('carries the tabs on a version and on its «Блоки», reading the runs under the run list’s own key', () => {
    for (const current of ['version', 'blocks'] as const) {
      const markup = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current }));
      expect(markup).toContain('data-version-tabs');
      expect(markup).toContain(`data-context-level="${current}"`);
    }
  });

  it('asks for no runs and draws no tabs until the version itself is known', () => {
    const cold = newClient();
    const markup = renderScreen(cold, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' }));
    expect(markup).not.toContain('data-version-tabs');
    expect(cold.getQueryCache().find({ queryKey: [...queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT)] })).toBeUndefined();
  });

  it('carries them on a run and on its «Разбор» too, where the version is read through the run', () => {
    const seeded = newClient();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ classification: classification({ section_code: 'AR' }) }));
    seeded.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), page([]));
    seeded.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID }));
    for (const current of ['run', 'review'] as const) {
      const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, runId: RUN_ID, current }));
      expect(markup).toContain('data-version-tabs');
      // and the section opens the strip, a link to the section page
      expect(markup).toContain(`href="${routes.projectSection(PROJECT_UID, 'AR')}"`);
    }
  });

  it('puts the section step in the strip of «Блоки» as well', () => {
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ classification: classification({ section_code: 'KJ' }) }));
    const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'blocks' }));
    expect(markup).toContain(`href="${routes.projectSection(PROJECT_UID, 'KJ')}"`);
  });

  it('offers the document’s versions in the strip, marks the newest as the current one, and keeps «Блоки» on «Блоки»', () => {
    const second = version({ version_uid: `${VERSION_UID.slice(0, -1)}Z`, version_ordinal: 2 });
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), page([second, version()]));
    const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'blocks' }));
    expect(markup).toContain('Версия 2 · текущая');
    expect(markup).not.toContain('Версия 1 · текущая');
    expect(markup).toContain('>Версия 1<');
  });

  it('carries none on the levels that are not a version', () => {
    const markup = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, current: 'document' }));
    expect(markup).not.toContain('data-version-tabs');
  });
});
