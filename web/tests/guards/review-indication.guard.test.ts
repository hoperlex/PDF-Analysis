/**
 * Every string that tells a reader «a human did not review this» goes through the one switch
 * (`REVIEW-INDICATION-SWITCH-01`, `R-146ba`, accepted risks `A-10`, `A-11`).
 *
 * ## Why this reads source
 *
 * The per-state tests (`tests/unit/review-indication/`) prove the strings that exist today. They
 * cannot prove that the NEXT string of this kind, added to an AR v3 view next month, goes behind
 * the switch: that is a property of the source. So this guard parses each owned file with the
 * TypeScript compiler, takes every string literal, template part, JSX text and JSX attribute
 * string, and for each one that reads as «provisional», «needs the expert's check» or «no person
 * reviewed it» asks one question: is it inside the branch of an `?:`, an `if` or an `&&` whose
 * condition is the constant `SHOW_REVIEW_INDICATION` (or its negation, for the other branch)? If
 * not, the string is reported. Nothing is exempt except the entries of `ALLOWED_UNGATED`, each of
 * which carries the reason.
 *
 * ## What it deliberately does not catch
 *
 * It sees wording, not meaning: a sentence that says the same thing in other words passes. The
 * word list below is closed and written out, so what the guard can and cannot see is readable.
 * Comments and identifiers are not strings and are not read.
 *
 * ## What stays out of the switch
 *
 * The label above the version-comparison summary, the attestation record of the sealed pack and the
 * statements that a verdict is the expert's own decision are NOT behind the switch (owner and
 * integrator rule). The second half of this file holds them out: none of their files reads the
 * constant.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT, repoRelative, walkFiles } from './lib/repo';

/**
 * The wording the owner took off the screens, as a closed pattern: «предварительн…» (provisional),
 * «проверк… эксперт…» and «проверк… человек…» (a check by the expert, by a person), and «экспертн…
 * проверк…» (an expert check). `\p{L}*` takes the ending.
 */
const INDICATION = /предварительн|проверк\p{L}*\s+(?:эксперт|человек)|экспертн\p{L}*\s+проверк/iu;

const SWITCH = 'SHOW_REVIEW_INDICATION';
const SWITCH_MODULES: ReadonlySet<string> = new Set(['@/shared/config', '@/shared/config/review-indication']);

/** The trees that draw an AR v3 result or the profile label. Everything under them is read. */
const OWNED_TREES: readonly string[] = [
  'src/widgets/ar-v3-beta-review',
  'src/widgets/ar-v3-beta-pack',
  'src/widgets/ar-v3-beta-status',
  'src/widgets/run-progress',
  'src/features/start-ar-v3-group',
  'src/entities/analysis-profile',
];

/** An indication that is NOT behind the switch, on purpose. Keyed by file, then by the exact text. */
const ALLOWED_UNGATED: Readonly<Record<string, Readonly<Record<string, string>>>> = {
  'src/entities/analysis-profile/model/presentation.ts': {
    'черновик, требует экспертной проверки':
      'the label of a draft profile; the owner removed the label of a reviewed profile only (R-146ba)',
  },
  'src/widgets/ar-v3-beta-pack/model/pack-presentation.ts': {
    'остаются предварительными и требуют проверки эксперта.':
      'the attestation record of the sealed pack, as «Настройки анализа» shows it (integrator rule)',
  },
};

/** Files that must never read the switch: what it does not govern. */
const NEVER_GATED: readonly string[] = [
  'src/entities/version-comparison/ui/comparison-summary.tsx',
  'src/entities/version-comparison/model/summary.ts',
  'src/widgets/ar-v3-beta-pack/model/pack-presentation.ts',
  'src/widgets/ar-v3-beta-pack/ui/ar-v3-beta-pack.tsx',
  'src/widgets/ar-v3-beta-review/ui/run-findings.tsx',
  'src/widgets/ar-v3-beta-review/model/may-decide.ts',
];

