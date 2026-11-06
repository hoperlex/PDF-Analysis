/**
 * Guard: the screen registry (`web/src/shared/config/screen-registry.ts`) is the only list of
 * screens, it is the route tree's list, and it says what `W50-PLAN.md` §3.1 and owner ruling
 * `R-66` say.
 *
 * ## What each half is held to
 *
 *   - **the tree, both directions.** The addresses of every `page.tsx` under `web/src/app`
 *     (the walker in `web/tests/unit/screens/route-screens.ts`) equal the registry's. A page
 *     with no row is a screen nobody decided anything about; a row with no page is a menu
 *     item that 404s. Each is red naming the address.
 *   - **the ruling.** `R-66`'s groups, their members and their order; `/optimisation`
 *     registered, reachable and out of the menu; the four stubs `session`/`any`.
 *   - **the shape.** One row per address, a Russian label, a role list only on a `session`
 *     row and never empty, and the addresses the guard redirects to at the access levels that
 *     make a redirect cycle impossible.
 *   - **the project class** (`R-150c`, `UI-PARITY-01`). Every row states a `projectScope`; the
 *     `required` rows are exactly the ones with `[project_uid]` in the address; the `optional`
 *     set is exactly six screens; every other row is `global`.
 *
 * Every check is a pure function over rows, exercised against a deliberately broken registry
 * — which proves it can go red — and against the live one.
 */

import { describe, expect, it } from 'vitest';

import { routeAddresses } from '../unit/screens/route-screens';

import { ROLE_VALUES } from '@/shared/api';
import type { ScreenEntry, ScreenGroup } from '@/shared/config';
import type { ProjectScope } from '@/shared/lib';
import {
  CHANGE_PASSWORD_SCREEN,
  FORBIDDEN_SCREEN,
  HOME_SCREEN,
  PROFILE_SCREEN,
  SCREEN_ACCESS_LEVELS,
  SCREEN_GROUPS,
  SCREEN_REGISTRY,
  SIGN_IN_SCREEN,
} from '@/shared/config';

const REGISTRY: readonly ScreenEntry[] = SCREEN_REGISTRY;

const PROJECT_SCOPES: readonly ProjectScope[] = ['required', 'optional', 'global'];

// ---------------------------------------------------------------- the checks, as functions

/** Addresses the tree serves and the registry lacks, and rows whose address the tree lacks. */
function drift(
  tree: readonly string[],
  registry: readonly ScreenEntry[],
): { readonly unregistered: string[]; readonly pageless: string[] } {
  const rows = new Set(registry.map((row) => row.address));
  const pages = new Set(tree);
  return {
    unregistered: tree.filter((address) => !rows.has(address)).sort(),
    pageless: registry
      .map((row) => row.address)
      .filter((address) => !pages.has(address))
      .sort(),
  };
}

/** The in-menu addresses of each group, in registry order. */
function menu(registry: readonly ScreenEntry[]): Record<ScreenGroup, string[]> {
  const out = Object.fromEntries(SCREEN_GROUPS.map((group) => [group, [] as string[]])) as Record<
    ScreenGroup,
    string[]
  >;
  for (const row of registry) if (row.inMenu) out[row.group].push(row.address);
  return out;
}

