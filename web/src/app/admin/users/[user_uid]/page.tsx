import { notFound } from 'next/navigation';

import { AdminUserPage } from '@/_pages/admin-user';
import { looksLikeUserUid } from '@/entities/user';

import type { RouteParams } from '@/shared/config';

import { requireScreen } from '../../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AdminUserRoute({
  params,
  searchParams,
}: {
  params: Promise<{ user_uid: string }>;
  searchParams?: Promise<RouteParams> | undefined;
}) {
  const subject = await requireScreen('/admin/users/[user_uid]', { params, searchParams });
  const { user_uid } = await params;
  // `C-24`: a malformed identity is a 404, as on the project routes — not a screen that
  // spends a request to report that the server found nothing.
  if (!looksLikeUserUid(user_uid)) notFound();
  return <AdminUserPage userUid={user_uid} signedInLogin={subject.login} />;
}
