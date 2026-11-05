'use client';

/**
 * `R-150c`, `UI-PARITY-01` project context: on a screen that follows the header (class `optional`) the
 * project lives in the address. This hook reads `?project=` and writes it back through `switchProject`,
 * which also drops the parameters that only meant something inside the old project. Outside the app
 * router both navigation hooks answer `null`: no project, and a change written onto `fallbackPath`.
 */

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { PROJECT_PARAM, switchProject } from '@/shared/lib';

const NO_PARAMS = new URLSearchParams();

export function useAddressProject(fallbackPath: string): readonly [string | null, (projectUid: string | null) => void] {
  const router = useRouter();
  const pathname = usePathname() ?? fallbackPath;
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const projectUid = searchParams.get(PROJECT_PARAM);
  const choose = (next: string | null) => {
    const query = switchProject(searchParams, next).toString();
    router.replace(query === '' ? pathname : `${pathname}?${query}`, { scroll: false });
  };
  return [projectUid === '' ? null : projectUid, choose] as const;
}