/** Sentences naming every row that breaks a shape rule. */
function shapeFindings(registry: readonly ScreenEntry[]): string[] {
  const findings: string[] = [];
  const seen = new Set<string>();
  for (const row of registry) {
    if (seen.has(row.address)) findings.push(`${row.address} has two rows`);
    seen.add(row.address);
    if (!/^\/(?:[a-z0-9-]+|\[[a-z_]+\])?(?:\/(?:[a-z0-9-]+|\[[a-z_]+\]))*$/.test(row.address)) {
      findings.push(`${row.address} is not an address shape`);
    }
    if (!/^[А-ЯЁ][А-Яа-яЁё ]*$/.test(row.label)) findings.push(`${row.address} has no Russian label`);
    if (!(SCREEN_ACCESS_LEVELS as readonly string[]).includes(row.access)) {
      findings.push(`${row.address} has an access level outside the three`);
    }
    if (!(SCREEN_GROUPS as readonly string[]).includes(row.group)) {
      findings.push(`${row.address} is in no known group`);
    }
    if (row.roles === 'any-role' && row.access !== 'session') {
      findings.push(`${row.address} asks for a role on a ${row.access} row`);
    }
    if (Array.isArray(row.roles)) {
      if (row.access !== 'session') findings.push(`${row.address} lists roles on a ${row.access} row`);
      if (row.roles.length === 0) findings.push(`${row.address} lists no role`);
      if (new Set(row.roles).size !== row.roles.length) findings.push(`${row.address} repeats a role`);
      for (const role of row.roles) {
        if (!(ROLE_VALUES as readonly string[]).includes(role)) {
          findings.push(`${row.address} lists ${String(role)}, which is not a contract role`);
        }
      }
    }
    if (!PROJECT_SCOPES.includes(row.projectScope as ProjectScope)) {
      findings.push(`${row.address} has no project class`);
    } else if (row.address.includes('[project_uid]') !== (row.projectScope === 'required')) {
      findings.push(`${row.address} is ${row.projectScope} and ${row.address.includes('[project_uid]') ? 'has' : 'lacks'} a project in its path`);
    }
    if (row.inMenu && row.group === 'hidden') findings.push(`${row.address} is hidden and in the menu`);
    if (row.inMenu && row.address.includes('[')) {
      findings.push(`${row.address} is in the menu and needs an identity to open`);
    }
  }
  return findings;
}

/** The redirect targets at the access levels that keep the five decisions from looping. */
function cycleFindings(registry: readonly ScreenEntry[]): string[] {
  const expected: Record<string, string> = {
    [SIGN_IN_SCREEN]: 'public',
    [FORBIDDEN_SCREEN]: 'public',
    [CHANGE_PASSWORD_SCREEN]: 'open-to-default-credential',
    [PROFILE_SCREEN]: 'open-to-default-credential',
    [HOME_SCREEN]: 'session',
  };
  const findings: string[] = [];
  for (const [address, access] of Object.entries(expected)) {
    const row = registry.find((entry) => entry.address === address);
    if (row === undefined) findings.push(`${address} is a redirect target with no row`);
    else if (row.access !== access) findings.push(`${address} is ${row.access}, not ${access}`);
    else if (row.roles !== 'any') findings.push(`${address} is a redirect target that requires a role`);
  }
  return findings;
}

/**
 * The ruling with both later comparison screens, as data. Order matters: it is the menu's order.
 * `R-150b`: «Проекты» is no longer in it; the project selector of the frame's top strip replaced
 * that item, and `/projects` stays a registered screen with `inMenu: false`.
 */
const R66: Partial<Record<ScreenGroup, string[]>> = {
  home: [],
  work: ['/dashboard', '/section-optimisation', '/dispatcher', '/schedule', '/version-comparison', '/stage-comparison'],
  // `R-151m`: «Блоки» is a tab of the version, out of the menu.
  knowledge: ['/knowledge-base', '/norms'],
  system: ['/logs', '/workers', '/analysis-settings', '/queue'],
  admin: ['/admin/users', '/admin/registrations', '/admin/auth-events'],
  account: [],
  hidden: [],
};

const R66_STUBS = ['/section-optimisation', '/norms', '/analysis-settings', '/queue'];
/** `R-150w`: the operator's screens, closed to «Наблюдатель». */
const OPERATOR_SCREENS: readonly string[] = ['/queue', '/logs', '/workers', '/dispatcher', '/schedule'];

// --------------------------------------------------------------------------------- tree