/** The files allowed to name the switch at all: the module, its index and the owners above. */
const MAY_NAME_THE_SWITCH: readonly string[] = [
  'src/shared/config/review-indication.ts',
  'src/shared/config/index.ts',
  'src/entities/analysis-profile/model/presentation.ts',
  'src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx',
  'src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx',
  'src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx',
  'src/widgets/run-progress/ui/run-progress.tsx',
];

interface Reading {
  /** Strings that read as an indication and are outside the switch. */
  readonly ungated: readonly { readonly text: string; readonly line: number }[];
  /** Strings that read as an indication and are inside it. */
  readonly gated: number;
  /** The file names the switch somewhere other than its import. */
  readonly usesSwitch: boolean;
  /** Findings about the switch itself: no import, or a local declaration of the same name. */
  readonly faults: readonly string[];
}

function kindOf(fileName: string): ts.ScriptKind {
  return fileName.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
}

function stripParens(node: ts.Expression): ts.Expression {
  let current = node;
  while (ts.isParenthesizedExpression(current)) current = current.expression;
  return current;
}

/** Whether `expression` is the switch itself (`positive`) or its negation (`!positive`). */
function isSwitch(expression: ts.Expression, positive: boolean): boolean {
  const inner = stripParens(expression);
  if (positive) return ts.isIdentifier(inner) && inner.text === SWITCH;
  return ts.isPrefixUnaryExpression(inner)
    && inner.operator === ts.SyntaxKind.ExclamationToken
    && isSwitch(inner.operand, true);
}

/** Whether `node` is inside the branch the switch selects. */
function isGated(node: ts.Node): boolean {
  let child: ts.Node = node;
  for (let parent = node.parent; parent !== undefined; child = parent, parent = parent.parent) {
    if (ts.isConditionalExpression(parent)) {
      if (child === parent.whenTrue && isSwitch(parent.condition, true)) return true;
      if (child === parent.whenFalse && isSwitch(parent.condition, false)) return true;
    } else if (ts.isIfStatement(parent)) {
      if (child === parent.thenStatement && isSwitch(parent.expression, true)) return true;
      if (child === parent.elseStatement && isSwitch(parent.expression, false)) return true;
    } else if (
      ts.isBinaryExpression(parent)
      && parent.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken
      && child === parent.right
      && isSwitch(parent.left, true)
    ) {
      return true;
    }
  }
  return false;
}

/** The text a node contributes to a screen, or `null` when it is not a string-bearing node. */
function stringOf(node: ts.Node): string | null {
  if (ts.isStringLiteral(node)) {
    const holder = node.parent;
    if (holder !== undefined && (ts.isImportDeclaration(holder) || ts.isExportDeclaration(holder))) return null;
    return node.text;
  }
  if (ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node)) return node.text;
  if (ts.isJsxText(node)) return node.containsOnlyTriviaWhiteSpaces ? null : node.text.replace(/\s+/g, ' ').trim();
  return null;
}

