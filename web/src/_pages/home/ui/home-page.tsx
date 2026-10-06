/**
 * `/` — the application's front door, as a placeholder until `W50-HOME-01` builds it.
 *
 * `W50-PLAN.md` §3.2 moves the landing of a completed sign-in from `/projects` to `/`, and
 * §3.6 gives `/` a home page: a greeting by the account's name, the most recent projects,
 * the dashboard's summary and, for an administrator, the registration requests waiting for a
 * decision. This slice holds the address and the props until that lands.
 *
 * **The props are the contract, and they already carry what the home page needs from the
 * session**, because `W50-HOME-01` may change neither them nor the `/` seed in
 * `web/tests/unit/screens/route-screens.ts`. Both come from the subject the route's guard
 * returns, which the API described at sign-in (`getMe`): never a credential. Everything else
 * the home page shows is read by the page itself, through the generated client.
 */

import type { Role } from '@/shared/api';
import { RoutePlaceholder } from '@/shared/ui';

export interface HomePageProps {
  /** The account's name as the server resolves it (`Фамилия И. О.`), never empty. */
  readonly displayLabel: string;
  /** The account's role set, exactly as `getMe` listed it. Empty is a valid set. */
  readonly roles: readonly Role[];
}

export function HomePage({ displayLabel }: HomePageProps) {
  return (
    <RoutePlaceholder
      screen="Главная"
      route="/"
      // An exclamation and not a period: the server's name form ends in one (`Петрова А. С.`),
      // and a period after it reads `С..` — measured on the lane stand's journey.
      headline={`Здравствуйте, ${displayLabel}! Начальная страница ещё не готова.`}
      promise="Здесь будут последние проекты, общая сводка по ним и, для администратора, заявки на регистрацию, которые ждут решения."
    />
  );
}
