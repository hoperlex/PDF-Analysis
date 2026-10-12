/**
 * `C-22` — the three no-JavaScript forms cannot be posted twice, and the island that stops it
 * reads no field.
 *
 * `lockOnSubmit` is driven with a recording form and window: the first `submit` goes ahead and
 * disables the submit controls on the next task; every later one is cancelled; a page restored
 * from the back-forward cache gets its controls back. The component's source is then held to
 * touching nothing but the submit controls, and each of the three forms is shown to mount it.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { SignInPage } from '@/_pages/sign-in';
import { RegisterPage } from '@/_pages/register';
import { ChangePasswordPage } from '@/_pages/change-password';
import { REGISTRATION_SUBMIT_PATH } from '@/features/register';
import { SESSION_OPEN_PATH } from '@/features/sign-in';
import type { SubmitLockEvent } from '@/shared/ui/submit-lock';
import { SUBMIT_CONTROLS, lockOnSubmit } from '@/shared/ui/submit-lock';

import { WEB_ROOT } from '../../guards/lib/repo';
import { render } from '../review/fixtures';

function harness() {
  const controls = [{ disabled: false }, { disabled: false }];
  let submit: ((event: SubmitLockEvent) => void) | null = null;
  let restore: (() => void) | null = null;
  const queued: (() => void)[] = [];
  const disarm = lockOnSubmit(
    {
      onSubmit(listener) {
        submit = listener;
        return () => {
          submit = null;
        };
      },
      submitControls: () => controls,
    },
    {
      onRestore(listener) {
        restore = listener;
        return () => {
          restore = null;
        };
      },
    },
    (task) => queued.push(task),
  );
  const press = (alreadyPrevented = false) => {
    const event = {
      defaultPrevented: alreadyPrevented,
      preventDefault() {
        this.defaultPrevented = true;
      },
    };
    submit?.(event);
    return event.defaultPrevented;
  };
  const runQueued = () => queued.splice(0).forEach((task) => task());
  return { controls, press, runQueued, restore: () => restore?.(), disarm, armed: () => submit !== null };
}

describe('lockOnSubmit', () => {
  it('lets the first submission through and disables the controls only after it, on the next task', () => {
    const lock = harness();
    expect(lock.press()).toBe(false);
    // Not inside the event: the browser builds the submission after it.
    expect(lock.controls.map((control) => control.disabled)).toEqual([false, false]);
    lock.runQueued();
    expect(lock.controls.map((control) => control.disabled)).toEqual([true, true]);
  });

  it('cancels every later submission', () => {
    const lock = harness();
    lock.press();
    lock.runQueued();
    expect(lock.press()).toBe(true);
    expect(lock.press()).toBe(true);
  });

  it('does not lock on a submission somebody else already cancelled', () => {
    const lock = harness();
    lock.press(true);
    lock.runQueued();
    expect(lock.controls.map((control) => control.disabled)).toEqual([false, false]);
    expect(lock.press()).toBe(false);
  });

  it('gives the controls back when the page is restored from the back-forward cache', () => {
    const lock = harness();
    lock.press();
    lock.runQueued();
    lock.restore();
    expect(lock.controls.map((control) => control.disabled)).toEqual([false, false]);
    expect(lock.press()).toBe(false);
  });

  it('disarms', () => {
    const lock = harness();
    lock.disarm();
    expect(lock.armed()).toBe(false);
  });
});

describe('the island reads no field', () => {
  const source = readFileSync(join(WEB_ROOT, 'src/shared/ui/submit-lock.tsx'), 'utf8');
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

  it('touches only the submit controls', () => {
    expect(SUBMIT_CONTROLS).toBe('button[type="submit"], input[type="submit"]');
    expect(code.match(/querySelectorAll[^(]*\(([^)]*)\)/g)).toEqual([
      'querySelectorAll<HTMLButtonElement | HTMLInputElement>(SUBMIT_CONTROLS)',
    ]);
  });

  it('names no value, no form data, no element collection and no storage', () => {
    for (const forbidden of [
      '.value', 'FormData', '.elements', 'namedItem', 'password', 'localStorage', 'sessionStorage',
      'document.cookie', 'fetch(', 'querySelector(', 'getElementById', '.textContent', '.innerHTML',
    ]) {
      expect(code.includes(forbidden), forbidden).toBe(false);
    }
  });
});

describe('each of the three forms mounts it, inside the form', () => {
  const form = (markup: string, action: string): string =>
    new RegExp(`<form[^>]*action="${action.replace(/[?]/g, '\\?')}"[^>]*>[\\s\\S]*?</form>`).exec(markup)?.[0] ?? '';

  it('sign-in', () => {
    expect(form(render(createElement(SignInPage, {})), SESSION_OPEN_PATH)).toContain('data-submit-lock=""');
  });

  it('registration, which posts to the BFF mount like sign-in', () => {
    expect(REGISTRATION_SUBMIT_PATH).toBe(SESSION_OPEN_PATH.replace(/\/session$/, '/registration'));
    expect(form(render(createElement(RegisterPage, {})), REGISTRATION_SUBMIT_PATH)).toContain('data-submit-lock=""');
  });

  it('password change', () => {
    const markup = render(createElement(ChangePasswordPage, { login: 'проверяющий' }));
    expect(/<form[^>]*method="post"[^>]*>[\s\S]*?<\/form>/.exec(markup)?.[0] ?? '').toContain('data-submit-lock=""');
  });
});
