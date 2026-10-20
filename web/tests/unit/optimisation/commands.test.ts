/**
 * The price-list upload and the two vendor-list commands as the features send them
 * (`W60-PRICE-LIST-01`): the multipart body with or without a default currency, the expected
 * revision on every vendor-list write, and the reads each one tells afterwards — never the
 * dashboard, whose numbers none of them changes.
 *
 * The hooks are exercised through their configuration, as `version-upload-command.test.ts`
 * does: `useMutation` is replaced by the identity, so the test holds the very `mutationFn`,
 * `onSuccess` and `onSettled` the browser would run.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: (configuration: unknown) => configuration,
    useQueryClient: () => ({
      invalidateQueries: (...args: unknown[]) => {
        calls.invalidations.push(args);
        return Promise.resolve();
      },
    }),
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    uploadPriceList: vi.fn(),
    setProjectVendorList: vi.fn(),
    setGlobalVendorList: vi.fn(),
  };
});

import type { PriceListRevision, SectionVendorList, VendorListRevision } from '@/shared/api';
import { queryKeys, setGlobalVendorList, setProjectVendorList, uploadPriceList } from '@/shared/api';
import type { UploadPriceListCommand } from '@/features/upload-price-list';
import { useUploadPriceList } from '@/features/upload-price-list';
import type { SetGlobalVendorListCommand, SetProjectVendorListCommand } from '@/features/set-vendor-list';
import { useSetGlobalVendorList, useSetProjectVendorList } from '@/features/set-vendor-list';

import { OPT_PROJECT_UID, revision } from './fixtures';

type Captured<I, R> = {
  mutationFn: (input: I) => Promise<R>;
  onSuccess?: (result: R, input: I) => void;
  onSettled?: () => void;
};

function file(): File {
  return new File(['Наименование;Ед. изм.;Цена\n'], 'прайс.csv', { type: 'text/csv' });
}

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
});

describe('the price-list upload', () => {
  it('sends the file and the declared currency under the caller’s key', async () => {
    vi.mocked(uploadPriceList).mockResolvedValue({ data: revision() } as never);
    const hook = useUploadPriceList() as unknown as Captured<UploadPriceListCommand, PriceListRevision>;
    const chosen = file();
    await hook.mutationFn({ projectUid: OPT_PROJECT_UID, file: chosen, defaultCurrency: 'RUB', idempotencyKey: 'intent-1' });
    expect(vi.mocked(uploadPriceList)).toHaveBeenCalledWith({
      path: { project_uid: OPT_PROJECT_UID },
      body: { file: chosen, default_currency: 'RUB' },
      idempotencyKey: 'intent-1',
    });
  });

  it('omits the currency part entirely when none was chosen', async () => {
    vi.mocked(uploadPriceList).mockResolvedValue({ data: revision() } as never);
    const hook = useUploadPriceList() as unknown as Captured<UploadPriceListCommand, PriceListRevision>;
    const chosen = file();
    await hook.mutationFn({ projectUid: OPT_PROJECT_UID, file: chosen, defaultCurrency: null, idempotencyKey: 'intent-2' });
    const sent = vi.mocked(uploadPriceList).mock.calls[0]?.[0];
    expect(sent?.body).toEqual({ file: chosen });
    expect(Object.keys(sent?.body ?? {})).toEqual(['file']);
  });

  it('asks the project’s revisions again, and not the dashboard', () => {
    const hook = useUploadPriceList() as unknown as Captured<UploadPriceListCommand, PriceListRevision>;
    hook.onSuccess?.(revision(), {} as UploadPriceListCommand);
    expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.optimisation.priceLists(OPT_PROJECT_UID) }]]);
  });
});

describe('the vendor-list commands', () => {
  it('send the whole list with the revision the screen showed', async () => {
    vi.mocked(setProjectVendorList).mockResolvedValue({ data: {} } as never);
    vi.mocked(setGlobalVendorList).mockResolvedValue({ data: {} } as never);
    const project = useSetProjectVendorList() as unknown as Captured<SetProjectVendorListCommand, SectionVendorList>;
    const global = useSetGlobalVendorList() as unknown as Captured<SetGlobalVendorListCommand, VendorListRevision>;
    const entries = [{ material: 'Кабель', vendor: 'Завод', note: null }];
    await project.mutationFn({
      projectUid: OPT_PROJECT_UID, sectionCode: 'EOM', mode: 'list', entries,
      expectedVendorListId: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8K',
    });
    await global.mutationFn({ sectionCode: 'OV', entries: [], expectedVendorListId: null });
    expect(vi.mocked(setProjectVendorList)).toHaveBeenCalledWith({
      path: { project_uid: OPT_PROJECT_UID, section_code: 'EOM' },
      body: { mode: 'list', entries, expected_vendor_list_id: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8K' },
    });
    expect(vi.mocked(setGlobalVendorList)).toHaveBeenCalledWith({
      path: { section_code: 'OV' },
      body: { entries: [], expected_vendor_list_id: null },
    });
  });

  it('ask every project’s vendor lists again however they settle', () => {
    (useSetProjectVendorList() as unknown as Captured<never, never>).onSettled?.();
    (useSetGlobalVendorList() as unknown as Captured<never, never>).onSettled?.();
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.optimisation.vendorLists() }],
      [{ queryKey: queryKeys.optimisation.vendorLists() }],
    ]);
  });
});