describe('the registry is the route tree: every page has a row and every row a page', () => {
  it('can fail: a page with no row, and a row with no page, are each named', () => {
    const tree = ['/', '/projects', '/new-screen'];
    const registry = [
      { ...REGISTRY[0]!, address: '/' },
      { ...REGISTRY[0]!, address: '/projects' },
      { ...REGISTRY[0]!, address: '/gone' },
    ];
    expect(drift(tree, registry)).toEqual({ unregistered: ['/new-screen'], pageless: ['/gone'] });
  });

  it('reads a tree and a registry of a credible size', () => {
    // `W55A-WEB-NORMS` added the norms document view: 27 -> 28. `W61-DISPATCHER-01` added
    // «Диспетчер»: 28 -> 29. `CMP-VC-UI-01` added «Сравнение версий»: 29 -> 30.
    // `CMP-STAGE-PAIR-01` added «Сравнение стадий»: 30 -> 31. `R-151l` added «Раздел»: 31 -> 32. `R-151m` added
    // the version's «Блоки» tab: 32 -> 33. `UI-PARITY-P0P` added «График работ»: 33 -> 34.
    // `UI-A-94` (contract 1.36.0) added «Журнал входов»: 34 -> 35.
    expect(routeAddresses().length).toBe(35);
    expect(REGISTRY.length).toBe(35);
  });

  it('has no page without a row and no row without a page', () => {
    const { unregistered, pageless } = drift(
      routeAddresses().map((route) => route.address),
      REGISTRY,
    );
    expect(
      unregistered,
      'web/src/app serves these addresses and the screen registry has no row for them: nobody ' +
        'decided who may open them. Add a row to web/src/shared/config/screen-registry.ts',
    ).toEqual([]);
    expect(
      pageless,
      'the screen registry lists these addresses and no page.tsx serves them: a menu item ' +
        'would open a 404. Remove the row or add the page',
    ).toEqual([]);
  });
});

// -------------------------------------------------------------------------------- shape

describe('every row has the shape §3.1 gives it', () => {
  it('can fail: each shape rule names the row that breaks it', () => {
    const broken: ScreenEntry[] = [
      { address: '/x', label: 'Икс', group: 'work', access: 'session', roles: 'any', inMenu: true, projectScope: 'global' },
      { address: '/x', label: 'Ex', group: 'hidden', access: 'public', roles: ['admin'], inMenu: true, projectScope: 'global' },
      {
        address: '/y/[id]',
        label: 'Игрек',
        group: 'work',
        access: 'session',
        roles: ['admin', 'admin'],
        inMenu: true,
        projectScope: 'global',
      },
      { address: '/z', label: 'Зет', group: 'account', access: 'public', roles: 'any-role', inMenu: false, projectScope: 'global' },
    ];
    expect(shapeFindings(broken)).toEqual([
      '/x has two rows',
      '/x has no Russian label',
      '/x lists roles on a public row',
      '/x is hidden and in the menu',
      '/y/[id] repeats a role',
      '/y/[id] is in the menu and needs an identity to open',
      '/z asks for a role on a public row',
    ]);
  });

  it('the live registry breaks none of them', () => {
    expect(shapeFindings(REGISTRY)).toEqual([]);
  });

  it('can fail: a redirect target at a level that would loop', () => {
    const looping = REGISTRY.map((row) =>
      row.address === PROFILE_SCREEN ? { ...row, access: 'session' as const } : row,
    );
    expect(cycleFindings(looping)).toEqual(['/account is session, not open-to-default-credential']);
  });

  it('puts every redirect target at the level that keeps the decisions from looping', () => {
    expect(cycleFindings(REGISTRY)).toEqual([]);
  });

  it('R-60: exactly the four administrator screens require admin (the access journal is the fourth, 1.36.0); R-150w: four operator screens require expert or admin', () => {
    expect(REGISTRY.filter((row) => Array.isArray(row.roles)).map((row) => [row.address, row.roles])).toEqual([
      ['/dispatcher', ['expert', 'admin']],
      ['/schedule', ['expert', 'admin']],
      ['/logs', ['expert', 'admin']],
      ['/workers', ['expert', 'admin']],
      ['/queue', ['expert', 'admin']],
      ['/admin/users', ['admin']],
      ['/admin/users/[user_uid]', ['admin']],
      ['/admin/registrations', ['admin']],
      ['/admin/auth-events', ['admin']],
    ]);
    for (const address of ['/register', '/register/submitted']) {
      expect(REGISTRY.find((row) => row.address === address)).toMatchObject({
        group: 'account', access: 'public', roles: 'any', inMenu: false,
      });
    }
  });
});

