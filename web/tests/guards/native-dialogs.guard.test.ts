/**
 * Guard: nothing under `web/src` opens the browser's own `alert`, `confirm` or `prompt` (`UIP-G-04`, `UIC-G-15`).
 *
 * A native dialog is outside the product: it takes none of the product's tokens, it cannot be tested in
 * the page, it blocks the thread, and a browser may swallow it. A question or a notice is the shared
 * window (`Dialog` in `@/shared/ui`) or an inline note; this guard says so when a new call appears.
 *
 * ## Why it reads the syntax tree and not the text
 *
 * `confirm(` is also the name of a perfectly good local function: `archive-group-control.tsx` declares
 * `async function confirm()` and calls it from its button, and four other files do the same. A text search
 * for `confirm(` would be red on all of them, and a guard that is red on the tree as it stands is switched
 * off the day it is written. So each file is parsed with the TypeScript compiler and a name is the browser's
 * only when NO declaration in scope — a function, a variable, a parameter, an import, a class, a catch
 * variable — binds it. What it takes for the browser's:
 *
 * - a bare `alert`, `confirm` or `prompt` that nothing binds, called or passed on (`onClick={confirm}`);
 * - the same names read off the global object: `window.confirm`, `globalThis.alert`, `self.prompt`,
 *   `window.top.alert`, `document.defaultView.confirm`, `window['confirm']`;
 * - a destructuring of the global object that takes one of the names (`const { confirm } = window`);
 * - the same through a name the file bound to the global object (`const w = window; w.confirm(...)`).
 *
 * A `window` that a file binds itself (a parameter, a local) is not the global object. Comments, strings,
 * JSX attribute names (`role="alert"`), property names and methods of other objects (`modal.confirm()`,
 * `props.confirm`) are not reads of the name.
 *
 * ## What it does not see
 *
 * An alias that is built through a call or a conditional (`getWindow().confirm`), `eval` and `new Function`,
 * an assignment pattern on an existing variable (`({ confirm } = window)`), and a computed read whose key is not a
 * string literal (`window[kind]`). The last is left alone on purpose: the server-side registries of `app/bff/session` are
 * `globalThis[SYMBOL_KEY]`, the same shape, and a key that is a variable cannot be read without running the code. None of
 * them is in the tree, and ESLint's `no-restricted-globals` cannot see them either.
 *
 * The second half runs the same scanner over in-memory files that break each rule and over files that
 * look like breaking it and do not, so the guard is shown to fire and to hold its fire.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT, repoRelative, walkFiles } from './lib/repo';

const NATIVE_NAMES: ReadonlySet<string> = new Set(['alert', 'confirm', 'prompt']);
const GLOBAL_OBJECTS: ReadonlySet<string> = new Set(['window', 'globalThis', 'self', 'top', 'parent', 'frames']);

export type NativeDialogForm = 'bare' | 'member' | 'element' | 'destructured';

export interface SourceText {
  readonly path: string;
  readonly text: string;
}

export interface NativeDialogUse {
  readonly path: string;
  readonly line: number;
  readonly name: string;
  readonly form: NativeDialogForm;
}

/** A call of a local function that carries one of the names: seen, resolved, and not a finding. */
export interface LocalCall {
  readonly path: string;
  readonly line: number;
  readonly name: string;
}

export interface NativeDialogScan {
  readonly native: readonly NativeDialogUse[];
  readonly local: readonly LocalCall[];
}

// ------------------------------------------------------------------------------------------ scopes

function bindingNames(name: ts.BindingName, into: Set<string>): void {
  if (ts.isIdentifier(name)) {
    into.add(name.text);
    return;
  }
  for (const element of name.elements) {
    if (ts.isBindingElement(element)) bindingNames(element.name, into);
  }
}

