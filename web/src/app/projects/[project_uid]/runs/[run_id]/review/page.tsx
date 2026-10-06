/**
 * `/projects/{project_uid}/runs/{run_id}/review` — the findings of one run, and the page each was quoted from.
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
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders, and the screen registry's row for that address decides
 * who may open it: a guest is sent to sign in and comes back here, a default credential
 * goes to `/account/password`, an incomplete profile to `/account`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { notFound } from 'next/navigation';

import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeRunId } from '@/entities/audit-run';
import { ReviewPage } from '@/_pages/review';

import type { RouteParams } from '@/shared/config';

import { requireScreen } from '../../../../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function ReviewRoute({
  params,
  searchParams,
}: {
  params: Promise<{ project_uid: string; run_id: string }>;
  searchParams?: Promise<RouteParams> | undefined;
}) {
  await requireScreen('/projects/[project_uid]/runs/[run_id]/review', { params, searchParams });
  const { project_uid, run_id } = await params;
  if (!looksLikeProjectUid(project_uid) || !looksLikeRunId(run_id)) notFound();
  return <ReviewPage projectUid={project_uid} runId={run_id} />;
}
