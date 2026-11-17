/**
 * `UI-A-22`, `R-151m`, `UIP-G-09`: the version's tabs, «Инфо · Блоки · Лог · Разбор · Оптимизация», the original's strip
 * «Инфо · Блоки · Лог · Замечания · Оптимизация» in our nouns, and the frame they stand in.
 *
 * What is held: the open tab is text and not a link; «Разбор» opens the version's newest run that published a result
 * and carries that run's finding count, and with no such run it is not a link and says why; a failed or cancelled run
 * is not a result; «Лог» opens the newest run of any state on its journal, is the operator's and says why it is not
 * a link when there is no run; «Блоки» carries the number it is handed and «Оптимизация» the proposals of the version's
 * latest pass, with those still undecided in its hint; «Оптимизация» is the document's own tab; the frame draws the tabs and
 * the version bar on the document's page, its «Оптимизация», a version, its «Блоки», a run, its log and its «Разбор», and the tabs
 * read the version's runs under the key the run list already uses.
 *
 * `UIP-S04-02`: both numbers are the version's own read (`block_count` and the counts of its `audit`): none without the
 * field and never a zero, the same on every page of the frame including the document's, where the version held from a
 * listing carries neither, and a change of version changes them together with the tabs.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { DocumentAudit, RunState } from '@/shared/api';
import { routes } from '@/shared/lib';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { VERSION_PAGE_LIMIT } from '@/entities/document-version';
import {
  ALL_VERSIONS_LABEL,
  DocumentContext,
  PDF_BUTTON_HINT,
  PDF_BUTTON_LABEL,
  VersionTabsView,
  latestResultRun,
  optimisationOf,
  runLogAddress,
  versionFigures,
  versionTabs,
} from '@/widgets/document-context';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import { DOCUMENT_UID, PROJECT_UID, RUN_ID, VERSION_UID, runStatus } from '../review/fixtures';
import { classification, page, version } from '../sections/fixtures';

const FACTS = { projectUid: PROJECT_UID, versionUid: VERSION_UID, documentUid: DOCUMENT_UID } as const;
const run = (id: string, state: RunState, findings = 0) =>
  runStatus({ run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}`, state, published_finding_count: findings });
/** The audit of a version read (`UIP-S04-01`), with the optimisation counts of its latest pass when it has one. */
const audit = (pass?: { proposals: number; undecided: number }): DocumentAudit => ({
  state: 'awaiting_decision',
  finding_count: 5,
  undecided_finding_count: 2,
  partial: false,
  ...(pass === undefined ? {} : { optimisation_proposal_count: pass.proposals, optimisation_undecided_count: pass.undecided }),
});

