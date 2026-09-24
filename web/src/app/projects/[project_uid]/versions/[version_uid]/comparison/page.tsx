/**
 * `/projects/{project_uid}/versions/{version_uid}/comparison` — two runs of one version,
 * side by side.
 *
 * Delegation-only, like every other route in this tree.
 *
 * **The shape of every dynamic segment is checked here, and a malformed one is a 404.**
 * `D-28`: a dynamic segment matches any string, so an unrouted path answers **200** and
 * renders a screen in an error state unless the route refuses it — and no journey, probe
 * or monitor reading a status code can then tell *"this screen exists and works"* from
 * *"this screen exists and is reporting a failure"*. The check is a pure regex over the
 * contract's own patterns and costs no request.
 *
 * **Both segments, not only the last one.** `routes.test.ts` has a case for exactly this:
 * a route that validated the child and trusted the parent answers 200 for
 * `/projects/nonsense/versions/<real>/comparison`.
 */

import { notFound } from 'next/navigation';

import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeVersionUid } from '@/entities/document-version';
import { StageComparisonPage } from '@/_pages/stage-comparison';

export default async function ComparisonRoute({
  params,
}: {
  params: Promise<{ project_uid: string; version_uid: string }>;
}) {
  const { project_uid, version_uid } = await params;
  if (!looksLikeProjectUid(project_uid) || !looksLikeVersionUid(version_uid)) notFound();
  return <StageComparisonPage projectUid={project_uid} versionUid={version_uid} />;
}