// -------------------------------------------------------------------------------- R-66

describe('R-66: the groups, their members and their order', () => {
  it('can fail: a reordered group and a stray menu row are both differences', () => {
    const moved = REGISTRY.map((row) =>
      row.address === '/optimisation' ? { ...row, group: 'system' as const, inMenu: true } : row,
    );
    expect(menu(moved).system).toContain('/optimisation');
    expect(menu(moved).system).not.toEqual(R66.system);
  });

  it('the menu is exactly the ruling, group by group, in order — Дашборд first in Работа, since R-150b took Проекты out', () => {
    const live = menu(REGISTRY);
    for (const group of SCREEN_GROUPS) {
      expect(live[group], `group ${group}`).toEqual(R66[group] ?? []);
    }
    expect(live.work[0]).toBe('/dashboard');
    // R-150b: the screen stays registered and open; only the menu item is gone.
    expect(live.work).not.toContain('/projects');
    expect(REGISTRY.find((row) => row.address === '/projects')).toMatchObject({ inMenu: false, access: 'session', roles: 'any-role' });
  });

  it('/optimisation is registered, reachable, hidden and out of the menu', () => {
    const row = REGISTRY.find((entry) => entry.address === '/optimisation');
    expect(row, '/optimisation is unregistered; R-66 keeps it a reachable screen until W59').toBeDefined();
    expect(row?.group).toBe('hidden');
    expect(row?.inMenu, '/optimisation is in the menu; R-66 took it out').toBe(false);
    expect(row?.access).toBe('session');
    expect(routeAddresses().map((route) => route.address)).toContain('/optimisation');
  });

  it('the four stubs are session screens any account holding a role opens (R-80), the queue only an expert or an administrator (R-150w)', () => {
    for (const address of R66_STUBS) {
      const row = REGISTRY.find((entry) => entry.address === address);
      expect(row, `${address} is not registered`).toBeDefined();
      // `R-150w`: «Наблюдатель» does not see the operational screens; the queue is one of them.
      const roles = OPERATOR_SCREENS.includes(address) ? ['expert', 'admin'] : 'any-role';
      expect([row?.access, row?.roles, row?.inMenu], address).toEqual(['session', roles, true]);
    }
  });

  it('the operational screens are not a viewer\'s (R-150w): queue, journal, executors and dispatcher need expert or admin', () => {
    for (const address of OPERATOR_SCREENS) {
      const row = REGISTRY.find((entry) => entry.address === address);
      expect(row?.roles, address).toEqual(['expert', 'admin']);
    }
  });

  it('«Нормы» keeps its menu place, and its document view is an any-role screen out of the menu (W55A-WEB-NORMS)', () => {
    const view = REGISTRY.find((entry) => entry.address === '/norms/document');
    expect(view, '/norms/document is not registered').toBeDefined();
    expect([view?.group, view?.access, view?.roles, view?.inMenu]).toEqual(['knowledge', 'session', 'any-role', false]);
    expect(view?.label).toBe('Нормативный документ');
    // The menu still offers «Нормы» once, and not its document view.
    expect(menu(REGISTRY).knowledge).toEqual(['/knowledge-base', '/norms']);
  });

  it('the labels are the ruling\'s words', () => {
    const labels = Object.fromEntries(REGISTRY.map((row) => [row.address, row.label]));
    expect(labels['/section-optimisation']).toBe('Оптимизация разделов');
    expect(labels['/norms']).toBe('Нормы');
    expect(labels['/analysis-settings']).toBe('Настройки анализа');
    expect(labels['/queue']).toBe('Очередь');
    expect(labels['/']).toBe('Главная');
    expect(labels['/projects']).toBe('Проекты');
    expect(labels['/admin/users']).toBe('Пользователи');
    expect(labels['/admin/registrations']).toBe('Заявки на регистрацию');
    expect(labels['/admin/auth-events']).toBe('Журнал входов');
  });
});

// ------------------------------------------------------------------------ project class

/** The addresses of the rows with this class, in registry order. */
function scopeOf(registry: readonly ScreenEntry[], scope: ProjectScope): string[] {
  return registry.filter((row) => row.projectScope === scope).map((row) => row.address);
}

