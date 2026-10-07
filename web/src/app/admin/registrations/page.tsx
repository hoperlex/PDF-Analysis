import { AdminRegistrationsPage } from '@/_pages/admin-registrations';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AdminRegistrationsRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/admin/registrations', { params, searchParams });
  return <AdminRegistrationsPage />;
}
