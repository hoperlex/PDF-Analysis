/**
 * `R-150c` (`UI-PARITY-01`): the project the user works in lives in the address, and four pure
 * helpers read and write it. Each test names the rule it holds.
 *
 * The classes come from the live screen registry (`required` under `/projects/[project_uid]`,
 * `optional` for the six screens that follow the header, `global` for the rest), plus one
 * fixture registry for the cases the live one cannot reach: a row with no class.
 */

import { describe, expect, it } from 'vitest';

import type { ScreenEntry } from '@/shared/config';
import {
  PROJECT_DEPENDENT_PARAMS,
  canonicalProjectParams,
  projectScopeOf,
  readProjectContext,
  switchProject,
  withProjectParam,
} from '@/shared/lib';

const A = 'prj_01JAAAAAAAAAAAAAAAAAAAAAAA';
const B = 'prj_01JBBBBBBBBBBBBBBBBBBBBBBB';

const q = (query: string): URLSearchParams => new URLSearchParams(query);

/** One address per class, from the live registry. */
const REQUIRED_PATHS = [
  `/projects/${A}`,
  `/projects/${A}/documents/doc_1`,
  `/projects/${A}/versions/ver_1`,
  `/projects/${A}/versions/ver_1/comparison`,
  `/projects/${A}/runs/run_1`,
  `/projects/${A}/runs/run_1/review`,
];
const OPTIONAL_PATHS = [
  '/dashboard',
  '/knowledge-base',
  '/section-optimisation',
  '/optimisation',
  '/version-comparison',
  '/stage-comparison',
];
const GLOBAL_PATHS = [
  '/',
  '/projects',
  '/queue',
  '/logs',
  '/workers',
  '/analysis-settings',
  '/norms',
  '/norms/document',
  '/admin/users',
  '/account',
  // Undecided (debt D-305): global for now, because that is their behaviour today.
  '/dispatcher',
  '/blocks',
];

describe('projectScopeOf: the registry class of the screen an address is', () => {
  it('reads required, optional and global from the matched row', () => {
    for (const path of REQUIRED_PATHS) expect(projectScopeOf(path), path).toBe('required');
    for (const path of OPTIONAL_PATHS) expect(projectScopeOf(path), path).toBe('optional');
    for (const path of GLOBAL_PATHS) expect(projectScopeOf(path), path).toBe('global');
  });

  it('is null for an address no row matches, and never a class by default', () => {
    expect(projectScopeOf('/no-such-screen')).toBeNull();
    expect(projectScopeOf(`/projects/${A}/no-such-child`)).toBeNull();
  });

  it('can fail: a registry row with no class is an error, not a quiet `global`', () => {
    const unclassed: ScreenEntry[] = [
      { address: '/x', label: 'Икс', group: 'work', access: 'session', roles: 'any', inMenu: false },
    ];
    expect(() => projectScopeOf('/x', unclassed)).toThrow(/no projectScope/);
  });
});

describe('readProjectContext: the project an address names, and where it came from', () => {
  it('required: the path says it, with and without a query', () => {
    for (const path of REQUIRED_PATHS) {
      expect(readProjectContext(path, q('')), path).toEqual({ projectUid: A, source: 'path' });
    }
  });

  it('required: the path wins when ?project= names another project', () => {
    for (const path of REQUIRED_PATHS) {
      expect(readProjectContext(path, q(`project=${B}`)), path).toEqual({ projectUid: A, source: 'path' });
    }
  });

  it('required: other parameters change nothing', () => {
    expect(readProjectContext(`/projects/${A}/runs/run_1/review`, q('severity=high&cursor=abc'))).toEqual({
      projectUid: A,
      source: 'path',
    });
  });

  it('optional: the query says it', () => {
    for (const path of OPTIONAL_PATHS) {
      expect(readProjectContext(path, q(`project=${A}`)), path).toEqual({ projectUid: A, source: 'query' });
    }
  });

  it('optional: no parameter, or an empty one, is «Все проекты»', () => {
    for (const path of OPTIONAL_PATHS) {
      expect(readProjectContext(path, q('')), path).toEqual({ projectUid: null, source: 'none' });
      expect(readProjectContext(path, q('project=')), path).toEqual({ projectUid: null, source: 'none' });
      expect(readProjectContext(path, q('tab=x')), path).toEqual({ projectUid: null, source: 'none' });
    }
  });

  it('global: the frame still reads the query, to carry it on', () => {
    for (const path of GLOBAL_PATHS) {
      expect(readProjectContext(path, q(`project=${A}`)), path).toEqual({ projectUid: A, source: 'query' });
      expect(readProjectContext(path, q('')), path).toEqual({ projectUid: null, source: 'none' });
    }
  });

  it('a repeated ?project= is read as its first value', () => {
    expect(readProjectContext('/dashboard', q(`project=${A}&project=${B}`))).toEqual({
      projectUid: A,
      source: 'query',
    });
  });

  it('an address no row matches names no project, even with a query', () => {
    expect(readProjectContext('/no-such-screen', q(`project=${A}`))).toEqual({ projectUid: null, source: 'none' });
  });

  it('can fail: swapping the winner would be seen -- the path value is not the query value', () => {
    expect(readProjectContext(`/projects/${A}`, q(`project=${B}`)).projectUid).not.toBe(B);
  });
});

