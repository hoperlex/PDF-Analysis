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
}));

import type { DocumentUid } from '@/shared/api';
import { uploadDocument, uploadDocumentVersion } from '@/shared/api';
import { precheckUploadFile } from '@/entities/document-version';
import type { ManyFile } from '@/features/upload-document';
import { NEW_DOCUMENT, UploadManyView, sendable, targetOf, targetValue, useUploadMany } from '@/features/upload-document';

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
    expect(markup).toContain('первые документы проекта');
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
