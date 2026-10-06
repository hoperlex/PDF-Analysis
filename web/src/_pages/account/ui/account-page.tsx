/**
 * `/account` — the account's profile, as a placeholder that says what is missing.
 *
 * `W50-PLAN.md` §3.2, decision three: a session whose profile is incomplete opens nothing but
 * the screens that complete it, and the guard sends it here. The screen that completes a
 * profile is `W51`'s, so until it lands this one states the fact the guard acted on — what
 * the account lacks, and that nothing else opens without it — rather than leaving a reviewer
 * on a screen that does not say why they are there.
 *
 * `R-59`: a profile is complete once the account has given its last name, first name and
 * e-mail; the API refuses every operation but `getMe`, `updateMyProfile` and
 * `changePassword` until then. The session records only whether it is complete, not which
 * field is missing, so the screen names what a complete profile needs.
 */

import { RoutePlaceholder } from '@/shared/ui';

export interface AccountPageProps {
  /** `R-59`: whether the account has given its names and e-mail, as `getMe` said at sign-in. */
  readonly profileComplete: boolean;
}

export function AccountPage({ profileComplete }: AccountPageProps) {
  return profileComplete ? (
    <RoutePlaceholder
      screen="Профиль"
      route="/account"
      promise="Здесь будет профиль учётной записи: фамилия, имя, отчество и адрес электронной почты, по которому выполняется вход, с возможностью их исправить."
    />
  ) : (
    <RoutePlaceholder
      screen="Профиль"
      route="/account"
      headline="Профиль не заполнен."
      promise="Учётной записи не хватает фамилии, имени и адреса электронной почты. Пока их нет, остальные разделы приложения не открываются. Экран, на котором их можно указать, ещё не готов."
    />
  );
}