/** The names one statement declares in its own block. `var` is the function's and is taken apart from this. */
function declaredBy(statement: ts.Statement, into: Set<string>): void {
  if (ts.isVariableStatement(statement)) {
    if ((statement.declarationList.flags & ts.NodeFlags.BlockScoped) !== 0) {
      for (const declaration of statement.declarationList.declarations) bindingNames(declaration.name, into);
    }
  } else if (ts.isFunctionDeclaration(statement) || ts.isClassDeclaration(statement) || ts.isEnumDeclaration(statement)) {
    if (statement.name !== undefined) into.add(statement.name.text);
  } else if (ts.isModuleDeclaration(statement)) {
    if (ts.isIdentifier(statement.name)) into.add(statement.name.text);
  } else if (ts.isImportEqualsDeclaration(statement)) {
    into.add(statement.name.text);
  } else if (ts.isImportDeclaration(statement)) {
    const clause = statement.importClause;
    if (clause === undefined) return;
    if (clause.name !== undefined) into.add(clause.name.text);
    const bindings = clause.namedBindings;
    if (bindings === undefined) return;
    if (ts.isNamespaceImport(bindings)) into.add(bindings.name.text);
    else for (const element of bindings.elements) into.add(element.name.text);
  }
}

/** Every `var` under `node`, without entering a nested function: `var` belongs to the function that holds it. */
function hoistedVars(node: ts.Node, into: Set<string>): void {
  const visit = (child: ts.Node): void => {
    if (ts.isFunctionLike(child) || ts.isClassLike(child)) return;
    if (ts.isVariableDeclarationList(child) && (child.flags & ts.NodeFlags.BlockScoped) === 0) {
      for (const declaration of child.declarations) bindingNames(declaration.name, into);
    }
    ts.forEachChild(child, visit);
  };
  ts.forEachChild(node, visit);
}

/** The names a node brings into scope for everything inside it, or `null` when it opens no scope. */
function scopeOf(node: ts.Node): Set<string> | null {
  if (ts.isSourceFile(node)) {
    const names = new Set<string>();
    for (const statement of node.statements) declaredBy(statement, names);
    hoistedVars(node, names);
    return names;
  }
  if (ts.isBlock(node) || ts.isModuleBlock(node)) {
    const names = new Set<string>();
    for (const statement of node.statements) declaredBy(statement, names);
    return names;
  }
  if (ts.isCaseBlock(node)) {
    const names = new Set<string>();
    for (const clause of node.clauses) for (const statement of clause.statements) declaredBy(statement, names);
    return names;
  }
  if (ts.isFunctionLike(node) && !ts.isTypeNode(node)) {
    const names = new Set<string>();
    for (const parameter of node.parameters) bindingNames(parameter.name, names);
    if (ts.isFunctionExpression(node) && node.name !== undefined) names.add(node.name.text);
    const body = (node as ts.FunctionLikeDeclaration).body;
    if (body !== undefined) hoistedVars(body, names);
    return names;
  }
  if (ts.isClassExpression(node) && node.name !== undefined) return new Set([node.name.text]);
  if (ts.isForStatement(node) || ts.isForInStatement(node) || ts.isForOfStatement(node)) {
    const initializer = node.initializer;
    if (initializer !== undefined && ts.isVariableDeclarationList(initializer) && (initializer.flags & ts.NodeFlags.BlockScoped) !== 0) {
      const names = new Set<string>();
      for (const declaration of initializer.declarations) bindingNames(declaration.name, names);
      return names;
    }
    return null;
  }
  if (ts.isCatchClause(node) && node.variableDeclaration !== undefined) {
    const names = new Set<string>();
    bindingNames(node.variableDeclaration.name, names);
    return names;
  }
  return null;
}

const bound = (chain: readonly ReadonlySet<string>[], name: string): boolean => chain.some((scope) => scope.has(name));

// ------------------------------------------------------------------------------------- references

