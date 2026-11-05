'use client';

/**
 * `R-150e`: may this account take an expert's action on product data -- create a project, upload,
 * start a run, record a decision?
 *
 * The server is the only authority: every such operation refuses an account without `expert`. The
 * screens only stop offering what would be refused. While the account is not known yet (loading, or
 * its read failed), the actions stay drawn and the operations answer for themselves, as the
 * comparison screens already do; once it is known and holds no `expert` -- «Наблюдатель», or an
 * administrator alone -- they are hidden.
 */

import { useMe } from './use-me';

export function mayActAsExpert(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert');
}

export function useMayActAsExpert(): boolean {
  const me = useMe();
  return mayActAsExpert(me.data?.roles);
}