/** The ruling (`R-150c`): the screens that follow the header's project. Order is the registry's. */
const OPTIONAL_SCREENS = [
  '/dashboard',
  // `R-151m`: «Диспетчер» follows the header.
  '/dispatcher',
  '/section-optimisation',
  '/version-comparison',
  '/stage-comparison',
  '/knowledge-base',
  '/optimisation',
];

describe('R-150c: every row states how the screen relates to the project', () => {
  it('can fail: a row with no class, an unknown class, and a class that contradicts the path are each named', () => {
    const base = REGISTRY.find((row) => row.address === '/dashboard')!;
    const unstated: ScreenEntry = {
      address: base.address,
      label: base.label,
      group: base.group,
      access: base.access,
      roles: base.roles,
      inMenu: base.inMenu,
    };
    const broken: ScreenEntry[] = [
      unstated,
      { ...base, address: '/a', projectScope: 'sometimes' as unknown as ProjectScope },
      { ...base, address: '/b/[project_uid]', inMenu: false, projectScope: 'optional' },
      { ...base, address: '/c', projectScope: 'required' },
    ];
    expect(shapeFindings(broken).filter((finding) => /project/.test(finding))).toEqual([
      '/dashboard has no project class',
      '/a has no project class',
      '/b/[project_uid] is optional and has a project in its path',
      '/c is required and lacks a project in its path',
    ]);
  });

  it('can fail: the optional set is compared as a set, so one more or one fewer is a difference', () => {
    const widened = REGISTRY.map((row) => (row.address === '/queue' ? { ...row, projectScope: 'optional' as const } : row));
    expect(scopeOf(widened, 'optional').sort()).not.toEqual([...OPTIONAL_SCREENS].sort());
    const narrowed = REGISTRY.map((row) => (row.address === '/dashboard' ? { ...row, projectScope: 'global' as const } : row));
    expect(scopeOf(narrowed, 'optional').sort()).not.toEqual([...OPTIONAL_SCREENS].sort());
  });

  it('every live row carries one of the three classes', () => {
    expect(REGISTRY.filter((row) => !PROJECT_SCOPES.includes(row.projectScope as ProjectScope)).map((row) => row.address)).toEqual([]);
  });

  it('required: exactly the screens with the project in the path -- everything under /projects/[project_uid]', () => {
    expect(scopeOf(REGISTRY, 'required')).toEqual([
      '/projects/[project_uid]',
      '/projects/[project_uid]/sections/[section_code]',
      '/projects/[project_uid]/documents/[document_uid]',
      '/projects/[project_uid]/versions/[version_uid]',
      '/projects/[project_uid]/versions/[version_uid]/blocks',
      '/projects/[project_uid]/versions/[version_uid]/comparison',
      '/projects/[project_uid]/runs/[run_id]',
      '/projects/[project_uid]/runs/[run_id]/review',
    ]);
    // The project list is not under a project: it is the screen that chooses one.
    expect(REGISTRY.find((row) => row.address === '/projects')?.projectScope).toBe('global');
  });

  it('optional: exactly the seven screens that follow the header', () => {
    expect(scopeOf(REGISTRY, 'optional').sort()).toEqual([...OPTIONAL_SCREENS].sort());
  });

  it('global: every other screen, including /blocks (R-151m: the chooser out of the menu)', () => {
    const others = REGISTRY.filter((row) => !row.address.includes('[project_uid]') && !OPTIONAL_SCREENS.includes(row.address));
    expect(others.length).toBeGreaterThan(0);
    expect(others.filter((row) => row.projectScope !== 'global').map((row) => row.address)).toEqual([]);
    for (const address of ['/blocks']) {
      expect(REGISTRY.find((row) => row.address === address)?.projectScope, address).toBe('global');
    }
    // The three sets partition the registry.
    expect(scopeOf(REGISTRY, 'required').length + scopeOf(REGISTRY, 'optional').length + scopeOf(REGISTRY, 'global').length).toBe(
      REGISTRY.length,
    );
  });
});
