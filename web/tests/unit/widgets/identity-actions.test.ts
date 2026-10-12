/**
 * `W53C-WEB-ID-01`, `C-20` and `C-24` — what the identity controls *do* when pressed.
 *
 * This suite has no DOM (`environment: 'node'`, no jsdom), so a click cannot be dispatched.
 * What it can do is real anyway: a probe component calls the control as a function inside a
 * server render, keeps the element tree it returned, and the test calls that tree's own
 * `onClick`/`onSubmit` handlers. Whatever they send goes through the generated client to a
 * recording `fetch`, and whatever they ask of the router goes to a recording router. So "the
 * trigger sends nothing" is read off the network, not off the markup.
 *
 * A server render keeps every `useState` at its initial value, so the confirmation shapes are
 * reached by seeding chosen initial values (`seed` below) through a `react` mock that wraps the
 * real `useState` and changes nothing else.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement, isValidElement } from 'react';
import type * as ReactModule from 'react';
import type { ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Account, RegistrationRequest } from '@/shared/api';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderWith } from '../screens/harness';

const seed = vi.hoisted(() => new Map<unknown, unknown>());
const router = vi.hoisted(() => ({ calls: [] as string[] }));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof ReactModule>();
  return {
    ...actual,
    useState: (initial: unknown) => actual.useState(seed.has(initial) ? seed.get(initial) : initial),
  };
});

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: (href: string) => router.calls.push(`push ${href}`),
    refresh: () => router.calls.push('refresh'),
    replace: () => {},
    back: () => {},
    forward: () => {},
    prefetch: () => {},
  }),
}));

const { ManageUserControls, followUserCommand } = await import('@/features/manage-user');
const { RegistrationDecisionControls } = await import('@/features/decide-registration');
const { followProfileSave } = await import('@/features/edit-profile');

const ACCOUNT: Account = {
  archived_at: null,
  display_label: 'Петрова А. С.',
  first_name: 'Анна',
  is_default_credential: false,
  last_name: 'Петрова',
  login: 'petrova@example.org',
  middle_name: 'Сергеевна',
  profile_complete: true,
  roles: ['expert'],
  user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
};

const REQUEST = {
  request_id: 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
  status: 'pending',
  login: 'applicant@example.org',
} as unknown as RegistrationRequest;

let requests: string[] = [];

beforeEach(() => {
  seed.clear();
  router.calls = [];
  requests = [];
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init: RequestInit) => {
      const url = new URL(input);
      requests.push(`${init.method ?? 'GET'} ${url.pathname}${init.body ? ` ${String(init.body)}` : ''}`);
      const body = url.pathname.includes('/registrations/') ? { ...REQUEST, status: 'rejected' } : ACCOUNT;
      return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

/** Render `make()` inside a probe and return the element tree it produced. */
function treeOf(make: () => ReactNode): ReactElement {
  let tree: ReactNode = null;
  function Probe() {
    tree = make();
    return tree as ReactElement;
  }
  renderWith(newClient(), createElement(Probe));
  expect(isValidElement(tree)).toBe(true);
  return tree as unknown as ReactElement;
}

function elements(node: ReactNode): ReactElement[] {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!isValidElement(node)) return [];
  const props = node.props as { children?: ReactNode };
  return [node, ...elements(props.children)];
}

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  if (!isValidElement(node)) return '';
  return textOf((node.props as { children?: ReactNode }).children);
}

function button(tree: ReactElement, text: string): ReactElement<{ onClick?: () => void }> | undefined {
  return elements(tree).find((element) => element.type === 'button' && textOf(element) === text) as
    | ReactElement<{ onClick?: () => void }>
    | undefined;
}

