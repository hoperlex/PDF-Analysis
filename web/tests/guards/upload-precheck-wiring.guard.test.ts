/**
 * Guard: the browser pre-check is wired to the upload form, not merely available to it.
 *
 * This guard exists because of two specific survivors. `W12-WEB` ran ten mutations inside
 * the region no test reached and all ten survived; two of them were:
 *
 *   U-04  `setPrecheck(chosen === null ? null : precheckUploadFile(chosen))`
 *         becomes `setPrecheck(null)` — the form stops pre-checking the chosen file;
 *   U-05  `if (file === null || precheck !== null) return;`
 *         becomes `if (file === null) return;` — the form submits a file the pre-check
 *         refused.
 *
 * Both are criterion 10's surface, and **neither is reachable from a render test.** Both
 * live inside closures that only an event fires: `choose` runs on the picker's `change`,
 * `send` on submit. `vitest.config.ts` pins `environment: 'node'` and this tree has no
 * `jsdom`, no `happy-dom` and no `@testing-library/*` — `FRONTEND_LOCK.json` seals the
 * dependency set and none may be added. One `renderToStaticMarkup` pass renders the
 * resting form and cannot press anything on it. `tests/unit/screens/forms-and-pages.test.ts`
 * takes the render half as far as it goes (the submit button is `disabled` before a file
 * is chosen); this file is the rest.
 *
 * **What this guard proves, and what it does not.** It proves the two statements are
 * present and wired to the right values. It does not execute them, so it is weaker than
 * the render tests beside it and is not offered as equivalent. It is here because the
 * alternative is not a better test — it is no test, on the two survivors that decide
 * whether a refused file can be sent.
 *
 * The mutation half below applies `W12-WEB`'s two substitutions to the source text in
 * memory and asserts the scanner reports each one. The fixture *is* the mutation, so this
 * guard is shown to fire on exactly what it exists to catch, not on a resemblance to it.
 */

import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT, readText } from './lib/repo';

const FORM_PATH = join(
  WEB_ROOT,
  'src',
  'features',
  'upload-document',
  'ui',
  'upload-document-form.tsx',
);

export const PRECHECK_RULE_IDS = ['precheck-runs-on-choice', 'submit-consults-precheck'] as const;
type PrecheckRuleId = (typeof PRECHECK_RULE_IDS)[number];

interface Violation {
  readonly rule: PrecheckRuleId;
  readonly why: string;
}

/**
 * The two rules, read off the source text.
 *
 * Comments and strings are stripped first so that a rule cannot be satisfied by the
 * docstring that describes it — the form's own comment names `precheckUploadFile`, and a
 * scanner that counted that would pass on a form that had stopped calling it.
 */
function scanPrecheckWiring(source: string): Violation[] {
  const code = source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1')
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")
    .replace(/"(?:[^"\\]|\\.)*"/g, '""');

  const violations: Violation[] = [];

  // 1. The chosen file reaches the pre-check. `precheckUploadFile(` must be called with
  //    the identifier the handler was given, not with a literal and not at all.
  const called = /setPrecheck\(\s*([^;]*?)\)\s*;/s.exec(code);
  if (called === null) {
    violations.push({ rule: 'precheck-runs-on-choice', why: 'no setPrecheck(...) call' });
  } else if (!/precheckUploadFile\s*\(\s*chosen\s*\)/.test(called[1] ?? '')) {
    violations.push({
      rule: 'precheck-runs-on-choice',
      why: `setPrecheck is given ${JSON.stringify((called[1] ?? '').trim())}, which does not run the pre-check over the chosen file`,
    });
  }

  // 2. The submit path refuses to send when the pre-check refused. There must be an early
  //    return that reads `precheck`, and it must come before `mutation.mutate(`.
  const mutateAt = code.indexOf('mutation.mutate(');
  const sendAt = code.indexOf('const send =');
  if (sendAt < 0 || mutateAt < 0) {
    violations.push({ rule: 'submit-consults-precheck', why: 'no send path to check' });
  } else {
    const beforeSend = code.slice(sendAt, mutateAt);
    const guards = /if\s*\(([^)]*)\)\s*return\s*;/g;
    let consulted = false;
    for (const match of beforeSend.matchAll(guards)) {
      if (/\bprecheck\b/.test(match[1] ?? '')) consulted = true;
    }
    if (!consulted) {
      violations.push({
        rule: 'submit-consults-precheck',
        why: 'the send path reaches mutation.mutate without an early return that reads `precheck`',
      });
    }
  }

  return violations;
}

describe('the upload form runs the pre-check and obeys it', () => {
  const source = readText(FORM_PATH);

  it('reads a real, non-trivial source file, so a broken path cannot pass vacuously', () => {
    expect(source.length).toBeGreaterThan(2000);
    expect(source).toContain('UploadDocumentForm');
    expect(source).toContain('precheckUploadFile');
  });

  it('has no wiring violation', () => {
    const violations = scanPrecheckWiring(source);
    expect(
      violations,
      `pre-check wiring violations:\n${violations.map((v) => `  [${v.rule}] ${v.why}`).join('\n')}`,
    ).toEqual([]);
  });

  it('keeps both rules in force', () => {
    expect(PRECHECK_RULE_IDS).toEqual(['precheck-runs-on-choice', 'submit-consults-precheck']);
  });
});

/**
 * The half that shows the guard fires. Each case is `W12-WEB`'s `b8.json` substitution,
 * byte for byte, applied in memory. Nothing tracked is edited.
 */
describe('the scanner goes red on W12-WEB’s two surviving mutations', () => {
  const source = readText(FORM_PATH);

  const cases: ReadonlyArray<{ id: string; rule: PrecheckRuleId; from: string; to: string }> = [
    {
      id: 'U-04 the upload form stops pre-checking the chosen file',
      rule: 'precheck-runs-on-choice',
      from: '    setPrecheck(chosen === null ? null : precheckUploadFile(chosen));',
      to: '    setPrecheck(null);',
    },
    {
      id: 'U-05 the upload form submits a file the pre-check refused',
      rule: 'submit-consults-precheck',
      from: '    if (file === null || precheck !== null) return;',
      to: '    if (file === null) return;',
    },
  ];

  it.each(cases)('$id is reported', ({ rule, from, to }) => {
    // The substitution must still apply to today's source; if the form is refactored so
    // that it does not, this assertion says so rather than silently testing nothing.
    expect(source.split(from).length - 1, `the mutated text is no longer in the form:\n${from}`).toBe(1);

    const mutated = source.replace(from, to);
    expect(mutated).not.toBe(source);

    const violations = scanPrecheckWiring(mutated);
    expect(violations.map((v) => v.rule)).toContain(rule);
  });

  it('reports nothing on the unmutated source, so the cases above are not always-red', () => {
    expect(scanPrecheckWiring(source)).toEqual([]);
  });

  it('reports the pre-check rule when the call is removed entirely', () => {
    const mutated = source.replace(
      'setPrecheck(chosen === null ? null : precheckUploadFile(chosen));',
      'setPrecheck(null);',
    );
    expect(scanPrecheckWiring(mutated).map((v) => v.rule)).toEqual(['precheck-runs-on-choice']);
  });
});
