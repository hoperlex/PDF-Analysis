/**
 * `safeReturnPath` — the one validator for `next` and `from` (`W50-PLAN.md` §3.2), and the
 * concrete-address builder the guard feeds it.
 *
 * Every value here is one a browser can put in a query string, because that is where both
 * parameters come from. A value the validator lets through becomes a `Location` header after
 * sign-in and a hidden field on the sign-in form, so each refused shape below is an open
 * redirect or an injected attribute that did not happen.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ForbiddenPage } from '@/_pages/forbidden';
import type { ScreenEntry } from '@/shared/config';
import {
  RETURN_PATH_MAX_LENGTH,
  concreteAddress,
  requiredRolesFor,
  safeReturnPath,
} from '@/shared/config';

import { newClient, renderScreen } from '../screens/harness';

const A_PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

describe('a same-application address passes, as it was given', () => {
  it.each([
    '/',
    '/projects',
    '/projects?x=1',
    `/projects/${A_PROJECT}`,
    `/projects/${A_PROJECT}/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/review`,
    '/knowledge-base?category=%D0%90&verdict=accepted',
    '/login',
    '/403',
  ])('%s', (candidate) => {
    expect(safeReturnPath(candidate)).toBe(candidate);
  });

  it('keeps the query exactly: /projects?x=1 survives with it', () => {
    expect(safeReturnPath('/projects?x=1')).toBe('/projects?x=1');
  });

  it('takes exactly the maximum length, and not one character more', () => {
    const at = `/projects?q=${'a'.repeat(RETURN_PATH_MAX_LENGTH - '/projects?q='.length)}`;
    expect(at.length).toBe(512);
    expect(safeReturnPath(at)).toBe(at);
    expect(safeReturnPath(`${at}a`)).toBeNull();
  });
});

describe('anything else is dropped', () => {
  it.each([
    ['another origin, protocol-relative', '//evil.example'],
    ['another origin, protocol-relative, with a path', '//evil.example/projects'],
    ['an absolute URL', 'https://evil.example'],
    ['an absolute URL to this path', 'https://evil.example/projects'],
    ['a backslash read as a slash', '/\\evil'],
    ['a backslash later in the path', '/projects\\evil'],
    ['a scheme with no slashes', 'javascript:alert(1)'],
    ['an address this application does not serve', '/nowhere'],
    ['a trailing slash', '/projects/'],
    ['a template, not an address', '/projects/[project_uid]'],
    ['a dot segment', '/projects/..'],
    ['an encoded slash in a segment', '/projects/a%2Fb'],
    ['a fragment', '/projects#top'],
    ['a space', '/projects?x=a b'],
    ['a line break', '/projects?x=1\r\nSet-Cookie: a=b'],
    ['a stray percent', '/projects?x=%zz'],
    ['non-ASCII in the query', '/projects?x=я'],
    ['the empty string', ''],
    ['no leading slash', 'projects'],
  ])('%s', (_why, candidate) => {
    expect(safeReturnPath(candidate)).toBeNull();
  });

  it('a 513-character value', () => {
    const over = `/projects?q=${'a'.repeat(513 - '/projects?q='.length)}`;
    expect(over.length).toBe(513);
    expect(safeReturnPath(over)).toBeNull();
  });

  it('anything that is not a string', () => {
    for (const value of [null, undefined, 1, ['/projects'], { toString: () => '/projects' }]) {
      expect(safeReturnPath(value)).toBeNull();
    }
  });
});

describe('the guard builds the concrete address it is protecting', () => {
  it('fills each segment by name and keeps the query', () => {
    expect(
      concreteAddress('/projects/[project_uid]', { project_uid: A_PROJECT }, { x: '1', y: ['a', 'b'] }),
    ).toBe(`/projects/${A_PROJECT}?x=1&y=a&y=b`);
  });

  it('re-encodes the query, so what comes out is made of query characters', () => {
    const built = concreteAddress('/projects', {}, { q: 'я b&c' });
    expect(built).toBe('/projects?q=%D1%8F+b%26c');
    expect(safeReturnPath(built)).toBe(built);
  });

  it('answers null for a segment with no single value', () => {
    expect(concreteAddress('/projects/[project_uid]', {}, {})).toBeNull();
    expect(concreteAddress('/projects/[project_uid]', { project_uid: ['a', 'b'] }, {})).toBeNull();
  });
});

describe('/403 names the role the registry requires for from', () => {
  const FIXTURE: readonly ScreenEntry[] = [
    { address: '/', label: 'Главная', group: 'home', access: 'session', roles: 'any', inMenu: true },
    {
      address: '/admin/users',
      label: 'Учётные записи',
      group: 'admin',
      access: 'session',
      roles: ['admin'],
      inMenu: true,
    },
  ];

  it('resolves an administrator screen to the admin role', () => {
    expect(requiredRolesFor('/admin/users', FIXTURE)).toEqual(['admin']);
    expect(requiredRolesFor('/admin/users?page=2', FIXTURE)).toEqual(['admin']);
  });

  it('an expert sent here from /admin/users sees «Администратор»', () => {
    const markup = renderScreen(
      newClient(),
      createElement(ForbiddenPage, { requiredRoles: requiredRolesFor('/admin/users', FIXTURE) }),
    );
    expect(markup).toContain('«Администратор»');
    // `from` itself is never shown: it is an address the browser controls.
    expect(markup).not.toContain('/admin/users');
  });

  it('names no role when from resolves to none, and still says why the screen is closed', () => {
    const markup = renderScreen(
      newClient(),
      createElement(ForbiddenPage, { requiredRoles: requiredRolesFor('//evil.example', FIXTURE) }),
    );
    expect(markup).not.toContain('Администратор');
    expect(markup).not.toContain('evil');
    expect(markup).toContain('Доступ закрыт');
  });

  it('resolves nothing for a screen with no role, an invalid from, or none at all', () => {
    expect(requiredRolesFor('/', FIXTURE)).toBeNull();
    expect(requiredRolesFor('//evil.example/admin/users', FIXTURE)).toBeNull();
    expect(requiredRolesFor(undefined, FIXTURE)).toBeNull();
    // The live registry has no role-gated row in W50 (`R-60`).
    expect(requiredRolesFor('/admin/users')).toBeNull();
  });
});
