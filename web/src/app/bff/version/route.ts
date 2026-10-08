/** Same-origin web-build check. Only a live, complete session may read it. */

import { getWebBuildId } from '@/shared/config';

import { readSessionId, subjectOf } from '../session/store';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request): Response {
  const session = subjectOf(readSessionId(request.headers.get('cookie')));
  if (session === null || !session.profileComplete || session.isDefaultCredential) {
    return new Response(null, { status: 401, headers: { 'Cache-Control': 'no-store' } });
  }
  return Response.json(
    { web_build_id: getWebBuildId() },
    { headers: { 'Cache-Control': 'no-store' } },
  );
}