/** Is this identifier a READ of a binding, rather than the name of a declaration, a property or a tag? */
function isReference(id: ts.Identifier): boolean {
  const parent = id.parent;
  if (ts.isPropertyAccessExpression(parent)) return parent.expression === id;
  if (ts.isQualifiedName(parent)) return parent.left === id;
  if (ts.isPropertyAssignment(parent) || ts.isPropertyDeclaration(parent) || ts.isBindingElement(parent)) {
    return parent.initializer === id;
  }
  if (ts.isVariableDeclaration(parent) || ts.isParameter(parent)) return parent.initializer === id;
  if (
    ts.isMethodDeclaration(parent) || ts.isMethodSignature(parent) || ts.isPropertySignature(parent) ||
    ts.isGetAccessorDeclaration(parent) || ts.isSetAccessorDeclaration(parent) || ts.isEnumMember(parent) ||
    ts.isFunctionDeclaration(parent) || ts.isFunctionExpression(parent) || ts.isClassDeclaration(parent) ||
    ts.isClassExpression(parent) || ts.isImportClause(parent) || ts.isImportSpecifier(parent) ||
    ts.isNamespaceImport(parent) || ts.isExportSpecifier(parent) || ts.isImportEqualsDeclaration(parent) ||
    ts.isJsxAttribute(parent) || ts.isJsxOpeningElement(parent) || ts.isJsxClosingElement(parent) ||
    ts.isJsxSelfClosingElement(parent) || ts.isLabeledStatement(parent) || ts.isBreakOrContinueStatement(parent) ||
    ts.isTypeReferenceNode(parent) || ts.isTypeQueryNode(parent) || ts.isTypeParameterDeclaration(parent) ||
    ts.isMetaProperty(parent) || ts.isNamespaceExport(parent) || ts.isModuleDeclaration(parent) ||
    ts.isInterfaceDeclaration(parent) || ts.isTypeAliasDeclaration(parent) || ts.isEnumDeclaration(parent) ||
    ts.isNamedTupleMember(parent) || ts.isTypePredicateNode(parent) || ts.isExpressionWithTypeArguments(parent)
  ) {
    return false;
  }
  return true;
}

function unwrap(expression: ts.Expression): ts.Expression {
  let current = expression;
  while (
    ts.isParenthesizedExpression(current) || ts.isAsExpression(current) || ts.isNonNullExpression(current) ||
    ts.isTypeAssertionExpression(current) || ts.isSatisfiesExpression(current)
  ) {
    current = current.expression;
  }
  return current;
}

function stringKey(node: ts.Expression): string | null {
  return ts.isStringLiteralLike(node) ? node.text : null;
}

// ------------------------------------------------------------------------------------------ scan

const KINDS: Readonly<Record<string, ts.ScriptKind>> = {
  '.ts': ts.ScriptKind.TS,
  '.tsx': ts.ScriptKind.TSX,
  '.js': ts.ScriptKind.JS,
  '.jsx': ts.ScriptKind.JSX,
  '.mjs': ts.ScriptKind.JS,
};

