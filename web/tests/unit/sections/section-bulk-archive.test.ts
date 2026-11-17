/**
 * `UIP-S02-04`, `R-151a`: «В архив (N)» in the bottom bar of a section.
 *
 * The chosen documents are archived by the existing command, one document at a time, each under its own idempotency key; the bar then says
 * one thing — «Убрано в архив: k из N» — and lists the documents the server refused with the reason of each; the choice stays with those, so
 * the button retries them, under the key of the first attempt. Nothing is deleted and there is no window to confirm. The pieces are pinned
 * one by one (the pure pass, the targets, the bar over each state) and then once through the real component with the command mocked.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  setDocumentArchived: vi.fn(),
}));

import type { DocumentVersion } from '@/shared/api';
import { failureMessage, setDocumentArchived } from '@/shared/api';
import { SectionSelectionBar, SectionSelectionBarView, bulkTargets } from '@/_pages/section-detail';
import type { SectionArchiveView } from '@/_pages/section-detail';
import { archiveDocuments, archiveReportLine } from '@/features/manage-document';
import type { ArchiveReport, ArchiveTarget } from '@/features/manage-document';
import type { BatchSelection } from '@/widgets/project-sections';

import type { LiveRender } from '../analysis-settings/live-render';
import { mountLive } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { PROJECT_UID, apiError, classification, otherVersion } from './fixtures';

const inAr = (suffix: string, over: Partial<DocumentVersion> = {}): DocumentVersion =>
  otherVersion(suffix, { classification: classification({ section_code: 'AR' }), ...over });

const A = inAr('A');
const B = inAr('B');
const C = inAr('C');
const target = (version: DocumentVersion): ArchiveTarget => ({ documentUid: version.document_uid, title: version.display_title ?? '' });

// ------------------------------------------------------------------ the pass

describe('one pass over the chosen documents', () => {
  const pass = (send: (target: ArchiveTarget, key: string) => Promise<DocumentVersion>, targets = [A, B, C].map(target)) => {
    const keys = new Map<string, string>();
    const seen: Array<{ uid: string; key: string }> = [];
    const progress: string[] = [];
    return {
      keys, seen, progress,
      run: () => archiveDocuments({
        targets,
        send: async (item, key) => { seen.push({ uid: item.documentUid, key }); return send(item, key); },
        keyOf: (item) => { const key = keys.get(item.documentUid) ?? `key-${keys.size}`; keys.set(item.documentUid, key); return key; },
        reasonOf: (error) => (error instanceof Error ? error.message : 'unknown'),
        onStep: (step) => { progress.push(`${step.done}/${step.total}`); },
      }),
    };
  };

  it('sends one command per document, in the order they were chosen, each under its own key', async () => {
    const run = pass(async (item) => ({ ...A, document_uid: item.documentUid, archived_at: '2026-11-17T10:00:00Z' }));
    const report = await run.run();
    expect(run.seen.map((call) => call.uid)).toEqual([A, B, C].map((version) => version.document_uid));
    expect(new Set(run.seen.map((call) => call.key)).size).toBe(3);
    expect(report).toMatchObject({ total: 3, failed: [] });
    expect(report.archived.map((item) => item.title)).toEqual([A, B, C].map((version) => version.display_title));
    expect(run.progress).toEqual(['1/3', '2/3', '3/3']);
  });

  it('lists a refused document with its reason and goes on with the others', async () => {
    const run = pass(async (item) => {
      if (item.documentUid === B.document_uid) throw new Error('Сервер отказал.');
      return { ...A, document_uid: item.documentUid };
    });
    const report = await run.run();
    expect(run.seen).toHaveLength(3);
    expect(report.archived.map((item) => item.documentUid)).toEqual([A.document_uid, C.document_uid]);
    expect(report.failed).toEqual([{ target: target(B), reason: 'Сервер отказал.' }]);
    expect(report.total).toBe(3);
  });

  it('says each of them is in exactly one list, even when every command is refused', async () => {
    const report = await pass(async () => { throw new Error('нет'); }).run();
    expect(report.archived).toEqual([]);
    expect(report.failed).toHaveLength(3);
    expect(archiveReportLine(report)).toBe('Убрано в архив: 0 из 3');
  });

  it('sends a document named twice once, and counts it once', async () => {
    const run = pass(async (item) => ({ ...A, document_uid: item.documentUid }), [A, B, A].map(target));
    const report = await run.run();
    expect(run.seen).toHaveLength(2);
    expect(report.total).toBe(2);
  });

  it('is one sentence, «Убрано в архив: k из N»', () => {
    const report: ArchiveReport = { total: 5, archived: [A, B, C].map(target), failed: [] };
    expect(archiveReportLine(report)).toBe('Убрано в архив: 3 из 5');
  });
});

// ------------------------------------------------------------------ the targets

describe('what «В архив» acts on', () => {
  const known = new Map([A, B, C].map((version) => [version.version_uid, version] as const));

  it('is the chosen documents that are not archived yet, in the order they were chosen', () => {
    const chosen = new Set([C.version_uid, A.version_uid]);
    expect(bulkTargets(chosen, known).archivable.map((item) => item.documentUid)).toEqual([C.document_uid, A.document_uid]);
  });

  it('leaves out a document that is archived already, and a version the page never showed', () => {
    const archived = inAr('B', { archived_at: '2026-11-17T09:00:00Z' });
    const withArchived = new Map([...known, [archived.version_uid, archived] as const]);
    const chosen = new Set([A.version_uid, B.version_uid, 'ver_unknown']);
    expect(bulkTargets(chosen, withArchived).archivable.map((item) => item.documentUid)).toEqual([A.document_uid]);
    // it can fail: the same choice over the documents as the page showed them first counts B
    expect(bulkTargets(chosen, known).archivable).toHaveLength(2);
  });

  it('names a document by its card title and by its identity, which the title never replaces', () => {
    const [only] = bulkTargets(new Set([A.version_uid]), known).archivable;
    expect(only).toEqual({ documentUid: A.document_uid, title: A.display_title });
  });
});

// ------------------------------------------------------------------ the bar

describe('the bottom bar with «В архив»', () => {
  const noop = (): void => undefined;
  const chosenOf = (count: number, over: Partial<BatchSelection> = {}): BatchSelection => ({
    selection: { selected: new Set<string>(), onToggle: noop },
    chosenCount: count, batch: null, choose: noop, clear: noop, openBatch: noop, closeBatch: noop, ...over,
  });
  const archiveOf = (over: Partial<SectionArchiveView> = {}): { archive: SectionArchiveView } => ({
    archive: { count: 3, pending: false, progress: null, report: null, onArchive: noop, onDismiss: noop, ...over },
  });
  const bar = (selection: BatchSelection, bulk?: { archive: SectionArchiveView }) =>
    renderToStaticMarkup(createElement(SectionSelectionBarView, { selection, bulk }));

  it('offers «В архив (N)» between «Запустить все» and «Снять выделение», with the count of what it would send', () => {
    const markup = bar(chosenOf(5), archiveOf({ count: 4 }));
    expect(markup).toMatch(/<button type="button"[^>]*data-archive-chosen[^>]*>В архив \(4\)<\/button>/);
    expect(markup.indexOf('Запустить все')).toBeLessThan(markup.indexOf('В архив (4)'));
    expect(markup.indexOf('В архив (4)')).toBeLessThan(markup.indexOf('Снять выделение'));
    // it says what is kept before the press
    expect(markup).toContain('версии, прогоны и решения не удаляются');
  });

  it('is not offered without the actions, to a session that cannot act, nor when every chosen document is archived already', () => {
    expect(bar(chosenOf(5))).not.toContain('В архив');
    expect(bar(chosenOf(5, { selection: undefined }), archiveOf())).toBe('');
    expect(bar(chosenOf(5), archiveOf({ count: 0 }))).not.toContain('В архив');
    expect(bar(chosenOf(5), archiveOf({ count: 0 }))).toContain('Запустить все (5)');
  });

  it('holds the button while the pass runs, and says how far it has gone', () => {
    const markup = bar(chosenOf(3), archiveOf({ pending: true, progress: { done: 1, total: 3 } }));
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*data-archive-chosen[^>]*>/);
    expect(markup).toMatch(/<p[^>]*role="status"[^>]*data-archive-progress[^>]*>Убираю в архив: 1 из 3…<\/p>/);
  });

  it('says one thing at the end, and lists the refused documents with a reason each', () => {
    const report: ArchiveReport = {
      total: 3, archived: [target(A), target(C)],
      failed: [{ target: target(B), reason: 'Недостаточно прав для этого действия.' }],
    };
    const markup = bar(chosenOf(1), archiveOf({ count: 1, report }));
    expect(markup).toContain('data-archive-report="2/3"');
    expect(markup).toContain('Убрано в архив: 2 из 3');
    expect(markup).toContain(`data-archive-failed="${B.document_uid}"`);
    expect(markup).toContain('Документ B');
    expect(markup).toContain('Недостаточно прав для этого действия.');
    expect(markup).toContain('«В архив» повторит их');
    expect(markup).toContain('Версии, прогоны и решения не удалены');
    // the one message: the count of the pass is said once
    expect(markup.match(/Убрано в архив/g)).toHaveLength(1);
  });

  it('keeps the message, with a way to close it, when nothing is chosen any more', () => {
    const report: ArchiveReport = { total: 3, archived: [A, B, C].map(target), failed: [] };
    const markup = bar(chosenOf(0), archiveOf({ count: 0, report }));
    expect(markup).toContain('Убрано в архив: 3 из 3');
    expect(markup).toMatch(/<button[^>]*data-archive-dismiss[^>]*>Закрыть<\/button>/);
    expect(markup).toContain('архивные документы видны по «Показать архивные»');
    expect(markup).not.toContain('Выбрано:');
    expect(markup).not.toContain('<ul');
    // it can fail: with no message and nothing chosen there is no bar at all
    expect(bar(chosenOf(0), archiveOf({ count: 0 }))).toBe('');
  });

  it('asks nothing in a window: the action is the button, and the way back is on the document', () => {
    const markup = bar(chosenOf(2), archiveOf({ count: 2 }));
    expect(markup).not.toMatch(/<dialog|aria-modal|role="dialog"|role="alertdialog"/);
  });
});

// ------------------------------------------------------------------ through the real component, the command mocked

describe('pressing «В архив (N)»', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.mocked(setDocumentArchived).mockReset();
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const archivedAs = (version: DocumentVersion): DocumentVersion => ({ ...version, archived_at: '2026-11-17T10:00:00Z' });

  type Call = { path: { project_uid: string; document_uid: string }; body: { archived: boolean }; idempotencyKey: string };
  const calls = (): Call[] => vi.mocked(setDocumentArchived).mock.calls.map((call) => call[0] as unknown as Call);

  function chosen(versions: readonly DocumentVersion[]) {
    const choose = vi.fn();
    const clear = vi.fn();
    const selection: BatchSelection = {
      selection: { selected: new Set(versions.map((version) => version.version_uid)), onToggle: () => undefined },
      chosenCount: versions.length, batch: null, choose, clear, openBatch: () => undefined, closeBatch: () => undefined,
    };
    return { selection, choose, clear };
  }

  const bar = (selection: BatchSelection, pageDocuments: readonly DocumentVersion[] = [A, B, C]) =>
    createElement(QueryClientProvider, { client: clientOf }, createElement(SectionSelectionBar, {
      selection, scope: { projectUid: PROJECT_UID, pageDocuments, walk: { status: 'idle' } },
    }));
  let clientOf = newClient();
  beforeEach(() => { clientOf = newClient(); });

  it('sends the archive command once per document under its own key and says how many were archived', async () => {
    vi.mocked(setDocumentArchived).mockImplementation((async (input: Call) => ({
      data: archivedAs([A, B, C].find((version) => version.document_uid === input.path.document_uid) as DocumentVersion),
    })) as never);
    const { selection, clear, choose } = chosen([A, B, C]);
    live = await mountLive(bar(selection));
    expect(await live.press('В архив (3)')).toBe(true);
    expect(calls().map((call) => call.path.document_uid)).toEqual([A, B, C].map((version) => version.document_uid));
    expect(calls().every((call) => call.path.project_uid === PROJECT_UID && call.body.archived === true)).toBe(true);
    expect(new Set(calls().map((call) => call.idempotencyKey)).size).toBe(3);
    expect(live.markup()).toContain('Убрано в архив: 3 из 3');
    // nobody was refused: the choice is given back whole
    expect(clear).toHaveBeenCalledTimes(1);
    expect(choose).not.toHaveBeenCalled();
  });

  it('leaves the choice with the refused document, lists it with its reason, and a second press retries it under the first key', async () => {
    const refusal = apiError(403, 'permission_denied');
    let answer: 'refuse' | 'accept' = 'refuse';
    vi.mocked(setDocumentArchived).mockImplementation((async (input: Call) => {
      if (input.path.document_uid === B.document_uid && answer === 'refuse') throw refusal;
      return { data: archivedAs([A, B, C].find((version) => version.document_uid === input.path.document_uid) as DocumentVersion) };
    }) as never);
    const first = chosen([A, B, C]);
    live = await mountLive(bar(first.selection));
    await live.press('В архив (3)');
    expect(live.markup()).toContain('Убрано в архив: 2 из 3');
    expect(live.markup()).toContain(`data-archive-failed="${B.document_uid}"`);
    expect(live.markup()).toContain(failureMessage(refusal).detail);
    expect(first.clear).not.toHaveBeenCalled();
    expect(first.choose).toHaveBeenCalledTimes(1);
    expect((first.choose.mock.calls[0] as [DocumentVersion[]])[0].map((version) => version.version_uid)).toEqual([B.version_uid]);
    const firstKey = calls().find((call) => call.path.document_uid === B.document_uid)?.idempotencyKey;

    // the page now holds only B chosen; the same button retries exactly it
    answer = 'accept';
    const second = chosen([B]);
    await live.update(bar(second.selection));
    expect(live.markup()).toContain('В архив (1)');
    await live.press('В архив (1)');
    const retries = calls().filter((call) => call.path.document_uid === B.document_uid);
    expect(retries).toHaveLength(2);
    expect(retries[1]?.idempotencyKey).toBe(firstKey);
    expect(calls()).toHaveLength(4);
    expect(live.markup()).toContain('Убрано в архив: 1 из 1');
    expect(second.clear).toHaveBeenCalledTimes(1);

    // once archived, the intent is settled: archiving the same document again is a new command
    await live.update(bar(chosen([B]).selection));
    await live.press('В архив (1)');
    const again = calls().filter((call) => call.path.document_uid === B.document_uid);
    expect(again).toHaveLength(3);
    expect(again[2]?.idempotencyKey).not.toBe(firstKey);
  });

  it('keeps the message after the choice is cleared, until it is closed', async () => {
    vi.mocked(setDocumentArchived).mockImplementation((async (input: Call) => ({
      data: archivedAs([A, B, C].find((version) => version.document_uid === input.path.document_uid) as DocumentVersion),
    })) as never);
    live = await mountLive(bar(chosen([A, B]).selection));
    await live.press('В архив (2)');
    await live.update(bar(chosen([]).selection));
    expect(live.markup()).toContain('Убрано в архив: 2 из 2');
    expect(live.markup()).not.toContain('Выбрано:');
    expect(await live.press('Закрыть')).toBe(true);
    expect(live.markup()).toBe('');
  });

  it('sends no command for a document that is archived already, and draws no button when nothing is left to send', async () => {
    const gone = inAr('A', { archived_at: '2026-11-16T10:00:00Z' });
    live = await mountLive(bar(chosen([gone]).selection, [gone, B, C]));
    expect(live.markup()).toContain('Запустить все (1)');
    expect(live.markup()).not.toContain('В архив');
    expect(setDocumentArchived).not.toHaveBeenCalled();
  });

  it('does not send a second pass while the first is running', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    vi.mocked(setDocumentArchived).mockImplementation((async (input: Call) => {
      await gate;
      return { data: archivedAs([A, B, C].find((version) => version.document_uid === input.path.document_uid) as DocumentVersion) };
    }) as never);
    live = await mountLive(bar(chosen([A, B]).selection));
    expect(await live.pressRepeatedly('В архив (2)', 2)).toBe(true);
    expect(live.markup()).toContain('Убираю в архив');
    expect(calls()).toHaveLength(1);
    await live.settle(async () => { release(); await gate; });
    expect(calls()).toHaveLength(2);
    expect(live.markup()).toContain('Убрано в архив: 2 из 2');
  });
});
