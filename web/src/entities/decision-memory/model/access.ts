/**
 * Who sees the decision memory (`D-495`, `DECISION-MEMORY-01` section 8, contract 1.44.0).
 *
 * The reads are the expert's and the administrator's; the viewer never reads the memory. The standing changes and the status
 * read are the administrator's. The server decides again on every call: this only stops the screen offering what would be
 * refused, and it does so by HIDING, never by disabling. While the account is not known (loading, or its read failed) neither
 * is offered: unlike the expert's actions (`mayActAsExpert`), a memory that flashed on for a viewer would have shown a
 * viewer something he may not read.
 */

import { useMe } from '@/entities/account';

export interface MemoryAccess {
  /** The account is known; before that nothing of the memory is drawn. */
  readonly known: boolean;
  /** The list and the case view: `expert` or `admin`. */
  readonly read: boolean;
  /** «Отозвать», «Вернуть» and the status line: `admin`. */
  readonly manage: boolean;
}

export function memoryAccessOf(roles: readonly string[] | undefined): MemoryAccess {
  if (roles === undefined) return { known: false, read: false, manage: false };
  return { known: true, read: roles.includes('expert') || roles.includes('admin'), manage: roles.includes('admin') };
}

export function useMemoryAccess(): MemoryAccess {
  const me = useMe();
  // An account read that failed cannot confirm the role: the memory stays hidden, and does not wait for it for ever.
  if (me.isError) return { known: true, read: false, manage: false };
  return memoryAccessOf(me.data?.roles);
}