describe('canonicalProjectParams: the query an address should have', () => {
  it('required: ?project=Y beside /projects/X is dropped, so the path wins', () => {
    const result = canonicalProjectParams(`/projects/${A}/versions/ver_1`, q(`project=${B}`));
    expect(result.has('project')).toBe(false);
    expect(result.toString()).toBe('');
  });

  it('required: ?project= with the same project is dropped too -- one spelling', () => {
    expect(canonicalProjectParams(`/projects/${A}`, q(`project=${A}`)).toString()).toBe('');
  });

  it('required: every other parameter keeps its value and order', () => {
    const result = canonicalProjectParams(
      `/projects/${A}/runs/run_1/review`,
      q(`severity=high&project=${B}&cursor=abc&tab=evidence`),
    );
    expect(result.toString()).toBe('severity=high&cursor=abc&tab=evidence');
  });

  it('optional and global: a project is kept as it is', () => {
    expect(canonicalProjectParams('/dashboard', q(`x=1&project=${A}`)).toString()).toBe(`x=1&project=${A}`);
    expect(canonicalProjectParams('/queue', q(`project=${A}&state=failed`)).toString()).toBe(
      `project=${A}&state=failed`,
    );
  });

  it('optional and global: an empty ?project= is dropped (no project is no parameter)', () => {
    expect(canonicalProjectParams('/dashboard', q('x=1&project=')).toString()).toBe('x=1');
    expect(canonicalProjectParams('/queue', q('project=')).toString()).toBe('');
  });

  it('optional: a repeated ?project= keeps the first, where it stood', () => {
    expect(canonicalProjectParams('/dashboard', q(`x=1&project=${A}&y=2&project=${B}`)).toString()).toBe(
      `x=1&project=${A}&y=2`,
    );
  });

  it('an address no row matches is returned as it came', () => {
    expect(canonicalProjectParams('/no-such-screen', q(`project=${A}&x=1`)).toString()).toBe(`project=${A}&x=1`);
  });

  it('returns a copy: the input is not changed', () => {
    const input = q(`project=${B}&x=1`);
    canonicalProjectParams(`/projects/${A}`, input);
    expect(input.toString()).toBe(`project=${B}&x=1`);
  });

  it('accepts anything with get and toString, as Next hands a read-only query', () => {
    const readonlyLike = { get: (name: string) => (name === 'project' ? B : null), toString: () => `project=${B}` };
    expect(canonicalProjectParams(`/projects/${A}`, readonlyLike).toString()).toBe('');
  });
});