describe('versionTabs', () => {
  it('names the five tabs in the order of the original’s strip', () => {
    expect(versionTabs({ ...FACTS, current: 'version', runs: [] }).map((tab) => tab.label)).toEqual([
      'Инфо', 'Блоки', 'Лог', 'Разбор', 'Оптимизация',
    ]);
  });

  it('leaves «Лог» out for an account that does not read the journal, and keeps it while the account is not known', () => {
    const keys = (mayReadLog: boolean | undefined) =>
      versionTabs({ ...FACTS, current: 'version', runs: [], mayReadLog }).map((tab) => tab.key);
    expect(keys(false)).toEqual(['version', 'blocks', 'review', 'optimisation']);
    expect(keys(true)).toContain('log');
    expect(keys(undefined)).toContain('log');
  });

  it('opens «Лог» at the newest run of any state, on its journal', () => {
    const runs = [run('C', 'running'), run('B', 'published', 7), run('A', 'failed')];
    const log = versionTabs({ ...FACTS, current: 'version', runs }).find((tab) => tab.key === 'log');
    expect(log?.href).toBe(runLogAddress(PROJECT_UID, runs[0]?.run_id as string));
    expect(log?.href).toBe(`${routes.run(PROJECT_UID, runs[0]?.run_id as string)}?tab=journal`);
    expect(log?.count).toBeNull();
    // «Разбор» still opens the newest run that published a result, which is not that run.
    expect(versionTabs({ ...FACTS, current: 'version', runs }).find((tab) => tab.key === 'review')?.href)
      .toBe(routes.review(PROJECT_UID, runs[1]?.run_id as string));
  });

  it('says «Лог» has no link when the version has no run, as «Разбор» does, and says nothing while the runs are not known', () => {
    const none = versionTabs({ ...FACTS, current: 'version', runs: [] }).find((tab) => tab.key === 'log');
    expect(none?.href).toBeNull();
    expect(none?.current).toBe(false);
    expect(none?.title).toBe('У версии ещё не было прогонов');
    const unknown = versionTabs({ ...FACTS, current: 'version', runs: undefined }).find((tab) => tab.key === 'log');
    expect(unknown?.href).toBeNull();
    expect(unknown?.title).toBeNull();
  });

  it('carries the number of blocks it is handed, none when nobody has read it, and zero when it is zero', () => {
    const count = (blockCount: number | undefined) =>
      versionTabs({ ...FACTS, current: 'version', runs: [], blockCount }).find((tab) => tab.key === 'blocks')?.count;
    expect(count(15)).toBe(15);
    expect(count(0)).toBe(0);
    expect(count(undefined)).toBeNull();
  });

  it('carries the proposals of the version’s latest pass, with those undecided in the hint, and no number without a pass', () => {
    const optimisation = (pass: { proposals: number; undecided: number | null } | null | undefined) =>
      versionTabs({ ...FACTS, current: 'version', runs: [], optimisation: pass }).find((tab) => tab.key === 'optimisation');
    const counted = optimisation({ proposals: 8, undecided: 3 });
    expect(counted?.count).toBe(8);
    expect(counted?.title).toBe('Предложений последнего прохода: 8, из них без решения: 3');
    expect(optimisation({ proposals: 0, undecided: 0 })?.count).toBe(0);
    // a pass whose undecided count the server did not give says its proposals and nothing of the rest
    expect(optimisation({ proposals: 8, undecided: null })?.title).toBe('Предложений последнего прохода: 8');
    for (const none of [null, undefined]) {
      expect(optimisation(none)?.count).toBeNull();
      expect(optimisation(none)?.title).toBe('Оптимизация документа');
    }
  });

  it('makes the open tab text and every other reachable tab a link built by routes', () => {
    const tabs = versionTabs({ ...FACTS, current: 'blocks', runs: [run('A', 'published', 3)] });
    expect(tabs.find((tab) => tab.current)?.key).toBe('blocks');
    expect(tabs.find((tab) => tab.key === 'blocks')?.href).toBeNull();
    expect(tabs.find((tab) => tab.key === 'version')?.href).toBe(routes.version(PROJECT_UID, VERSION_UID));
    expect(tabs.find((tab) => tab.key === 'optimisation')?.href).toBe(`${routes.document(PROJECT_UID, DOCUMENT_UID)}?tab=optimisation`);
  });

  it('makes «Лог» and the document’s «Оптимизация» the open tab on their own pages, and none the open one on the document’s page', () => {
    const runs = [run('A', 'published', 1)];
    expect(versionTabs({ ...FACTS, current: 'log', runs }).filter((tab) => tab.current).map((tab) => tab.key)).toEqual(['log']);
    expect(versionTabs({ ...FACTS, current: 'optimisation', runs }).filter((tab) => tab.current).map((tab) => tab.key)).toEqual(['optimisation']);
    const document = versionTabs({ ...FACTS, current: 'document', runs });
    expect(document.some((tab) => tab.current)).toBe(false);
    expect(document.find((tab) => tab.key === 'version')?.href).toBe(routes.version(PROJECT_UID, VERSION_UID));
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

describe('the figures of the version read (`UIP-S04-02`)', () => {
  it('takes the blocks and the optimisation pass from the one read of the version', () => {
    expect(versionFigures(version({ block_count: 15, audit: audit({ proposals: 8, undecided: 3 }) }))).toEqual({
      blockCount: 15,
      optimisation: { proposals: 8, undecided: 3 },
    });
  });

  it('has no number for a field the server did not give, and keeps a true zero', () => {
    expect(versionFigures(version())).toEqual({ blockCount: undefined, optimisation: null });
    expect(versionFigures(version({ block_count: 0, audit: audit({ proposals: 0, undecided: 0 }) }))).toEqual({
      blockCount: 0,
      optimisation: { proposals: 0, undecided: 0 },
    });
    // an audit with no pass in it (never optimised) is no pass, not a pass of nothing
    expect(optimisationOf(audit())).toBeNull();
    expect(optimisationOf(undefined)).toBeNull();
  });

  it('says the proposals alone when the undecided count is missing', () => {
    expect(optimisationOf({ ...audit(), optimisation_proposal_count: 4 })).toEqual({ proposals: 4, undecided: null });
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

  it('draws the number of «Блоки» and of «Оптимизация» as the number of «Разбор», and the log as a link to the journal', () => {
    const markup = renderWith(newClient(), createElement(VersionTabsView, {
      tabs: versionTabs({
        ...FACTS, current: 'version', runs: [run('A', 'published', 7)], blockCount: 15, optimisation: { proposals: 8, undecided: 3 },
      }),
    }));
    expect(markup).toMatch(/Блоки <span[^>]*>15<\/span>/);
    expect(markup).toMatch(/Оптимизация <span[^>]*>8<\/span>/);
    expect(markup).toContain('title="Предложений последнего прохода: 8, из них без решения: 3"');
    expect(markup).toContain(`href="${runLogAddress(PROJECT_UID, `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8A`)}"`);
  });
});

describe('the frame', () => {
  const client = () => {
    const seeded = newClient();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
    seeded.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), page([]));
    return seeded;
  };

  it('carries the tabs and the version bar on a version and on its «Блоки», reading the runs under the run list’s own key', () => {
    for (const current of ['version', 'blocks'] as const) {
      const markup = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current }));
      expect(markup).toContain('data-version-tabs');
      expect(markup).toContain('data-version-bar');
      expect(markup).toContain(`data-context-level="${current}"`);
    }
  });

  it('asks for no runs and draws no tabs and no bar until the version itself is known', () => {
    const cold = newClient();
    const markup = renderScreen(cold, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' }));
    expect(markup).not.toContain('data-version-tabs');
    expect(markup).not.toContain('data-version-bar');
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
      expect(markup).toContain('data-version-bar');
      // and the section opens the row, a link to the section page
      expect(markup).toContain(`href="${routes.projectSection(PROJECT_UID, 'AR')}"`);
    }
  });

  it('is «раздел › документ» and tabs on the version, with no code of the version in it and the object left to the section', () => {
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ classification: classification({ section_code: 'KJ' }) }));
    const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'blocks' }));
    expect(markup).toContain(`href="${routes.projectSection(PROJECT_UID, 'KJ')}"`);
    expect(markup).toContain(`href="${routes.document(PROJECT_UID, DOCUMENT_UID)}"`);
    expect(markup).not.toContain('data-context-step="project"');
    // the version is the bar's, and its code is the version page's «Сведения о версии и файле», not the frame's
    expect(markup).not.toContain('data-context-step="version"');
    expect(markup).not.toContain('<code');
    const bare = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' }));
    expect(bare).toContain('data-context-step="project"');
  });

  it('draws the version choice even for one version, ending in «Все версии…», the document’s own page', () => {
    const markup = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' }));
    expect(markup).toContain('data-version-choice');
    expect(markup).toContain('>Версия 1<');
    expect(markup).toContain(`>${ALL_VERSIONS_LABEL}<`);
  });

  it('offers the document’s versions in the bar, marks the newest as the current one, and keeps «Блоки» on «Блоки»', () => {
    const second = version({ version_uid: `${VERSION_UID.slice(0, -1)}Z`, version_ordinal: 2 });
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), page([second, version()]));
    const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'blocks' }));
    expect(markup).toContain('Версия 2 · текущая');
    expect(markup).not.toContain('Версия 1 · текущая');
    expect(markup).toContain('>Версия 1<');
  });

  it('says the history is longer than the page when it is', () => {
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), page([version()], 'Y3Vyc29y'));
    const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' }));
    expect(markup).toContain('показаны первые 1');
  });

  it('draws «Лог» for an operator and not for a read-only account', () => {
    const operator = client();
    operator.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    expect(renderScreen(operator, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' })))
      .toContain('data-version-tab="log"');
    const viewer = client();
    viewer.setQueryData(queryKeys.account.me(), { roles: ['viewer'] });
    expect(renderScreen(viewer, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' })))
      .not.toContain('data-version-tab="log"');
  });

  it('puts the log tab open on «Лог» and the optimisation tab open on the document’s «Оптимизация»', () => {
    const log = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'log' }));
    expect(log).toMatch(/aria-current="page"[^>]*data-version-tab="log"/);
    const optimisation = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'optimisation' }));
    expect(optimisation).toMatch(/aria-current="page"[^>]*data-version-tab="optimisation"/);
    // the document is a link to the list of its versions, since the page is not that list
    expect(optimisation).toContain(`href="${routes.document(PROJECT_UID, DOCUMENT_UID)}"`);
  });

  it('draws the frame on the document’s own page with the version the page holds for its names, and reads the version only for the figures', () => {
    const held = version({ classification: classification({ section_code: 'AR' }) });
    const cold = newClient();
    const markup = renderScreen(cold, createElement(DocumentContext, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, version: held, current: 'document' }));
    expect(markup).toContain('data-version-tabs');
    expect(markup).toContain('data-version-bar');
    expect(markup).toMatch(/aria-current="page"[^>]*>Комплект АР</);
    // the read is the version's own entry, asked for the numbers; nothing of it is drawn until it has answered
    expect(cold.getQueryCache().find({ queryKey: [...queryKeys.versions.detail(VERSION_UID)] })).toBeDefined();
    expect(markup).not.toMatch(/Блоки <span/);
    expect(markup).not.toMatch(/Оптимизация <span/);
  });

  it('draws the numbers of the version read on the document’s page, where the version held from a listing carries none', () => {
    const held = version({ classification: classification({ section_code: 'AR' }) });
    const seeded = newClient();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ block_count: 15, audit: audit({ proposals: 8, undecided: 3 }) }));
    for (const current of ['document', 'optimisation'] as const) {
      const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, version: held, current }));
      expect(markup, current).toMatch(/Блоки <span[^>]*>15<\/span>/);
      expect(markup, current).toMatch(/Оптимизация <span[^>]*>8<\/span>/);
    }
  });

  it('carries the optimisation number from the version’s audit, with those undecided in the hint', () => {
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ audit: audit({ proposals: 8, undecided: 3 }) }));
    const markup = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' }));
    expect(markup).toMatch(/Оптимизация <span[^>]*>8<\/span>/);
    expect(markup).toContain('из них без решения: 3');
    // and with no pass in the audit, or no audit at all, the tab has no number
    for (const none of [version({ audit: audit() }), version()]) {
      const bare = client();
      bare.setQueryData(queryKeys.versions.detail(VERSION_UID), none);
      expect(renderScreen(bare, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'version' })))
        .not.toMatch(/Оптимизация <span/);
    }
  });

  it('hands «Блоки» the number of the version read, none when the server did not give it and zero when it is zero', () => {
    const blocks = (read: ReturnType<typeof version>, current: 'blocks' | 'version' = 'blocks') => {
      const seeded = client();
      seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), read);
      return renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current }));
    };
    expect(blocks(version({ block_count: 15 }))).toMatch(/Блоки <span[^>]*>15<\/span>/);
    expect(blocks(version({ block_count: 15 }), 'version')).toMatch(/Блоки <span[^>]*>15<\/span>/);
    expect(blocks(version({ block_count: 0 }))).toMatch(/Блоки <span[^>]*>0<\/span>/);
    expect(blocks(version())).not.toMatch(/Блоки <span/);
  });

  it('changes the numbers with the version: each version’s tabs carry that version’s own figures', () => {
    const otherUid = `${VERSION_UID.slice(0, -1)}Z`;
    const seeded = client();
    seeded.setQueryData(queryKeys.versions.detail(otherUid), version({
      version_uid: otherUid, version_ordinal: 2, block_count: 21, audit: audit({ proposals: 4, undecided: 0 }),
    }));
    seeded.setQueryData(queryKeys.runs.list(otherUid, undefined, RUN_PAGE_LIMIT), page([]));
    seeded.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ block_count: 15, audit: audit({ proposals: 8, undecided: 3 }) }));
    const first = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current: 'blocks' }));
    const second = renderScreen(seeded, createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: otherUid, current: 'blocks' }));
    expect(first).toMatch(/Блоки <span[^>]*>15<\/span>/);
    expect(first).toMatch(/Оптимизация <span[^>]*>8<\/span>/);
    expect(second).toMatch(/Блоки <span[^>]*>21<\/span>/);
    expect(second).toMatch(/Оптимизация <span[^>]*>4<\/span>/);
    expect(second).not.toMatch(/Блоки <span[^>]*>15<\/span>/);
  });

  it('draws the row alone on the levels that have no version in view', () => {
    for (const current of ['section', 'comparison'] as const) {
      const markup = renderScreen(client(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current, sectionLabel: 'АР' }));
      expect(markup, current).not.toContain('data-version-tabs');
      expect(markup, current).not.toContain('data-version-bar');
    }
  });
});

