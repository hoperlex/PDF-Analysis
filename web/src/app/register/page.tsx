import { RegisterPage } from '@/_pages/register';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function RegisterRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/register', { params, searchParams });
  return <RegisterPage />;
}
