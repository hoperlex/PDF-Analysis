import { RegisterPage } from '@/_pages/register';
import { isRegistrationRefusal } from '@/features/register';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function RegisterRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/register', { params, searchParams });
  const query = searchParams === undefined ? {} : await searchParams;
  const raw = query.refusal;
  const candidate = Array.isArray(raw) ? raw[0] : raw;
  return <RegisterPage refusal={isRegistrationRefusal(candidate) ? candidate : null} unknownRefusal={candidate !== undefined && !isRegistrationRefusal(candidate)} />;
}
