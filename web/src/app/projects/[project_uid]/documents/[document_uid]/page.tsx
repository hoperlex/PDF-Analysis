/**
 * `/projects/{project_uid}/documents/{document_uid}` — one document and its versions.
 *
 * Delegation-only. See the note in `/projects/page.tsx` for why these three routes were
 * wired by the integrator rather than by the session that wrote the screens.
 *
 * **The shape of every dynamic segment is checked here, and a malformed one is a 404.**
 * `D-28`: a dynamic segment matches any string, so before this an unrouted project path
 * answered **200** and rendered the screen in an error state. The consequence is not
 * mainly for users — the screen said the right thing — it is that no journey, probe or
 * monitor reading a status code could tell *"this screen exists and works"* from *"this
 * screen exists and is reporting a failure"*. `W21-E2E`'s committed journey reads the
 * rendered body precisely because of that.
 *
 * The check is a pure regex over the contract's own pattern, so it costs no request: a
 * typo in a pasted address is a *malformed URL*, which is a different thing from a
 * resource the server says does not exist. The second of those still answers 200 and is
 * still rendered as an error state — see `docs/program/reviews/W22-WEB.md` §3 for why
 * that half is not fixed here.
 *
 * `R-50`: the route awaits `requireAChangedPassword()` before it renders. A session still
 * on the password this deployment was seeded with is sent to `/account/password` instead,
 * and the API refuses this screen's data calls independently -- so what the reviewer would
 * otherwise meet here is a screen that cannot load. Declared `force-dynamic` because the
 * check reads a cookie, and a screen served from a cache is a screen showing somebody
 * else's session.
 */

import { notFound } from 'next/navigation';

import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeDocumentUid } from '@/entities/document-version';
import { DocumentDetailPage } from '@/_pages/document-detail';

import { requireAChangedPassword } from '../../../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function DocumentRoute({
  params,
}: {
  params: Promise<{ project_uid: string; document_uid: string }>;
}) {
  await requireAChangedPassword();
  const { project_uid, document_uid } = await params;
  if (!looksLikeProjectUid(project_uid) || !looksLikeDocumentUid(document_uid)) notFound();
  return <DocumentDetailPage projectUid={project_uid} documentUid={document_uid} />;
}