function scanFile(file: SourceText, native: NativeDialogUse[], local: LocalCall[]): void {
  const extension = file.path.slice(file.path.lastIndexOf('.'));
  const kind = KINDS[extension];
  if (kind === undefined) return;
  const tree = ts.createSourceFile(file.path, file.text, ts.ScriptTarget.Latest, true, kind);
  const lineOf = (node: ts.Node): number => tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1;

  // Names the file binds to the global object (`const w = window`), found before the check so order does not matter.
  const aliases = new Set<string>();
  const isGlobalObject = (expression: ts.Expression, chain: readonly ReadonlySet<string>[], useAliases: boolean): boolean => {
    const inner = unwrap(expression);
    if (ts.isIdentifier(inner)) {
      if (useAliases && aliases.has(inner.text)) return true;
      return GLOBAL_OBJECTS.has(inner.text) && !bound(chain, inner.text);
    }
    if (ts.isPropertyAccessExpression(inner)) {
      if (inner.name.text === 'defaultView' && ts.isIdentifier(unwrap(inner.expression))) {
        const owner = unwrap(inner.expression) as ts.Identifier;
        return owner.text === 'document' && !bound(chain, 'document');
      }
      return GLOBAL_OBJECTS.has(inner.name.text) && isGlobalObject(inner.expression, chain, useAliases);
    }
    return false;
  };

  const collect = (node: ts.Node, chain: readonly ReadonlySet<string>[]): void => {
    const own = scopeOf(node);
    const here = own === null ? chain : [...chain, own];
    if (
      ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer !== undefined &&
      isGlobalObject(node.initializer, here, false)
    ) {
      aliases.add(node.name.text);
    }
    ts.forEachChild(node, (child) => collect(child, here));
  };
  collect(tree, []);

  const found = (node: ts.Node, name: string, form: NativeDialogForm): void => {
    native.push({ path: file.path, line: lineOf(node), name, form });
  };

  const visit = (node: ts.Node, chain: readonly ReadonlySet<string>[]): void => {
    const own = scopeOf(node);
    const here = own === null ? chain : [...chain, own];

    if (ts.isIdentifier(node) && NATIVE_NAMES.has(node.text) && isReference(node)) {
      if (!bound(here, node.text)) found(node, node.text, 'bare');
      else if (ts.isCallExpression(node.parent) && node.parent.expression === node) {
        local.push({ path: file.path, line: lineOf(node), name: node.text });
      }
    } else if (ts.isPropertyAccessExpression(node)) {
      if (NATIVE_NAMES.has(node.name.text) && isGlobalObject(node.expression, here, true)) {
        found(node, node.name.text, 'member');
      }
    } else if (ts.isElementAccessExpression(node)) {
      if (isGlobalObject(node.expression, here, true)) {
        const key = stringKey(node.argumentExpression);
        if (key !== null && NATIVE_NAMES.has(key)) found(node, key, 'element');
      }
    } else if (
      ts.isVariableDeclaration(node) && ts.isObjectBindingPattern(node.name) && node.initializer !== undefined &&
      isGlobalObject(node.initializer, here, true)
    ) {
      for (const element of node.name.elements) {
        const property = element.propertyName ?? element.name;
        const name = ts.isIdentifier(property) || ts.isStringLiteralLike(property) ? property.text : null;
        if (name !== null && NATIVE_NAMES.has(name)) found(element, name, 'destructured');
      }
    }
    ts.forEachChild(node, (child) => visit(child, here));
  };
  visit(tree, []);
}

/** Every use of the browser's `alert`, `confirm` or `prompt` in the supplied files, and every local look-alike it set aside. */
export function scanNativeDialogs(files: readonly SourceText[]): NativeDialogScan {
  const native: NativeDialogUse[] = [];
  const local: LocalCall[] = [];
  for (const file of [...files].sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0))) {
    scanFile(file, native, local);
  }
  return { native, local };
}

const describeUse = (use: NativeDialogUse): string => `  ${use.path}:${use.line}  ${use.name}  (${use.form})`;

// ============================================================================== the real tree

const SRC = join(WEB_ROOT, 'src');

const sources: SourceText[] = walkFiles(SRC, (path) => /\.(?:tsx?|jsx?|mjs)$/.test(path) && !path.endsWith('.d.ts')).map((path) => ({
  path: repoRelative(path),
  text: readFileSync(path, 'utf8'),
}));

describe('the browser\'s own dialogs are not used under web/src', () => {
  const scan = scanNativeDialogs(sources);

  it('scans a non-trivial tree, so a broken walk cannot pass vacuously', () => {
    expect(sources.length).toBeGreaterThan(300);
    expect(sources.some((source) => source.path === 'web/src/shared/ui/dialog.tsx')).toBe(true);
  });

  it('finds no alert, confirm or prompt of the browser', () => {
    expect(
      scan.native.map(describeUse),
      'the browser\'s own dialog is outside the product. Use `Dialog` from `@/shared/ui` for a question, or an inline note ' +
        'for a notice. A local function that merely has this name is not a finding: a name that a declaration in scope binds is local.',
    ).toEqual([]);
  });

  it('sees the local functions that carry the names and sets them aside, so a text search would have been red', () => {
    // `archive-group-control.tsx` declares `async function confirm()` and calls it from a button.
    expect(scan.local.length, 'no local call of the three names was resolved, so the scope reading is untested here').toBeGreaterThan(0);
    expect(new Set(scan.local.map((call) => call.name))).toContain('confirm');
  });
});