function readSource(fileName: string, source: string): Reading {
  const file = ts.createSourceFile(fileName, source, ts.ScriptTarget.ES2022, true, kindOf(fileName));
  const allowed = ALLOWED_UNGATED[fileName] ?? {};
  const ungated: { text: string; line: number }[] = [];
  const faults: string[] = [];
  let gated = 0;
  let usesSwitch = false;
  let importsSwitch = false;

  const visit = (node: ts.Node): void => {
    if (ts.isImportDeclaration(node)) {
      const clause = node.importClause;
      const bindings = clause?.namedBindings;
      if (
        ts.isStringLiteral(node.moduleSpecifier)
        && SWITCH_MODULES.has(node.moduleSpecifier.text)
        && bindings !== undefined
        && ts.isNamedImports(bindings)
        && bindings.elements.some((element) => element.name.text === SWITCH && element.propertyName === undefined)
      ) importsSwitch = true;
    } else if (ts.isExportDeclaration(node)) {
      // `export { SHOW_REVIEW_INDICATION } from './review-indication'` is the index re-exporting it.
    } else if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.name.text === SWITCH) {
      if (fileName !== 'src/shared/config/review-indication.ts') faults.push(`declares its own ${SWITCH}`);
    } else if (ts.isIdentifier(node) && node.text === SWITCH) {
      const holder = node.parent;
      const inImportOrExport = holder !== undefined
        && (ts.isImportSpecifier(holder) || ts.isExportSpecifier(holder) || ts.isVariableDeclaration(holder));
      if (!inImportOrExport) usesSwitch = true;
    }

    const text = stringOf(node);
    if (text !== null && INDICATION.test(text)) {
      if (isGated(node)) gated += 1;
      else if (!Object.hasOwn(allowed, text)) {
        ungated.push({ text, line: file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1 });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);

  if (usesSwitch && !importsSwitch) faults.push(`reads ${SWITCH} without importing it from @/shared/config`);
  return { ungated, gated, usesSwitch, faults };
}

function readFile(relativePath: string): string {
  return readFileSync(join(WEB_ROOT, relativePath), 'utf8');
}

function ownedFiles(): string[] {
  return OWNED_TREES.flatMap((tree) =>
    walkFiles(join(WEB_ROOT, tree), (path) => /\.(?:ts|tsx)$/.test(path)).map((path) => repoRelative(path).replace(/^web\//, '')),
  );
}

describe('every indication of «no human reviewed this» is behind the switch', () => {
  const files = ownedFiles();
  const readings = new Map(files.map((file) => [file, readSource(file, readFile(file))] as const));

  it('reads the owned trees: the scan is not vacuous', () => {
    expect(files.length).toBeGreaterThanOrEqual(20);
    for (const required of [
      'src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx',
      'src/widgets/ar-v3-beta-review/ui/run-findings.tsx',
      'src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx',
      'src/widgets/ar-v3-beta-pack/model/pack-presentation.ts',
      'src/widgets/run-progress/ui/run-progress.tsx',
      'src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx',
      'src/entities/analysis-profile/model/presentation.ts',
    ]) expect(files, required).toContain(required);
  });

  it('finds no indication outside the switch in any owned file', () => {
    const outside = [...readings].flatMap(([file, reading]) =>
      reading.ungated.map((entry) => `${file}:${entry.line} «${entry.text}»`));
    expect(outside).toEqual([]);
  });

  it('finds the gated strings where they are (the counts are minimums, so a removed string is noticed)', () => {
    const gatedIn = (file: string): number => readings.get(file)?.gated ?? 0;
    expect(gatedIn('src/entities/analysis-profile/model/presentation.ts')).toBeGreaterThanOrEqual(1);
    expect(gatedIn('src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx')).toBeGreaterThanOrEqual(8);
    expect(gatedIn('src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx')).toBeGreaterThanOrEqual(5);
    expect(gatedIn('src/widgets/run-progress/ui/run-progress.tsx')).toBeGreaterThanOrEqual(6);
    expect(gatedIn('src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx')).toBeGreaterThanOrEqual(1);
  });

  it('has no fault in how a file reads the switch (no local copy, no missing import)', () => {
    const faulty = [...readings].flatMap(([file, reading]) => reading.faults.map((fault) => `${file}: ${fault}`));
    expect(faulty).toEqual([]);
  });

  it('keeps every allowed ungated string where it was allowed, and says why', () => {
    for (const [file, entries] of Object.entries(ALLOWED_UNGATED)) {
      const source = readFile(file);
      for (const [text, reason] of Object.entries(entries)) {
        expect(source, `${file}: ${text}`).toContain(text);
        expect(reason.length, `${file}: ${text}`).toBeGreaterThan(20);
      }
    }
  });
});

describe('what the switch does not govern never reads it', () => {
  it('names the switch in no file of the never-gated list', () => {
    for (const file of NEVER_GATED) {
      const reading = readSource(file, readFile(file));
      expect(reading.usesSwitch, file).toBe(false);
      expect(readFile(file), file).not.toContain(SWITCH);
    }
  });

  it('still holds the sentences the owner and the integrator kept', () => {
    expect(readFile('src/entities/version-comparison/ui/comparison-summary.tsx'))
      .toContain('проверка человеком не проводится');
    expect(readFile('src/widgets/ar-v3-beta-pack/model/pack-presentation.ts'))
      .toContain('остаются предварительными и требуют проверки эксперта.');
    expect(readFile('src/widgets/ar-v3-beta-review/ui/run-findings.tsx'))
      .toContain('Формулировка модели, не решение эксперта.');
  });
});

describe('there is one switch', () => {
  const everything = walkFiles(join(WEB_ROOT, 'src'), (path) => /\.(?:ts|tsx)$/.test(path))
    .map((path) => repoRelative(path).replace(/^web\//, ''));

  it('is declared once, as one exported constant, in shared/config', () => {
    const declared = everything.filter((file) => /export\s+const\s+SHOW_REVIEW_INDICATION\b/.test(readFile(file)));
    expect(declared).toEqual(['src/shared/config/review-indication.ts']);
    const reading = readSource('src/shared/config/review-indication.ts', readFile('src/shared/config/review-indication.ts'));
    expect(reading.faults).toEqual([]);
    expect(readFile('src/shared/config/index.ts')).toContain("export { SHOW_REVIEW_INDICATION } from './review-indication';");
  });

  it('is named only by the module, its index and the presentation owners of the screens', () => {
    const naming = everything.filter((file) => readFile(file).includes(SWITCH)).sort();
    expect(naming).toEqual([...MAY_NAME_THE_SWITCH].sort());
  });

  it('is not read from the environment or from a second flag', () => {
    for (const file of everything) {
      const source = readFile(file);
      expect(source, file).not.toMatch(/process\.env[^\n]*REVIEW/);
      expect(source, file).not.toMatch(/\bSHOW_(?!REVIEW_INDICATION\b)[A-Z_]*(?:REVIEW|INDICATION)[A-Z_]*\b/);
    }
  });
});

describe('the guard can fail', () => {
  const view = 'src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx';
  const head = `import { SHOW_REVIEW_INDICATION } from '@/shared/config';\n`;
  const read = (body: string, file = view): Reading => readSource(file, head + body);

  it('reports a bare string literal', () => {
    expect(read(`export const a = 'Требуется проверка эксперта';`).ungated).toHaveLength(1);
  });

  it('reports a bare JSX text and a bare JSX attribute', () => {
    expect(read(`export const a = <p>Все пункты требуют проверки эксперта.</p>;`).ungated).toHaveLength(1);
    expect(read(`export const a = <p title="Предварительный разбор">x</p>;`).ungated).toHaveLength(1);
  });

  it('reports a template literal, with or without a substitution', () => {
    expect(read('export const a = `предварительные цитаты`;').ungated).toHaveLength(1);
    expect(read('export const a = (n: number) => `Тем: ${n}; предварительные ссылки`;').ungated).toHaveLength(1);
  });

  it('accepts the branch the switch selects, in all the forms the tree uses', () => {
    const forms = [
      `export const a = SHOW_REVIEW_INDICATION ? 'Предварительный разбор' : 'Разбор';`,
      `export const a = !SHOW_REVIEW_INDICATION ? 'Разбор' : 'Предварительный разбор';`,
      `export const a = (SHOW_REVIEW_INDICATION) ? 'Предварительный разбор' : 'Разбор';`,
      `export const a = SHOW_REVIEW_INDICATION && 'Предварительный разбор';`,
      `export function a(x: boolean) { if (SHOW_REVIEW_INDICATION) { return x ? 'Предварительный разбор' : 'Другое'; } return 'Разбор'; }`,
      `export function a() { if (!SHOW_REVIEW_INDICATION) { return 'Разбор'; } else { return 'Предварительный разбор'; } }`,
      `export const a = SHOW_REVIEW_INDICATION ? <p>Требуется проверка эксперта.</p> : <p>Готово.</p>;`,
      `export const a = SHOW_REVIEW_INDICATION ? <p title="Предварительный">x</p> : <p>y</p>;`,
    ];
    for (const form of forms) {
      const reading = read(form);
      expect(reading.ungated, form).toEqual([]);
      expect(reading.gated, form).toBe(1);
      expect(reading.faults, form).toEqual([]);
    }
  });

  it('reports the string when the switch is not what the condition tests', () => {
    const mutated = [
      `export const a = true ? 'Предварительный разбор' : 'Разбор';`,
      `export const a = flag ? 'Предварительный разбор' : 'Разбор';`,
      `export const a = SHOW_REVIEW_INDICATION || flag ? 'Предварительный разбор' : 'Разбор';`,
      `export const a = !!SHOW_REVIEW_INDICATION ? 'Предварительный разбор' : 'Разбор';`,
      `export const a = flag && 'Предварительный разбор';`,
      `export function a(flag: boolean) { if (flag) { return 'Предварительный разбор'; } return 'Разбор'; }`,
    ];
    for (const form of mutated) expect(read(form).ungated, form).toHaveLength(1);
  });

  it('reports the string when it sits in the branch the switch does NOT select, or in the condition', () => {
    expect(read(`export const a = SHOW_REVIEW_INDICATION ? 'Разбор' : 'Предварительный разбор';`).ungated).toHaveLength(1);
    expect(read(`export const a = !SHOW_REVIEW_INDICATION ? 'Предварительный разбор' : 'Разбор';`).ungated).toHaveLength(1);
    expect(read(`export const a = ('Предварительный разбор' && SHOW_REVIEW_INDICATION) ? 'x' : 'y';`).ungated).toHaveLength(1);
  });

  it('reports a local copy of the switch and a read with no import', () => {
    expect(readSource(view, `const SHOW_REVIEW_INDICATION = true;\nexport const a = SHOW_REVIEW_INDICATION ? 'Предварительный разбор' : 'Разбор';`).faults)
      .toEqual([`declares its own ${SWITCH}`, `reads ${SWITCH} without importing it from @/shared/config`]);
    expect(readSource(view, `export const a = SHOW_REVIEW_INDICATION ? 'Предварительный разбор' : 'Разбор';`).faults)
      .toEqual([`reads ${SWITCH} without importing it from @/shared/config`]);
    expect(readSource(view, `import { SHOW_REVIEW_INDICATION } from './elsewhere';\nexport const a = SHOW_REVIEW_INDICATION ? 'x' : 'y';`).faults)
      .toEqual([`reads ${SWITCH} without importing it from @/shared/config`]);
  });

  it('allows an allowlisted text only in the file it is allowed in', () => {
    const attestation = `export const a = 'остаются предварительными и требуют проверки эксперта.';`;
    expect(readSource('src/widgets/ar-v3-beta-pack/model/pack-presentation.ts', attestation).ungated).toEqual([]);
    expect(readSource(view, attestation).ungated).toHaveLength(1);
    expect(readSource('src/widgets/ar-v3-beta-pack/model/pack-presentation.ts', `export const a = 'Предварительный разбор';`).ungated)
      .toHaveLength(1);
  });

  it('ignores words that are not the removed wording, a module specifier and a comment', () => {
    const quiet = [
      `export const a = 'Формулировка модели, не решение эксперта.';`,
      `export const a = 'Решение записывает эксперт.';`,
      `export const a = 'Полный проверенный результат не подтверждён.';`,
      `// Предварительный разбор, требует проверки эксперта\nexport const a = 1;`,
      `import x from './предварительный';\nexport const a = x;`,
    ];
    for (const form of quiet) expect(read(form).ungated, form).toEqual([]);
  });
});
