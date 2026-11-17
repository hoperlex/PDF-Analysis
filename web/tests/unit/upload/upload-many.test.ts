/**
 * Several files at once, each to its explicit target (`R-151b`).
 *
 * The owner ruled that the file name never chooses the target, not even as a suggestion: every file starts at
 * «Новый документ», and a file sent to an existing document goes as that document's next version. These cases pin
 * the default, the two commands each target sends, one key per file, and that a file the browser already refused
 * is listed with its reason and never sent.
 */

import { createElement, useEffect, useRef } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  uploadDocument: vi.fn(),
  uploadDocumentVersion: vi.fn(),
  // The panel reads the project's documents for the «Куда» list; an empty first page keeps the mount free of the network.
  listDocuments: vi.fn(async () => ({ data: { items: [], page: { next_cursor: null } } })),
}));

/**
 * The field's drop zone, replaced by one that hands its props to the test: the suite has no DOM to drop on, so what a drop DOES is
 * reached by calling the `onFiles` the form gave the zone, and what the zone does with a drop (`filesOfDrop`, `DropZoneView`) is
 * tested on its own below.
 */
const zone = vi.hoisted(() => ({
  props: null as null | { readonly onFiles: (files: readonly File[]) => void; readonly several: boolean },
}));
vi.mock('@/features/upload-document/ui/drop-zone', async (importOriginal) => {
  const { createElement: element } = await import('react');
  return {
    ...await importOriginal<Record<string, unknown>>(),
    DropZone: (props: { readonly onFiles: (files: readonly File[]) => void; readonly several: boolean; readonly children: unknown }) => {
      zone.props = props;
      return element('div', { 'data-stub-drop-zone': '' }, props.children as never);
    },
  };
});

import type { DocumentUid } from '@/shared/api';
import { queryKeys, uploadDocument, uploadDocumentVersion } from '@/shared/api';
import { precheckUploadFile } from '@/entities/document-version';
import type { DropTransfer, ManyFile } from '@/features/upload-document';
import {
  DropZoneView, FOLDER_NOT_TAKEN, NEW_DOCUMENT, ONE_ARCHIVE_ONLY, UploadDocumentForm, UploadManyForm, UploadManyView,
  carriesFiles, filesOfDrop, sendable, showChosen, targetOf, targetValue, useUploadMany,
} from '@/features/upload-document';
import { UploadPanel } from '@/widgets/upload-panel';

import type { LiveRender } from '../analysis-settings/live-render';
import { mountLive } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { version } from '../sections/fixtures';

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const DOCUMENT = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8D' as DocumentUid;

const zip = (name: string, size = 10): File => new File([new Uint8Array(size)], name, { type: 'application/zip', lastModified: 1 });
const item = (id: string, file: File, target = NEW_DOCUMENT): ManyFile => ({ id, file, precheck: precheckUploadFile(file), target });

describe('the choice', () => {
  it('starts every file at «Новый документ», whatever its name says', () => {
    const named = item('0', zip('АР_V2.zip'));
    expect(named.target).toEqual(NEW_DOCUMENT);
    expect(targetValue(NEW_DOCUMENT)).toBe('');
    expect(targetOf('')).toEqual(NEW_DOCUMENT);
    expect(targetOf(DOCUMENT)).toEqual({ kind: 'version', documentUid: DOCUMENT });
  });

  it('never sends a file the browser already refused', () => {
    const files = [item('0', zip('a.zip')), item('1', new File(['x'], 'b.txt', { type: 'text/plain' }))];
    expect(files[1]?.precheck).not.toBeNull();
    expect(sendable(files, new Map()).map((file) => file.id)).toEqual(['0']);
  });

  it('lists each file with its target and the refused one with its reason', () => {
    const files = [item('0', zip('a.zip')), item('1', new File(['x'], 'b.txt', { type: 'text/plain' }))];
    const markup = renderToStaticMarkup(createElement(UploadManyView, {
      projectUid: PROJECT, files, outcomes: new Map(), documents: [{ documentUid: DOCUMENT, title: 'Архитектурные решения' }],
      documentsPartial: true, sending: false, onChoose: () => {}, onTarget: () => {}, onSend: () => {},
    }));
    expect(markup).toContain('Новая версия: Архитектурные решения');
    expect(markup).toContain('не будет загружен:');
    expect(markup).toContain('Загрузить 1');
    expect(markup).toContain('первые документы объекта');
  });
});

