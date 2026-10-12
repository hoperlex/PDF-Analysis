'use client';

/**
 * The account's own profile form (`W50`/`W51`).
 *
 * `C-20`: the frame — the name in the bar, the avatar, the menu — is rendered by the root
 * layout from the session's subject, which the BFF refreshes when a profile change succeeds.
 * A client-side save alone does not re-render that layout, so after every successful save the
 * form calls `router.refresh()`: the server components are rendered again from the refreshed
 * subject, and a seeded account that has just completed its profile sees its name and its
 * menu at once. With a `next` address the form then goes there.
 *
 * `C-23`: a failure is the shared Russian reading (`failureMessage`) with this form's three
 * more precise sentences; nothing prints a thrown message.
 */

import { useRouter } from 'next/navigation';
import type { FormEvent } from 'react';

import type { Account, UpdateMyProfileRequest } from '@/shared/api';
import type { FailureWording } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState } from '@/shared/ui';

import { followProfileSave } from '../model/after-save';
import { useEditProfile } from '../model/use-edit-profile';

const PROFILE_FAILURE_WORDING: FailureWording = {
  validation_failed: 'Проверьте имя, фамилию и адрес электронной почты.',
  authentication_required: 'Сеанс завершён. Войдите снова.',
  permission_denied: 'Изменение профиля запрещено.',
};

export function EditProfileForm({ account, next }: { readonly account: Account; readonly next?: string | null }) {
  const router = useRouter();
  const edit = useEditProfile();
  const incomplete = !account.profile_complete;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body: UpdateMyProfileRequest = {
      last_name: String(form.get('last_name') ?? '').trim(),
      first_name: String(form.get('first_name') ?? '').trim(),
    };
    const middleName = String(form.get('middle_name') ?? '').trim();
    if (middleName) body.middle_name = middleName;
    if (incomplete) body.email = String(form.get('email') ?? '').trim();
    try {
      followProfileSave(router, await edit.mutateAsync(body), next);
    } catch {
      // The typed mutation error is rendered below; no second action occurs.
    }
  }

  const failure = edit.isError ? failureMessage(edit.error, PROFILE_FAILURE_WORDING) : null;

  return (
    <form className="am-form" onSubmit={(event) => void save(event)}>
      <div className="am-form__field"><label htmlFor="profile-last"><strong>Фамилия</strong></label><input id="profile-last" name="last_name" type="text" defaultValue={account.last_name ?? ''} required maxLength={60} /></div>
      <div className="am-form__field"><label htmlFor="profile-first"><strong>Имя</strong></label><input id="profile-first" name="first_name" type="text" defaultValue={account.first_name ?? ''} required maxLength={60} /></div>
      <div className="am-form__field"><label htmlFor="profile-middle"><strong>Отчество (необязательно)</strong></label><input id="profile-middle" name="middle_name" type="text" defaultValue={account.middle_name ?? ''} maxLength={60} /></div>
      <div className="am-form__field"><label htmlFor="profile-email"><strong>Адрес электронной почты</strong></label><input id="profile-email" name="email" type="email" defaultValue={incomplete ? '' : account.login} required={incomplete} disabled={!incomplete} maxLength={254} /></div>
      {incomplete ? <p className="am-note">Для завершения профиля укажите фамилию, имя и адрес электронной почты одним сохранением. После этого адрес входа изменить нельзя.</p> : null}
      <div className="am-form__row"><button className="am-button" type="submit" disabled={edit.isPending}>Сохранить профиль</button></div>
      {edit.isSuccess ? <p className="am-note" role="status">Профиль сохранён.</p> : null}
      {failure !== null ? <div data-profile-failure={failure.kind}><ErrorState title="Профиль не сохранён" detail={failure.detail} correlationId={failure.correlationId} /></div> : null}
    </form>
  );
}
