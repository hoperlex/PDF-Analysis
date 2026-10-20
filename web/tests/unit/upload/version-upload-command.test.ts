/**
 * `uploadDocumentVersion` as the feature sends it (`W59-VERSION-UPLOAD-01`): one multipart
 * `POST` of the bundle alone at the document's address under the caller's key, and the reads
 * it tells afterwards — the new version written into its own key, every page of the
 * document's version list, the project's reads (its document list and structure, its detail,
 * the listing) and the dashboard.
 *
 * The hook is exercised through its configuration, the way `classify-command.test.ts` does:
 * `useMutation` is replaced by the identity, so the test holds the very `mutationFn` and
 * `onSuccess` the browser would run.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({
  invalidations: [] as unknown[],
  writes: [] as { key: unknown; value: unknown }[],
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    setQueryData: (key: unknown, value: unknown) => {
      calls.writes.push({ key, value });
    },
    invalidateQueries: (...args: unknown[]) => {
      calls.invalidations.push(args);
      return Promise.resolve();
    },
  }),
}));

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, uploadDocumentVersion: vi.fn() };
});

import type * as ReactQuery from '@tanstack/react-query';

import type { DocumentVersion } from '@/shared/api';
import { queryKeys, uploadDocumentVersion } from '@/shared/api';
import { VERSION_PAGE_LIMIT } from '@/entities/document-version';
import type { UploadDocumentVersionCommand } from '@/features/upload-document';
import { useUploadDocumentVersion } from '@/features/upload-document';

const PROJECT_UID = 'prj_01M2545JSD15ETSNNV904X991F';
const DOCUMENT_UID = 'doc_01M2545JSD15ETSNNV904X991H';
const NEW_VERSION_UID = 'ver_01M2545JSD15ETSNNV904X991K';

type Captured = {
  mutationFn: (input: UploadDocumentVersionCommand) => Promise<DocumentVersion>;
  onSuccess: (result: DocumentVersion, input: UploadDocumentVersionCommand) => void;
};

const NEW_VERSION = {
  version_uid: NEW_VERSION_UID,
  document_uid: DOCUMENT_UID,
  project_uid: PROJECT_UID,
  version_ordinal: 2,
} as unknown as DocumentVersion;

function command(): UploadDocumentVersionCommand {
  return {
    projectUid: PROJECT_UID,
    documentUid: DOCUMENT_UID,
    file: new File([new Uint8Array([0x50, 0x4b, 3, 4])], 'комплект.zip', { type: 'application/zip' }),
    idempotencyKey: 'intent-1',
  };
}

beforeEach(() => {
  calls.invalidations.length = 0;
  calls.writes.length = 0;
  vi.clearAllMocks();
});

describe('the next-version upload command', () => {
  it('sends the bundle alone to the document’s address, under the caller’s key', async () => {
    vi.mocked(uploadDocumentVersion).mockResolvedValue({ data: NEW_VERSION } as never);
    const hook = useUploadDocumentVersion() as unknown as Captured;
    const input = command();

    const answer = await hook.mutationFn(input);

    expect(answer).toEqual(NEW_VERSION);
    expect(vi.mocked(uploadDocumentVersion).mock.calls).toEqual([
      [
        {
          path: { project_uid: PROJECT_UID, document_uid: DOCUMENT_UID },
          // No title and no section: a further version takes neither.
          body: { file: input.file },
          idempotencyKey: 'intent-1',
        },
      ],
    ]);
  });

  it('writes the new version and asks again for every read it changed', () => {
    const hook = useUploadDocumentVersion() as unknown as Captured;
    hook.onSuccess(NEW_VERSION, command());

    expect(calls.writes).toEqual([
      { key: queryKeys.versions.detail(NEW_VERSION_UID), value: NEW_VERSION },
    ]);
    const keys = calls.invalidations.map((args) => (args as [{ queryKey: unknown }])[0].queryKey);
    expect(keys).toEqual([
      queryKeys.versions.lists(DOCUMENT_UID),
      queryKeys.projects.all(),
      queryKeys.dashboard.summary(),
    ]);
  });

  it('reaches the version list the screens hold, and the project document list and structure', async () => {
    // Prefix matching, as TanStack Query applies it (the real `matchQuery`, not the mock
    // above): the invalidated key must cover the keys the screens read, whatever cursor.
    const { matchQuery } = await vi.importActual<typeof ReactQuery>('@tanstack/react-query');
    const listFilter = { queryKey: queryKeys.versions.lists(DOCUMENT_UID) };
    const projectsFilter = { queryKey: queryKeys.projects.all() };
    const query = (queryKey: readonly unknown[]) =>
      ({ queryKey, queryHash: JSON.stringify(queryKey) }) as never;
    expect(matchQuery(listFilter, query(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT)))).toBe(true);
    expect(matchQuery(listFilter, query(queryKeys.versions.list(DOCUMENT_UID, 'cursor-2', VERSION_PAGE_LIMIT)))).toBe(true);
    expect(
      matchQuery(listFilter, query(queryKeys.versions.list('doc_01M2545JSD15ETSNNV904X991Z', undefined, VERSION_PAGE_LIMIT))),
    ).toBe(false);
    expect(matchQuery(projectsFilter, query(queryKeys.projects.documents(PROJECT_UID)))).toBe(true);
    expect(matchQuery(projectsFilter, query(queryKeys.projects.detail(PROJECT_UID)))).toBe(true);
  });
});