// ======================================================================= the guard can fail

function violations(text: string, path = 'web/src/probe/ui/probe.tsx'): NativeDialogUse[] {
  return [...scanNativeDialogs([{ path, text }]).native];
}

const forms = (text: string): string[] => violations(text).map((use) => `${use.name}:${use.form}`);

describe('the scanner fires on each way of opening a native dialog', () => {
  const BREAKS: readonly (readonly [string, string, readonly string[]])[] = [
    ['window.alert', "window.alert('x');", ['alert:member']],
    ['window.confirm in a condition', "function f() { if (!window.confirm('Удалить?')) return; }", ['confirm:member']],
    ['window.prompt', "const name = window.prompt('Имя');", ['prompt:member']],
    ['globalThis', "globalThis.confirm('x');", ['confirm:member']],
    ['self', "self.alert('x');", ['alert:member']],
    ['window.top', "window.top.alert('x');", ['alert:member']],
    ['window.parent, optional', "window.parent?.confirm?.('x');", ['confirm:member']],
    ['document.defaultView', "document.defaultView?.confirm('x');", ['confirm:member']],
    ['a bare alert', "function f() { alert('x'); }", ['alert:bare']],
    ['a bare confirm in an arrow', "const f = () => confirm('x');", ['confirm:bare']],
    ['a bare confirm in a condition', "function f() { if (!confirm('x')) return; }", ['confirm:bare']],
    ['a bare prompt', "const v = prompt('x', '');", ['prompt:bare']],
    ['a string-literal element read', "window['confirm']('x');", ['confirm:element']],
    ['a destructuring of window', "const { confirm } = window; confirm('x');", ['confirm:destructured']],
    ['a renamed destructuring', "const { alert: ask } = globalThis; ask('x');", ['alert:destructured']],
    ['a property taken off window', "const ask = window.confirm; ask('x');", ['confirm:member']],
    ['window.confirm.call', "window.confirm.call(window, 'x');", ['confirm:member']],
    ['a bare name passed as a handler', 'const A = () => <button onClick={confirm}>x</button>;', ['confirm:bare']],
    ['an alias of window', "const w = window; w.confirm('x');", ['confirm:member']],
    ['an alias of globalThis', "const g = globalThis; function f() { return g.prompt('x'); }", ['prompt:member']],
    ['a name that is bound in another function only', "function a() { const confirm = 1; return confirm; } function b() { confirm('x'); }", ['confirm:bare']],
    ['a name that is bound in a block that has ended', "{ const confirm = () => 1; confirm(); } confirm('x');", ['confirm:bare']],
    ['a type of that name, which binds no value', "type confirm = string; confirm('x');", ['confirm:bare']],
  ];

  for (const [label, text, expected] of BREAKS) {
    it(`is red on ${label}`, () => {
      expect(forms(text)).toEqual(expected);
    });
  }

  it('reports the line and the file, so a red run says where', () => {
    const [use] = violations("const a = 1;\n\nwindow.alert('x');\n", 'web/src/widgets/x/ui/x.tsx');
    expect(use).toEqual({ path: 'web/src/widgets/x/ui/x.tsx', line: 3, name: 'alert', form: 'member' });
  });

  it('reads each file kind: plain scripts and modules too, and ignores what is not a script', () => {
    expect(violations("window.alert('x');", 'web/src/probe.js')).toHaveLength(1);
    expect(violations("window.alert('x');", 'web/src/probe.mjs')).toHaveLength(1);
    expect(violations("const a = <T,>(x: T) => window.alert('x');", 'web/src/probe.tsx')).toHaveLength(1);
    expect(violations("window.alert('x');", 'web/src/probe.css')).toHaveLength(0);
  });
});