/** Let the mutation reach `fetch` and settle. */
async function settle(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('C-24: «Архивировать» asks first', () => {
  it('the trigger sends nothing: it only opens the confirmation', async () => {
    const tree = treeOf(() => ManageUserControls({ account: ACCOUNT }));
    const trigger = button(tree, 'Архивировать учётную запись');
    expect(trigger?.props.onClick, 'the archive trigger is a button with a handler').toBeTypeOf('function');
    expect(button(tree, 'Подтвердить архивирование')).toBeUndefined();
    trigger?.props.onClick?.();
    await settle();
    expect(requests).toEqual([]);
  });

  it('the confirmation names the account, and only its confirm button archives', async () => {
    seed.set(false, true);
    const tree = treeOf(() => ManageUserControls({ account: ACCOUNT }));
    const group = elements(tree).find(
      (element) => (element.props as { 'aria-label'?: string })['aria-label'] === 'Подтверждение архивирования',
    );
    expect(textOf(group)).toContain(ACCOUNT.login);
    button(tree, 'Отмена')?.props.onClick?.();
    await settle();
    expect(requests).toEqual([]);
    button(tree, 'Подтвердить архивирование')?.props.onClick?.();
    await settle();
    expect(requests).toEqual([`POST /bff/v1/users/${ACCOUNT.user_uid}/archive`]);
  });
});

describe('C-24: «Отклонить заявку» asks first', () => {
  function rejectForm(tree: ReactElement): ReactElement<{ onSubmit?: (event: unknown) => void }> {
    const form = elements(tree).find(
      (element) => element.type === 'form' && elements(element).some((child) => child.type === 'textarea'),
    );
    expect(form, 'the rejection form').toBeDefined();
    return form as ReactElement<{ onSubmit?: (event: unknown) => void }>;
  }

  it('submitting a valid reason sends nothing: it only opens the confirmation', async () => {
    seed.set('', 'Дубликат заявки');
    const tree = treeOf(() => RegistrationDecisionControls({ request: REQUEST }));
    expect(button(tree, 'Подтвердить отклонение')).toBeUndefined();
    rejectForm(tree).props.onSubmit?.({ preventDefault: () => {} });
    await settle();
    expect(requests).toEqual([]);
  });

  it('the confirmation names the applicant, and only its confirm button rejects, with the reason', async () => {
    seed.set('', 'Дубликат заявки');
    seed.set(null, 'Дубликат заявки');
    const tree = treeOf(() => RegistrationDecisionControls({ request: REQUEST }));
    const group = elements(tree).find(
      (element) => (element.props as { 'aria-label'?: string })['aria-label'] === 'Подтверждение отклонения',
    );
    expect(textOf(group)).toContain('applicant@example.org');
    expect(button(tree, 'Отклонить заявку')).toBeUndefined();
    button(tree, 'Подтвердить отклонение')?.props.onClick?.();
    await settle();
    expect(requests).toEqual([
      `POST /bff/v1/registrations/${REQUEST.request_id}/reject ${JSON.stringify({ reason: 'Дубликат заявки' })}`,
    ]);
  });
});

describe('C-20: a change to the signed-in account refreshes the frame', () => {
  const ARCHIVED: Account = { ...ACCOUNT, archived_at: '2026-10-08T00:00:00Z' };

  it('restoring one\'s own account calls router.refresh(); another account\'s does not', async () => {
    for (const [isSelf, expected] of [[true, ['refresh']], [false, []]] as const) {
      router.calls = [];
      requests = [];
      const tree = treeOf(() => ManageUserControls({ account: ARCHIVED, isSelf }));
      button(tree, 'Восстановить учётную запись')?.props.onClick?.();
      await settle();
      expect(requests, `isSelf ${isSelf}`).toEqual([`POST /bff/v1/users/${ACCOUNT.user_uid}/restore`]);
      expect(router.calls, `isSelf ${isSelf}`).toEqual(expected);
    }
  });

  it('followUserCommand: a purge goes to the list, a self change refreshes, another change does neither', () => {
    const calls: string[] = [];
    const recorder = { push: (href: string) => calls.push(`push ${href}`), refresh: () => calls.push('refresh') };
    followUserCommand(recorder, { kind: 'purged' }, false, '/admin/users');
    followUserCommand(recorder, { kind: 'account', account: ACCOUNT }, true, '/admin/users');
    followUserCommand(recorder, { kind: 'account', account: ACCOUNT }, false, '/admin/users');
    expect(calls).toEqual(['push /admin/users', 'refresh']);
  });

  it('the profile form hands every successful save to followProfileSave (its submit needs a DOM FormData)', () => {
    const source = readFileSync(join(WEB_ROOT, 'src/features/edit-profile/ui/edit-profile-form.tsx'), 'utf8');
    expect(source).toContain('followProfileSave(router, await edit.mutateAsync(body), next);');
    expect(source).not.toMatch(/router\.push\(/);
  });

  it('followProfileSave: every save refreshes the frame, and a completed profile then goes to next', () => {
    const calls: string[] = [];
    const recorder = { push: (href: string) => calls.push(`push ${href}`), refresh: () => calls.push('refresh') };
    followProfileSave(recorder, { profile_complete: false }, '/projects');
    followProfileSave(recorder, { profile_complete: true }, null);
    followProfileSave(recorder, { profile_complete: true }, '/projects');
    expect(calls).toEqual(['refresh', 'refresh', 'refresh', 'push /projects']);
  });
});
