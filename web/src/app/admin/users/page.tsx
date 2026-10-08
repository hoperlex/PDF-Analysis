import { AdminUsersPage } from '@/_pages/admin-users';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AdminUsersRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/admin/users', { params, searchParams });
  return <AdminUsersPage />;
}
