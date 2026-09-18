/**
 * `/projects/{project_uid}/versions/{version_uid}` — one published version: its manifest,
 * its runs, and the control that starts one.
 *
 * Delegation-only.
 *
 * Added by `W19-SHELL` for `D-16`. A version is nested under its project for the same
 * reason a run is — the house convention this application already had — and the screen
 * then reads the version's own `project_uid` back from the server rather than trusting
 * the segment, so a pasted address carrying the wrong project links to the right one.
 *
 * `version_ordinal` is never a path parameter: the contract refuses it as one, because it
 * is a display and ordering value and not an identity.
 */

import { VersionDetailPage } from '@/_pages/version-detail';

export default async function VersionRoute({
  params,
}: {
  params: Promise<{ project_uid: string; version_uid: string }>;
}) {
  const { project_uid, version_uid } = await params;
  return <VersionDetailPage projectUid={project_uid} versionUid={version_uid} />;
}
