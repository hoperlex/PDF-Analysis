/**
 * `classifyDocumentVersion` as the feature sends it (`W59-SECTION-UI-01`): one `PUT` with
 * the expert's stage and section at the version's three-identity address, and the reads it
 * tells afterwards — the review, the version, the document's version list, the project
 * structure and the dashboard on success; the review and the version on a `409`, so the
 * stored classification is read back.
 *
 * The mutation hook is exercised through its configuration, the way the execution commands'
 * suite does: `useMutation` is replaced by the identity, so the test holds the very
 * `mutationFn`, `onSuccess` and `onError` the browser would run.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({
  invalidations: [] as unknown[],
  writes: [] as { key: unknown; next: unknown }[],
  seeded: new Map<string, unknown>(),
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    setQueryData: (key: unknown, updater: (old: unknown) => unknown) => {
      const next = updater(calls.seeded.get(JSON.stringify(key)));
      calls.writes.push({ key, next });
    },
    invalidateQueries: (...args: unknown[]) => {
      calls.invalidations.push(args);
      return Promise.resolve();
    },
  }),
}));

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, classifyDocumentVersion: vi.fn() };
});

import type { VersionClassification } from '@/shared/api';
import { classifyDocumentVersion, queryKeys } from '@/shared/api';
import { VERSION_PAGE_LIMIT } from '@/entities/document-version';
import type { ClassifyVersionCommand } from '@/features/classify-version';
import { useClassifyVersion } from '@/features/classify-version';

import { ADDRESS, DOCUMENT_UID, VERSION_UID, apiError, classification, review, version } from './fixtures';

type Captured = {
  mutationFn: (input: ClassifyVersionCommand) => Promise<VersionClassification>;
  onSuccess: (result: VersionClassification, input: ClassifyVersionCommand) => void;
  onError: (error: unknown, input: ClassifyVersionCommand) => void;
  retry: boolean;
};

const COMMAND: ClassifyVersionCommand = { ...ADDRESS, stage: 'P', section: 'AR' };

beforeEach(() => {
  calls.invalidations.length = 0;
  calls.writes.length = 0;
  calls.seeded.clear();
  vi.clearAllMocks();
});

describe('the classification command', () => {
  it('sends one PUT with the stage and section at the version’s own address, and never retries', async () => {
    vi.mocked(classifyDocumentVersion).mockResolvedValue({ data: classification() } as never);
    const command = useClassifyVersion() as unknown as Captured;
    expect(command.retry).toBe(false);
    const answer = await command.mutationFn(COMMAND);
    expect(answer).toEqual(classification());
    expect(vi.mocked(classifyDocumentVersion).mock.calls).toEqual([
      [
        {
          path: {
            project_uid: ADDRESS.projectUid,
            document_uid: ADDRESS.documentUid,
            version_uid: ADDRESS.versionUid,
          },
          body: { project_stage: 'P', section_code: 'AR' },
        },
      ],
    ]);
  });

  it('writes the answer into the review and the version, and tells every read that shows it', () => {
    calls.seeded.set(JSON.stringify(queryKeys.versions.sectionReview(VERSION_UID)), review());
    calls.seeded.set(JSON.stringify(queryKeys.versions.detail(VERSION_UID)), version());
    const command = useClassifyVersion() as unknown as Captured;
    command.onSuccess(classification(), COMMAND);

    const written = new Map(calls.writes.map(({ key, next }) => [JSON.stringify(key), next]));
    expect(
      (written.get(JSON.stringify(queryKeys.versions.sectionReview(VERSION_UID))) as { classification: unknown })
        .classification,
    ).toEqual(classification());
    expect(
      (written.get(JSON.stringify(queryKeys.versions.detail(VERSION_UID))) as { classification: unknown })
        .classification,
    ).toEqual(classification());

    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.versions.sectionReview(VERSION_UID) }]);
    expect(calls.invalidations).toContainEqual([
      { queryKey: queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT) },
    ]);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.projects.all() }]);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.dashboard.summary() }]);
  });

  it('writes nothing it was not holding: an empty cache stays empty', () => {
    const command = useClassifyVersion() as unknown as Captured;
    command.onSuccess(classification(), COMMAND);
    expect(calls.writes.every(({ next }) => next === undefined)).toBe(true);
  });

  it('on 409 version_already_classified, reads the stored classification back', () => {
    const command = useClassifyVersion() as unknown as Captured;
    command.onError(apiError(409, 'conflict', { conflict_reason: 'version_already_classified' }), COMMAND);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.versions.sectionReview(VERSION_UID) }],
      [{ queryKey: queryKeys.versions.detail(VERSION_UID) }],
    ]);
  });

  it('on 403 or any other refusal, changes no cache at all', () => {
    const command = useClassifyVersion() as unknown as Captured;
    command.onError(apiError(403, 'permission_denied'), COMMAND);
    command.onError(apiError(503, 'dependency_unavailable'), COMMAND);
    expect(calls.invalidations).toEqual([]);
    expect(calls.writes).toEqual([]);
  });
});
