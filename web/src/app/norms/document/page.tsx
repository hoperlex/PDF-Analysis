/**
 * `/norms/document` — the route file for one norm document (`W55A-WEB-NORMS`).
 *
 * The identity is the `id` query parameter (`routes.normDocument`; why not a path segment is
 * written there). Absent, the screen says no document was chosen. Present but not an
 * `ndoc_<ULID>`, or with a `page` that is not a positive whole number, the address is a 404
 * after the guard — as a malformed project or account address is (`C-24`) — rather than a
 * screen that spends a request to report what the shape already says.
 *
 * `W50-PLAN.md` §3.2: `requireScreen` first; the registry's row is `session`, `any-role`.
 */

import { notFound } from 'next/navigation';

import { NormDocumentPage } from '@/_pages/norms';
import { looksLikeNormDocumentId, pageFromAddress } from '@/entities/norms';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function NormDocumentRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/norms/document', { params, searchParams });
  const query = searchParams === undefined ? {} : await searchParams;
  const id = query.id;
  if (id !== undefined && !looksLikeNormDocumentId(id)) notFound();
  const page = pageFromAddress(query.page);
  if (page === undefined) notFound();
  return <NormDocumentPage normDocumentId={id ?? null} page={id === undefined ? null : page} />;
}
