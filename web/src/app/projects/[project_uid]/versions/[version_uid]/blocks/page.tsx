/**
 * `/projects/[project_uid]/versions/[version_uid]/blocks` — the version's «Блоки» tab (`R-151m`).
 *
 * Delegation-only: the route awaits `requireScreen` with its own address, then answers a malformed identifier
 * with not-found without a request; the screen is `/blocks`'s own, opened with the version already chosen.
 */

import { notFound } from 'next/navigation';

import { looksLikeVersionUid } from '@/entities/document-version';
import { looksLikeProjectUid } from '@/entities/project';
import { BlocksPage } from '@/_pages/blocks';

import type { RouteParams } from '@/shared/config';

import { requireScreen } from '../../../../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function VersionBlocksRoute({
  params,
  searchParams,
}: {
  params: Promise<{ project_uid: string; version_uid: string }>;
  searchParams?: Promise<RouteParams> | undefined;
}) {
  await requireScreen('/projects/[project_uid]/versions/[version_uid]/blocks', { params, searchParams });
  const { project_uid, version_uid } = await params;
  if (!looksLikeProjectUid(project_uid) || !looksLikeVersionUid(version_uid)) notFound();
  return <BlocksPage projectUid={project_uid} versionUid={version_uid} />;
}
