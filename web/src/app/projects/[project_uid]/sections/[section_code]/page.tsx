/**
 * `/projects/[project_uid]/sections/[section_code]` — the route file for one section of one project
 * (`R-151l`, `UI-PARITY-P0E`).
 *
 * Delegation-only: the route decides nothing. It awaits `requireScreen` with its own address, then checks
 * both segments of the address without a request: a project uid that does not have the contract's shape, or a section code
 * outside the fifteen, is a malformed address and answers not-found. The `filter` parameter of the address (`?filter=not_run`,
 * `UI-PARITY-DOC-AUDIT`) is handed to the page as it came; the page decides what it means.
 */

import { notFound } from 'next/navigation';

import { findProjectSection, looksLikeProjectUid } from '@/entities/project';
import { SectionDetailPage } from '@/_pages/section-detail';

import type { RouteParams } from '@/shared/config';

import { requireScreen } from '../../../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function ProjectSectionRoute({
  params,
  searchParams,
}: {
  params: Promise<{ project_uid: string; section_code: string }>;
  searchParams?: Promise<RouteParams> | undefined;
}) {
  await requireScreen('/projects/[project_uid]/sections/[section_code]', { params, searchParams });
  const { project_uid, section_code } = await params;
  if (!looksLikeProjectUid(project_uid) || findProjectSection(section_code) === null) notFound();
  const query = searchParams === undefined ? {} : await searchParams;
  return <SectionDetailPage projectUid={project_uid} sectionCode={section_code} filter={query['filter']} />;
}
