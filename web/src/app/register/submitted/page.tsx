import { RegisterSubmittedPage } from '@/_pages/register-submitted';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function RegisterSubmittedRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/register/submitted', { params, searchParams });
  return <RegisterSubmittedPage />;
}
