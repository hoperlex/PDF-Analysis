/**
 * No address is written into `web/src/_app` by hand (`W50-SHELL-FRAME`): every `href` and
 * `action` the frame renders comes from the screen registry or the session feature, so a
 * renamed screen cannot leave a dead link in the chrome.
 *
 * Read by PARSING every module under `_app` with the TypeScript compiler and refusing any
 * string literal — plain, template, or the head of a template — that begins with `/`.
 * Comments are not literals, so prose about an address does not trip it; an import
 * specifier begins with `@`, `.` or a package name, never with `/`.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const APP = fileURLToPath(new URL('../../../src/_app', import.meta.url));

function walk(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return walk(path);
    return /\.(?:ts|tsx)$/.test(name) ? [path] : [];
  });
}

/** Every literal in `source` that begins with `/`, as `line: text`. */
export function addressLiterals(source: string, fileName: string): string[] {
  const file = ts.createSourceFile(fileName, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const out: string[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isStringLiteralLike(node) || ts.isTemplateHead(node) || ts.isJsxText(node)) {
      const text = ts.isJsxText(node) ? node.text.trim() : node.text;
      if (text.startsWith('/')) {
        const line = file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1;
        out.push(`${line}: ${text}`);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return out;
}

const SOURCES = walk(APP);

describe('no address is written into _app by hand', () => {
  it('reads every module of _app', () => {
    const names = SOURCES.map((path) => relative(APP, path)).sort();
    for (const expected of ['app-frame.tsx', 'account-menu.tsx', 'frame-navigation.tsx', 'navigation.ts']) {
      expect(names).toContain(expected);
    }
  });

  it('finds no literal that begins with /', () => {
    const offences = SOURCES.flatMap((path) =>
      addressLiterals(readFileSync(path, 'utf8'), path).map((hit) => `${relative(APP, path)}:${hit}`),
    );
    expect(
      offences,
      'an address in _app is written by hand; take it from the screen registry (@/shared/config) ' +
        'or, for the session door, from @/features/sign-in',
    ).toEqual([]);
  });

  it('can fail: every spelling of a hand-written address is caught, and a comment is not', () => {
    const probe = [
      '<Link href="/projects">Проекты</Link>;',
      "<Link href={'/dashboard'}>Дашборд</Link>;",
      '<Link href={`/blocks`}>Блоки</Link>;',
      '<Link href={`/projects/${id}`}>Проект</Link>;',
      "const item = { href: '/account' };",
      '<form method="post" action="/bff/v1/session/end" />;',
      '// a comment naming /queue is prose',
      "import { HOME_SCREEN } from '@/shared/config';",
    ].join('\n');
    expect(addressLiterals(probe, 'probe.tsx').map((hit) => hit.split(':')[0])).toEqual(['1', '2', '3', '4', '5', '6']);
  });
});
