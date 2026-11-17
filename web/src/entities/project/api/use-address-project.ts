'use client';

/**
 * `R-150c`, `UI-PARITY-01` project context, `UIP-G-06`: the object a screen that follows the header (class `optional`) works in.
 *
 * {@link useCurrentProject} reads it: the address first (`?project=<uid>`, `?project=all`, the path on a `required` screen),
 * and where the address names none, the object the account chose last (`getMe`'s `last_project_uid`; the order is
 * `resolveProjectContext`'s). {@link useAddressProject} adds the write: a choice goes back through `switchProject`, which
 * also drops the parameters that only meant something inside the old object, and a choice of one object is kept on the
 * server (`setMyLastProject`), so the screens open on it next time. «Все объекты» is `?project=all` and is not kept.
 *
 * The account is read only where it can matter: on an `optional` screen whose address names no object (the same `getMe` query
 * the other readers of the account share). Outside the app router both navigation hooks answer `null`: the address is then
 * no address, and `fallbackPath` stands in for the screen's own, so the class is known and a write lands on it.
 *
 * **While `getMe` is on its way the screen has no last object yet** (`pending`): it is drawn for «Все объекты» and moves to
 * the account's object when the answer comes. A screen that must not ask twice for what it will not show reads `pending`.
 */

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { projectScopeOf, readProjectContext, resolveProjectContext, switchProject } from '@/shared/lib';
import type { ProjectSource } from '@/shared/lib';
import { useLastProject, useRememberProject } from '@/entities/account';
import type { RememberProjectFailure } from '@/entities/account';

const NO_PARAMS = new URLSearchParams();

export interface CurrentProject {
  /** The object's uid; `null` for «Все объекты». */
  readonly projectUid: string | null;
  /** Where it came from: `path`, `query`, `all` (chosen), `remembered` (the account's last object), `none`. */
  readonly source: ProjectSource;
  /** The address names no object and `getMe` has not answered: `remembered` may still arrive. */
  readonly pending: boolean;
}

export function useCurrentProject(fallbackPath: string): CurrentProject {
  const pathname = usePathname() ?? fallbackPath;
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const fromAddress = readProjectContext(pathname, searchParams);
  // Only a screen that follows the object, and whose address is silent, needs the account's answer.
  const needsAccount = fromAddress.source === 'none' && projectScopeOf(pathname) === 'optional';
  const last = useLastProject({ enabled: needsAccount });
  const context = resolveProjectContext(pathname, searchParams, last.projectUid);
  return { projectUid: context.projectUid, source: context.source, pending: needsAccount && last.pending };
}

/**
 * The object, a way to choose another, and the refusal of the last choice's keeping (`null` when there is none). The choice
 * stands whatever the server says; the screen that draws the chooser must say the refusal beside it.
 */
export function useAddressProject(
  fallbackPath: string,
): readonly [string | null, (projectUid: string | null) => void, RememberProjectFailure | null] {
  const router = useRouter();
  const pathname = usePathname() ?? fallbackPath;
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const current = useCurrentProject(fallbackPath);
  const { remember, failure } = useRememberProject();
  const choose = (next: string | null) => {
    const query = switchProject(searchParams, next, current.projectUid).toString();
    router.replace(query === '' ? pathname : `${pathname}?${query}`, { scroll: false });
    // The address already holds the choice; keeping it for next time is the server's, and a refusal comes back as `failure`.
    if (next !== null && next !== '' && next !== current.projectUid) remember(next);
  };
  return [current.projectUid, choose, failure] as const;
}