describe('sending', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.mocked(uploadDocument).mockReset();
    vi.mocked(uploadDocumentVersion).mockReset();
    vi.mocked(uploadDocument).mockResolvedValue({ data: version({ version_ordinal: 1 }) } as never);
    vi.mocked(uploadDocumentVersion).mockResolvedValue({ data: version({ version_ordinal: 2, document_uid: DOCUMENT }) } as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  function Harness({ files }: { readonly files: readonly ManyFile[] }) {
    const upload = useUploadMany(PROJECT);
    const sent = useRef(false);
    useEffect(() => {
      if (sent.current) return;
      sent.current = true;
      void upload.send(files);
    }, [upload, files]);
    return createElement('pre', null, [...upload.outcomes.entries()].map(([id, outcome]) => `${id}:${outcome.kind}`).join(' '));
  }

  it('sends a new document as uploadDocument and a version as uploadDocumentVersion, one key each', async () => {
    const files = [item('0', zip('a.zip')), item('1', zip('b.zip'), { kind: 'version', documentUid: DOCUMENT })];
    live = await mountLive(createElement(QueryClientProvider, { client: newClient() }, createElement(Harness, { files })));
    await live.settle(async () => {});
    expect(vi.mocked(uploadDocument)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(uploadDocumentVersion)).toHaveBeenCalledTimes(1);
    const versionCall = vi.mocked(uploadDocumentVersion).mock.calls[0]![0] as { path: { document_uid: string }; idempotencyKey: string };
    const documentCall = vi.mocked(uploadDocument).mock.calls[0]![0] as { idempotencyKey: string };
    expect(versionCall.path.document_uid).toBe(DOCUMENT);
    expect(versionCall.idempotencyKey).not.toBe(documentCall.idempotencyKey);
    expect(live.markup()).toContain('0:published 1:published');
  });
});

/**
 * A ZIP dropped on the field of the single form (`UIP-S22-03`): one file is chosen as the picker would choose it, several open
 * «Несколько файлов», a folder is not taken, and a drag of anything but files is not welcome.
 */
describe('a drop on the file field', () => {
  const entry = (file: File, directory = false) => ({
    kind: 'file', getAsFile: () => (directory ? null : file), webkitGetAsEntry: () => ({ isDirectory: directory }),
  });
  const transfer = (items: ReturnType<typeof entry>[], types: string[] = ['Files']): DropTransfer => ({
    types, files: items.flatMap((one) => (one.getAsFile() === null ? [] : [one.getAsFile() as File])), items,
  });

  it('takes the files of a drop, one or several, in the order dropped', () => {
    const [a, b] = [zip('a.zip'), zip('b.zip')];
    expect(filesOfDrop(transfer([entry(a)]))).toEqual({ files: [a], folders: 0 });
    expect(filesOfDrop(transfer([entry(a), entry(b)])).files).toEqual([a, b]);
  });

  it('does not take a folder, and counts it so the screen can say so', () => {
    const a = zip('a.zip');
    expect(filesOfDrop(transfer([entry(zip('Папка'), true)]))).toEqual({ files: [], folders: 1 });
    expect(filesOfDrop(transfer([entry(zip('Папка'), true), entry(a)]))).toEqual({ files: [a], folders: 1 });
  });

  it('reads the plain file list when the browser shows no item list', () => {
    const a = zip('a.zip');
    expect(filesOfDrop({ types: ['Files'], files: [a] })).toEqual({ files: [a], folders: 0 });
    expect(filesOfDrop({ types: ['Files'], files: [a], items: [] })).toEqual({ files: [a], folders: 0 });
  });

  it('welcomes a drag that carries files and leaves any other drag to the browser', () => {
    expect(carriesFiles({ types: ['Files'] })).toBe(true);
    expect(carriesFiles({ types: ['text/plain', 'Files'] })).toBe(true);
    expect(carriesFiles({ types: ['text/plain'] })).toBe(false);
    expect(carriesFiles({ types: [] })).toBe(false);
  });

  it('draws the highlight only while a drag is over, and says what a drop left out', () => {
    const view = (over: boolean, note: 'folder' | 'one-only' | null) => renderToStaticMarkup(
      createElement(DropZoneView, { over, note }, createElement('input', { type: 'file' })),
    );
    expect(view(false, null)).toContain('data-drop-zone=""');
    expect(view(false, null)).not.toContain('data-drop-zone="over"');
    expect(view(true, null)).toContain('data-drop-zone="over"');
    expect(view(true, null).match(/class="([^"]*)"/)?.[1]?.split(' ')).toHaveLength(2);
    expect(view(false, null)).not.toContain('role="alert"');
    expect(view(false, 'folder')).toContain(FOLDER_NOT_TAKEN);
    expect(view(false, 'one-only')).toContain(ONE_ARCHIVE_ONLY);
  });

  it('puts the dropped file into the native field when the browser can, and leaves it alone when not', () => {
    const file = zip('a.zip');
    const field: { files: unknown } = { files: null };
    const added: File[] = [];
    vi.stubGlobal('DataTransfer', class {
      readonly items = { add: (one: File) => { added.push(one); } };
      get files() { return { held: added.slice() }; }
    });
    try {
      showChosen(field as never, file);
      expect(added).toEqual([file]);
      expect(field.files).toEqual({ held: [file] });
    } finally {
      vi.unstubAllGlobals();
    }
    const untouched: { files: unknown } = { files: 'as it was' };
    showChosen(untouched as never, file);
    expect(untouched.files).toBe('as it was');
    expect(() => showChosen(null, file)).not.toThrow();
  });
});