describe('«Просмотр PDF» in the version bar', () => {
  const seeded = () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ page_count: 7 }));
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), page([]));
    return client;
  };
  it('is a link to the version with the window open on a page that has no window of its own — the button is on every tab', () => {
    for (const current of ['blocks', 'log', 'review'] as const) {
      const markup = renderScreen(seeded(), createElement(DocumentContext, { projectUid: PROJECT_UID, versionUid: VERSION_UID, current }));
      expect(markup, current).toContain(`href="${routes.version(PROJECT_UID, VERSION_UID)}?pdf=1"`);
      expect(markup, current).toContain('data-version-pdf-link');
      expect(markup, current).toContain(PDF_BUTTON_LABEL);
      expect(markup, current).toContain(`title="${PDF_BUTTON_HINT}"`);
      expect(markup, current).not.toContain('data-version-pdf-toggle');
    }
    expect(PDF_BUTTON_HINT).toBe('Весь документ, снизу');
  });

  it('is the button that opens the window in place on a page that hands the frame its window, closed until it is pressed', () => {
    const markup = renderScreen(seeded(), createElement(DocumentContext, {
      projectUid: PROJECT_UID,
      versionUid: VERSION_UID,
      current: 'version',
      pdf: { render: () => createElement('div', { 'data-drawer': '' }) },
    }));
    expect(markup).toMatch(/<button[^>]*aria-pressed="false"[^>]*data-version-pdf-toggle=""/);
    expect(markup).not.toContain('data-version-pdf-link');
    expect(markup).not.toContain('data-drawer');
  });

  it('draws the window at once when the page asks for it (`?pdf=1`), told its version, its name, its pages and how to close', () => {
    const told: unknown[] = [];
    const markup = renderScreen(seeded(), createElement(DocumentContext, {
      projectUid: PROJECT_UID,
      versionUid: VERSION_UID,
      current: 'version',
      pdf: {
        openAtStart: true,
        render: (drawer) => {
          told.push({ ...drawer, onClose: typeof drawer.onClose });
          return createElement('div', { 'data-drawer': '' });
        },
      },
    }));
    expect(markup).toContain('data-drawer');
    expect(markup).toMatch(/<button[^>]*aria-pressed="true"[^>]*data-version-pdf-toggle=""/);
    expect(told).toEqual([{ versionUid: VERSION_UID, title: 'Комплект АР · Версия 1', pageCount: 7, onClose: 'function' }]);
  });
});
