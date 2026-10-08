import { ErrorState } from '@/shared/ui';

import type { RegistrationRefusal } from '../model/exchange';
import { registrationRefusalMessage } from '../model/exchange';

export function RegisterForm({ refusal, unknownRefusal = false }: {
  readonly refusal?: RegistrationRefusal | null;
  readonly unknownRefusal?: boolean;
}) {
  return (
    <form className="am-form" method="post" action="/bff/v1/registration">
      <p className="am-form__hint">Имя, фамилия и отчество: до 60 символов каждое. Пароль: не менее 8 символов, с учётом правил сервера; избегайте имени и адреса почты. Подтвердите пароль повторным вводом.</p>
      <div className="am-form__field"><label htmlFor="register-last"><strong>Фамилия</strong></label><input id="register-last" name="last_name" type="text" autoComplete="family-name" required maxLength={60} /></div>
      <div className="am-form__field"><label htmlFor="register-first"><strong>Имя</strong></label><input id="register-first" name="first_name" type="text" autoComplete="given-name" required maxLength={60} /></div>
      <div className="am-form__field"><label htmlFor="register-middle"><strong>Отчество (необязательно)</strong></label><input id="register-middle" name="middle_name" type="text" autoComplete="additional-name" maxLength={60} /></div>
      <div className="am-form__field"><label htmlFor="register-email"><strong>Адрес электронной почты</strong></label><input id="register-email" name="login" type="email" autoComplete="email" required maxLength={254} /></div>
      <div className="am-form__field"><label htmlFor="register-password"><strong>Пароль</strong></label><input id="register-password" name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={1024} /></div>
      <div className="am-form__field"><label htmlFor="register-confirm"><strong>Повторите пароль</strong></label><input id="register-confirm" name="confirm_password" type="password" autoComplete="new-password" required minLength={8} maxLength={1024} /></div>
      <div className="am-form__row"><button className="am-button" type="submit">Отправить заявку</button></div>
      {refusal !== null && refusal !== undefined ? <div data-registration-refusal={refusal}><ErrorState title="Заявка не отправлена" detail={registrationRefusalMessage(refusal)} /></div> : null}
      {unknownRefusal ? <div data-registration-refusal="unknown"><ErrorState title="Неизвестный ответ регистрации" detail="Сервер вернул состояние, которое эта версия страницы не понимает." /></div> : null}
    </form>
  );
}
