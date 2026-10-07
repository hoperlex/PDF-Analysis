import { AdminUserPage } from '@/_pages/admin-user';

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
  await requireScreen('/admin/users/[user_uid]', { params, searchParams });
  const { user_uid } = await params;
  return <AdminUserPage userUid={user_uid} />;
}
