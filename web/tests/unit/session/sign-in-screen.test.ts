/**
 * The sign-in screen: what it renders, in which language, and what it is made of.
 *
 * `tests/guards/rendered-language.guard.test.ts` renders three of this screen's shapes and
 * judges every Latin word on them. This file covers the fourth thing that guard cannot: the
 * other three refusal sentences, which a static pass reaches only when a prop selects them.
 * The check here is deliberately stricter than the guard's — **no Latin letter at all** —
 * because unlike the six audit screens this one shows no contract vocabulary, no identifier
 * and no digest. A screen with nothing legitimate to spell in Latin can be held to that.
 *
 * The other half is structural. The password input must be plain HTML: no `'use client'`
 * anywhere in the slice, so the field is never a React state, never a value in a bundle and
 * never something a later dependency can read. That is asserted against the source text,
 * because it is a property of the files rather than of the markup.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { SignInPage } from '@/_pages/sign-in';
import type { SignInRefusal } from '@/features/sign-in';
import { SESSION_CLOSE_PATH, SESSION_OPEN_PATH, SIGN_IN_REFUSALS, signInRefusalMessage } from '@/features/sign-in';

import { WEB_ROOT } from '../../guards/lib/repo';
import { render } from '../review/fixtures';

const SLICE_FILES = [
  'src/features/sign-in/model/exchange.ts',
  'src/features/sign-in/ui/sign-in-form.tsx',
  'src/features/sign-in/ui/sign-out-form.tsx',
  'src/features/sign-in/index.ts',
  'src/_pages/sign-in/ui/sign-in-page.tsx',
  'src/_pages/sign-in/index.ts',
  'src/app/login/page.tsx',
];

/** The text a browser would show: element text, plus the attributes it renders as text. */
function visibleText(markup: string): string[] {
  const out: string[] = [];
  for (const match of markup.matchAll(/>([^<>]+)</g)) {
    const text = (match[1] ?? '').replace(/&#x27;|&quot;|&amp;|&lt;|&gt;/g, ' ').trim();
    if (text.length > 0) out.push(text);
  }
  for (const attribute of ['placeholder', 'title', 'alt', 'aria-label']) {
    for (const match of markup.matchAll(new RegExp(`\\s${attribute}="([^"]*)"`, 'g'))) {
      const text = (match[1] ?? '').trim();
      if (text.length > 0) out.push(text);
    }
  }
  return out;
}

function latinIn(markup: string): string[] {
  return [...new Set(visibleText(markup).flatMap((text) => text.match(/[A-Za-z]+/g) ?? []))].sort();
}

describe('the screen offers a credentials form and nothing that holds a credential', () => {
  const markup = render(createElement(SignInPage, {}));

  it('posts to the exchange, with both fields and a submit', () => {
    expect(markup).toContain(`action="${SESSION_OPEN_PATH}"`);
    expect(markup).toContain('method="post"');
    expect(markup).toContain('name="login"');
    expect(markup).toContain('name="password"');
    expect(markup).toContain('type="password"');
    expect(markup).toContain('type="submit"');
    expect(markup).toContain('Войти');
  });

  it('renders no value on either field, so nothing typed is ever re-served', () => {
    // A `value=` on these inputs would mean the markup carries what was typed. The form is
    // uncontrolled precisely so that it cannot.
    const inputs = markup.match(/<input[^>]*>/g) ?? [];
    expect(inputs.length).toBe(2);
    for (const input of inputs) expect(input).not.toContain('value=');
  });

  it('is built from files that ship no client JavaScript', () => {
    for (const relative of SLICE_FILES) {
      const source = readFileSync(join(WEB_ROOT, relative), 'utf8');
      // The directive is only a directive at the top of the file, so the comments — which
      // discuss it — are stripped before looking. A textual `includes` reported the
      // paragraph explaining why there is no directive as a directive.
      const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').trim();
      expect(code.startsWith("'use client'"), `${relative} declares a client component`).toBe(false);
      expect(code.startsWith('"use client"'), `${relative} declares a client component`).toBe(false);
      // No storage, no cookie writing, no transport: this slice posts a form and renders.
      for (const forbidden of ['localStorage', 'sessionStorage', 'document.cookie', 'indexedDB']) {
        expect(code.includes(forbidden), `${relative} touches ${forbidden}`).toBe(false);
      }
    }
  });
});

describe('the signed-in shape offers the way out, on the server', () => {
  const markup = render(createElement(SignInPage, { login: 'проверяющий' }));

  it('posts the logout to the address that ends the session', () => {
    expect(markup).toContain(`action="${SESSION_CLOSE_PATH}"`);
    expect(markup).toContain('Выйти');
    expect(markup).toContain('data-session-login="проверяющий"');
    // And the credentials form is gone: there is nothing to sign into while signed in.
    expect(markup).not.toContain('name="password"');
  });
});

describe('every refusal is Russian, and says nothing about which half was wrong', () => {
  it('renders all four, each with its machine value on a data attribute', () => {
    for (const refusal of SIGN_IN_REFUSALS) {
      const markup = render(createElement(SignInPage, { refusal }));
      expect(markup).toContain(`data-sign-in-refusal="${refusal}"`);
      expect(markup).toContain(signInRefusalMessage(refusal));
    }
  });

  it('states the throttling policy, and says nothing about the account in front of it', () => {
    // `W40-LIMIT`. The API answers a shut account with exactly the `401
    // authentication_required` it answers a wrong password with, so this tier could not
    // tell them apart if it wanted to -- and it must not want to: a `throttled` refusal
    // would say "this account exists and somebody is attacking it right now" to anybody
    // who can type a login.
    //
    // What the screen may say is the POLICY, which is public and is about nobody: it is
    // rendered on every credentials refusal, whether or not this account is anywhere near
    // its allowance. Without it, a reviewer who has mistyped five times and then types
    // their real password concludes their password is broken -- and this screen is the
    // only place that can be said.
    const message = signInRefusalMessage('credentials');
    expect(/приостанавлива/i.test(message)).toBe(true);
    expect(/подожд/i.test(message)).toBe(true);
    // Not a per-account report: no count, no deadline, no "this account".
    expect(/\d/.test(message)).toBe(false);
    expect(/эт(а|у|ой) учётн/i.test(message)).toBe(false);
    // And the refusal vocabulary did not grow a value for it.
    expect([...SIGN_IN_REFUSALS]).toEqual(['credentials', 'validation', 'unconfigured', 'upstream']);
  });

  it('never names the login or the password as the part that failed', () => {
    const message = signInRefusalMessage('credentials');
    // The two words this sentence must not carry as a diagnosis. It may name the pair —
    // it must not name a half.
    expect(/неверн\w* (имя|логин|пароль)/i.test(message)).toBe(false);
    expect(/(имя|логин|пароль)\w* не найден/i.test(message)).toBe(false);
    expect(message).toContain('не принята');
  });

  it('puts no Latin letter on any shape of this screen', () => {
    const shapes = [
      render(createElement(SignInPage, {})),
      render(createElement(SignInPage, { login: 'проверяющий' })),
      ...SIGN_IN_REFUSALS.map((refusal: SignInRefusal) =>
        render(createElement(SignInPage, { refusal })),
      ),
    ];
    // Non-vacuous: the extractor must be reading something.
    expect(visibleText(shapes[0] as string).length).toBeGreaterThan(5);
    for (const markup of shapes) expect(latinIn(markup)).toEqual([]);
  });

  it('can fail: the same reading finds a Latin label put on the same screen', () => {
    expect(latinIn('<p>Вход</p><button>Sign in</button>')).toEqual(['Sign', 'in']);
    expect(latinIn('<span data-sign-in-refusal="credentials">Отказ</span>')).toEqual([]);
  });
});
