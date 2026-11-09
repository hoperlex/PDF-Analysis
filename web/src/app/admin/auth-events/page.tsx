import { AdminAuthEventsPage } from '@/_pages/admin-auth-events';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AdminAuthEventsRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/admin/auth-events', { params, searchParams });
  return <AdminAuthEventsPage />;
}
