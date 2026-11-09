import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { RegisterPage } from '@/_pages/register';
import { RegisterSubmittedPage } from '@/_pages/register-submitted';
import { REGISTRATION_REFUSALS } from '@/features/register';

import { render } from '../review/fixtures';

describe('registration screens', () => {
  it('posts six fields through the server door without client-side password state', () => {
    const markup = render(createElement(RegisterPage));
    expect(markup).toContain('method="post"');
    expect(markup).toContain('action="/bff/v1/registration"');
    for (const name of ['last_name', 'first_name', 'middle_name', 'login', 'password', 'confirm_password']) {
      expect(markup).toContain(`name="${name}"`);
    }
  });

  it('starts on the first field, ties the password fields to their hint, and leads back to sign-in as the original does', () => {
    const markup = render(createElement(RegisterPage));
    expect(markup).toMatch(/<input[^>]*id="register-last"[^>]*autofocus=""/);
    expect(markup).toContain('id="register-hint"');
    expect(markup.match(/aria-describedby="register-hint"/g)).toHaveLength(1);
    expect(markup).toMatch(/<a href="\/login">Вернуться ко входу<\/a>/);
  });

  it.each(REGISTRATION_REFUSALS)('renders the typed %s refusal', (refusal) => {
    const markup = render(createElement(RegisterPage, { refusal }));
    expect(markup).toContain(`data-registration-refusal="${refusal}"`);
    expect(markup).toContain('Заявка не отправлена');
  });

  it('renders an unknown refusal as a fault', () => {
    expect(render(createElement(RegisterPage, { unknownRefusal: true }))).toContain('data-registration-refusal="unknown"');
  });

  it('does not claim a direct visitor submitted an application', () => {
    const markup = render(createElement(RegisterSubmittedPage));
    expect(markup).toContain('Если форма была успешно отправлена');
    expect(markup).toContain('Письмо не отправляется');
  });
});