describe('what a drop does', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    zone.props = null;
    // The earlier cases leave calls on these: a drop must send nothing, so the count starts from nothing.
    vi.mocked(uploadDocument).mockReset();
    vi.mocked(uploadDocumentVersion).mockReset();
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const withClient = (element: ReturnType<typeof createElement>, expert = false) => {
    const client = newClient();
    if (expert) client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    return createElement(QueryClientProvider, { client }, element);
  };
  const droppedOnField = async (files: File[]) => {
    await live?.settle(() => zone.props?.onFiles(files));
  };

  it('chooses one dropped ZIP exactly as the picker would, and sends nothing by itself', async () => {
    live = await mountLive(withClient(createElement(UploadDocumentForm, { projectUid: PROJECT })));
    expect(live.markup()).not.toContain('Выбран файл');
    await droppedOnField([zip('a.zip', 2048)]);
    expect(live.markup()).toContain('Выбран файл: a.zip');
    expect(live.markup()).not.toMatch(/<button[^>]*disabled=""[^>]*>Загрузить<\/button>/);
    expect(live.markup()).not.toContain('data-precheck-problem');
    expect(vi.mocked(uploadDocument)).not.toHaveBeenCalled();
  });

  it('runs the browser checks on a dropped file: a file that is not a ZIP is refused and cannot be sent', async () => {
    live = await mountLive(withClient(createElement(UploadDocumentForm, { projectUid: PROJECT })));
    await droppedOnField([new File(['x'], 'b.txt', { type: 'text/plain' })]);
    expect(live.markup()).toContain('data-precheck-problem');
    expect(live.markup()).toMatch(/<button[^>]*disabled=""[^>]*>Загрузить<\/button>/);
  });

  it('hands several dropped files to the caller and keeps the single field as it was', async () => {
    const handed: (readonly File[])[] = [];
    live = await mountLive(withClient(createElement(UploadDocumentForm, { projectUid: PROJECT, onDropMany: (files) => { handed.push(files); } })));
    expect(zone.props?.several).toBe(true);
    const [a, b] = [zip('a.zip'), zip('b.zip')];
    await droppedOnField([a, b]);
    expect(handed).toEqual([[a, b]]);
    expect(live.markup()).not.toContain('Выбран файл');
  });

  it('takes one archive only where nothing takes several', async () => {
    live = await mountLive(withClient(createElement(UploadDocumentForm, { projectUid: PROJECT })));
    expect(zone.props?.several).toBe(false);
  });

  it('lists the dropped files in «Несколько файлов» with the same browser checks', async () => {
    const files = [zip('a.zip'), new File(['x'], 'b.txt', { type: 'text/plain' })];
    live = await mountLive(withClient(createElement(UploadManyForm, {
      projectUid: PROJECT, documents: [], documentsPartial: false, dropped: { id: 1, files },
    })));
    expect(live.markup()).toContain('data-upload-many="2"');
    expect(live.markup()).toContain('a.zip');
    expect(live.markup()).toContain('не будет загружен:');
    expect(live.markup()).toContain('Загрузить 1');
  });

  it('opens «Несколько файлов» on a drop of several and shows them there; a drop of one leaves it as it was', async () => {
    live = await mountLive(withClient(createElement(UploadPanel, { projectUid: PROJECT }), true));
    await live.settle(async () => {});
    expect(live.markup()).toContain('data-upload-many-panel=""');
    expect(live.markup()).not.toMatch(/data-upload-many-panel="" open=""/);
    expect(live.markup()).toContain('data-upload-many="0"');
    await droppedOnField([zip('a.zip')]);
    expect(live.markup()).not.toMatch(/data-upload-many-panel="" open=""/);
    expect(live.markup()).toContain('Выбран файл: a.zip');
    await droppedOnField([zip('b.zip'), zip('c.zip')]);
    expect(live.markup()).toMatch(/data-upload-many-panel="" open=""/);
    expect(live.markup()).toContain('data-upload-many="2"');
    expect(live.markup()).toContain('b.zip');
    expect(live.markup()).toContain('c.zip');
  });
});