describe('withProjectParam: carrying the project onto a link', () => {
  it('optional and global targets get ?project=', () => {
    for (const path of [...OPTIONAL_PATHS, ...GLOBAL_PATHS]) {
      expect(withProjectParam(path, A), path).toBe(`${path}?project=${A}`);
    }
  });

  it('required targets never get it -- the project is in their path', () => {
    for (const path of REQUIRED_PATHS) expect(withProjectParam(path, B), path).toBe(path);
    expect(withProjectParam(`/projects/${A}?tab=runs`, B)).toBe(`/projects/${A}?tab=runs`);
  });

  it('keeps the existing query and fragment', () => {
    expect(withProjectParam('/queue?state=failed&period=7d', A)).toBe(`/queue?state=failed&period=7d&project=${A}`);
    expect(withProjectParam('/dashboard?x=1#top', A)).toBe(`/dashboard?x=1&project=${A}#top`);
    expect(withProjectParam('/logs#tail', A)).toBe(`/logs?project=${A}#tail`);
  });

  it('replaces a project the target already had, in place', () => {
    expect(withProjectParam(`/dashboard?project=${B}&x=1`, A)).toBe(`/dashboard?project=${A}&x=1`);
  });

  it('a target that already has this project is returned verbatim', () => {
    expect(withProjectParam(`/dashboard?x=1&project=${A}`, A)).toBe(`/dashboard?x=1&project=${A}`);
  });

  it('«Все проекты» (null) removes the parameter and keeps the rest', () => {
    expect(withProjectParam(`/dashboard?project=${A}&x=1`, null)).toBe('/dashboard?x=1');
    expect(withProjectParam(`/dashboard?project=${A}#top`, null)).toBe('/dashboard#top');
    expect(withProjectParam('/dashboard', null)).toBe('/dashboard');
    expect(withProjectParam('/dashboard?x=1', '')).toBe('/dashboard?x=1');
  });

  it('a required target is not touched by «Все проекты» either', () => {
    expect(withProjectParam(`/projects/${A}`, null)).toBe(`/projects/${A}`);
  });

  it('a value that needs escaping is escaped, not spliced', () => {
    expect(withProjectParam('/dashboard', 'a&b=c')).toBe('/dashboard?project=a%26b%3Dc');
  });

  it('an href that is not a registered address of this application is returned unchanged', () => {
    for (const href of ['https://example.org/dashboard', '//example.org/dashboard', '/\\example.org', 'dashboard', '', '/no-such-screen']) {
      expect(withProjectParam(href, A), href).toBe(href);
    }
  });
});

describe('switchProject: choosing a project in the header', () => {
  it('sets the new project and removes every dependent parameter', () => {
    const everything = [`project=${A}`, ...PROJECT_DEPENDENT_PARAMS.map((name) => `${name}=x`)].join('&');
    expect(switchProject(q(everything), B).toString()).toBe(`project=${B}`);
  });

  it('the dependent parameters are exactly section, version, pair, set, run, cursor, tab', () => {
    expect([...PROJECT_DEPENDENT_PARAMS]).toEqual(['section', 'version', 'pair', 'set', 'run', 'cursor', 'tab']);
  });

  it('removes each dependent parameter on its own', () => {
    for (const name of PROJECT_DEPENDENT_PARAMS) {
      expect(switchProject(q(`project=${A}&${name}=x`), B).toString(), name).toBe(`project=${B}`);
    }
  });

  it('keeps the parameters that do not depend on a project, in order', () => {
    expect(switchProject(q(`state=failed&project=${A}&section=s1&period=7d&tab=runs`), B).toString()).toBe(
      `state=failed&project=${B}&period=7d`,
    );
  });

  it('chooses a project from «Все проекты»: the dependent parameters go too', () => {
    expect(switchProject(q('section=s1&state=failed'), A).toString()).toBe(`state=failed&project=${A}`);
  });

  it('«Все проекты» (null) removes project and the dependent parameters', () => {
    expect(switchProject(q(`project=${A}&section=s1&version=v1&state=failed`), null).toString()).toBe('state=failed');
    expect(switchProject(q(`project=${A}`), '').toString()).toBe('');
  });

  it('choosing the project the address already has changes nothing', () => {
    const same = `project=${A}&section=s1&cursor=c9`;
    expect(switchProject(q(same), A).toString()).toBe(same);
    expect(switchProject(q('section=s1'), null).toString()).toBe('section=s1');
  });

  it('removes a repeated dependent parameter whole', () => {
    expect(switchProject(q(`project=${A}&run=r1&run=r2`), B).toString()).toBe(`project=${B}`);
  });

  it('returns a copy: the input is not changed', () => {
    const input = q(`project=${A}&section=s1`);
    switchProject(input, B);
    expect(input.toString()).toBe(`project=${A}&section=s1`);
  });

  it('accepts anything with get and toString, as Next hands a read-only query', () => {
    const readonlyLike = { get: () => null, toString: () => 'tab=x' };
    expect(switchProject(readonlyLike, A).toString()).toBe(`project=${A}`);
  });
});