describe('the scanner holds its fire on what only looks like one', () => {
  const FINE: readonly (readonly [string, string])[] = [
    [
      'the archive control: a local function declared in the component and called from a button',
      'export function Control() { async function confirm() { await run(); } return <button onClick={() => void confirm()}>x</button>; }',
    ],
    ['a local const', 'const confirm = () => 1; confirm();'],
    ['a module-level function called from another function', 'function confirm() {} export function f() { confirm(); }'],
    ['an exported function', "export function prompt() { return 1; } prompt();"],
    ['a function declared after its call', 'function f() { alert(); } function alert() {}'],
    ['a parameter', 'function f(confirm: () => void) { confirm(); }'],
    ['a destructured parameter', 'function f({ confirm, alert: raise }: P) { confirm(); raise(); }'],
    ['an arrow parameter', 'const f = (prompt: () => string) => prompt();'],
    ['an import', "import { confirm } from './ask'; confirm();"],
    ['a default import', "import alert from './ask'; alert();"],
    ['a namespace import', "import * as prompt from './ask'; prompt.run();"],
    ['a method of another object', 'props.confirm(); dialog.alert(); modal.prompt({});'],
    ['a method on this', 'class A { confirm() { return 1; } run() { return this.confirm(); } }'],
    ['an object literal member', 'const o = { confirm: () => 1, alert() { return 2; }, prompt: 3 }; o.confirm();'],
    ['a class named like one', 'class prompt {} new prompt();'],
    ['a for-of variable', 'for (const prompt of list) { prompt(); }'],
    ['a catch variable', 'try { run(); } catch (confirm) { confirm(); }'],
    ['a var hoisted from a block of the same function', 'function f() { if (a) { var confirm = () => 1; } confirm(); }'],
    ['a function expression\'s own name', 'const f = function alert() { return alert; };'],
    ['a window the file binds itself: a parameter', "function f(window: Fake) { window.alert('x'); }"],
    ['a window the file binds itself: a local', "const window = fake(); window.confirm('x');"],
    ['an alias of something that is not the global object', "const w = fake; w.confirm('x');"],
    ['an attribute of that name', '<p role="alert" alert prompt="x" confirm={y}>t</p>;'],
    ['a comment', "// window.alert('x') and confirm('x')\n/* window.prompt('x') */\nconst a = 1;"],
    ['a symbol-keyed registry on the global object, as the session store keeps', "const host = globalThis as unknown as Record<symbol, Map<string, string>>; host[KEY] = new Map(); window[kind];"],
    ['a string and a template', "const a = \"window.alert('x')\"; const b = `confirm('x')`;"],
    ['a type', 'type A = { confirm: () => void; alert(): void }; interface I { prompt(): void }'],
    ['a literal element read of something else', "window['location']; document['alert'];"],
    ['a property of another global object', 'localStorage.confirm; navigator.alert;'],
    ['a shorthand property that a local binds', 'const o = { alert }; const alert = 1;'],
  ];

  for (const [label, text] of FINE) {
    it(`is quiet on ${label}`, () => {
      expect(forms(text)).toEqual([]);
    });
  }

  it('records the local calls it set aside, and not the member calls of other objects', () => {
    const scan = scanNativeDialogs([
      {
        path: 'web/src/probe/ui/probe.tsx',
        text: 'function Control() { async function confirm() {} props.confirm(); return <b onClick={() => void confirm()}>x</b>; }',
      },
    ]);
    expect(scan.native).toEqual([]);
    expect(scan.local).toEqual([{ path: 'web/src/probe/ui/probe.tsx', line: 1, name: 'confirm' }]);
  });
});
