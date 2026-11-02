/**
 * WCAG 2.1 contrast, computed from the tokens as declared and from the pairs that
 * actually meet on a rendered screen.
 *
 * `W31-STYLE` closed its report with a named risk: *"the `-light` tints were chosen by
 * eye, no WCAG figure is claimed."* This module is the arithmetic that closes it, and
 * `contrast.test.ts` is the guard. Neither adds a dependency: the formula is ten lines
 * and the pair census is derived from the stylesheet and the rendered markup rather than
 * hand-listed.
 *
 * WHY A CENSUS AND NOT A LIST. A hand-written list of "the pairs that matter" is the
 * `W30-LISTS` class exactly — a hand-maintained subset standing in for a set something
 * else decides, with nothing that fails when the authority grows. The authority here is
 * the stylesheet crossed with the markup: a pair matters when some element carries a
 * `color` token and sits on a `background` token. So the pairs are COMPUTED, every
 * computed pair must be classified, and a classification naming a pair the screens no
 * longer produce is itself a failure. Adding a rule that puts a new ink on a new tint
 * reddens this suite until someone says which threshold it answers to.
 *
 * WHAT THIS IS NOT. It is not a browser. It resolves the cascade for the selector shapes
 * `globals.css` actually uses, and it says so out loud: `unsupported()` returns every
 * selector it declined, and the test asserts that list against what is expected rather
 * than letting a silently-skipped rule read as a passing one.
 */

// ============================================================ 1. the formula (WCAG 2.1)

/** sRGB channel to linear, per WCAG 2.1 relative luminance. */
function linearise(channel: number): number {
  return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

export function parseHex(value: string): readonly [number, number, number] {
  const hex = value.trim().replace(/^#/, '');
  const full = hex.length === 3 ? [...hex].map((c) => c + c).join('') : hex;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) throw new Error(`not a hex colour: ${value}`);
  const channel = (at: number): number => parseInt(full.slice(at, at + 2), 16) / 255;
  return [channel(0), channel(2), channel(4)];
}

export function relativeLuminance(hex: string): number {
  const [r, g, b] = parseHex(hex);
  return 0.2126 * linearise(r) + 0.7152 * linearise(g) + 0.0722 * linearise(b);
}

export function contrastRatio(a: string, b: string): number {
  const [la, lb] = [relativeLuminance(a), relativeLuminance(b)];
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

// ================================================================== 2. the token block

export type TokenName = `--am-${string}`;

/**
 * The palettes this stylesheet declares, and the block each one lives in.
 *
 * `W33-THEME` made the token set TWO sets. Every measurement below therefore answers to a
 * theme: a pair's ratio is a property of the palette, not of the stylesheet, and a census
 * taken over one palette says nothing about the other. What is NOT theme-dependent is the
 * set of pairs — the same elements meet on the same screens whichever values the tokens
 * carry — which is why the same census machinery runs twice rather than twice over.
 */
export const THEMES = ['light', 'dark'] as const;
export type Theme = (typeof THEMES)[number];

/** The block carrying the dark values for an explicit choice. */
export const DARK_SELECTOR = ":root[data-theme='dark']";
/** The block carrying the same values for a visitor who has chosen nothing. */
export const DARK_MEDIA_SELECTOR = ":root:not([data-theme='light'])";

/** Every custom property declared in the first block with this exact selector, by name. */
export function parseTokensIn(css: string, selector: string): Map<TokenName, string> {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const body = new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\}`).exec(stripComments(css));
  if (!body) throw new Error(`no ${selector} block`);
  const out = new Map<TokenName, string>();
  for (const decl of (body[1] ?? '').split(';')) {
    const at = decl.indexOf(':');
    if (at < 0) continue;
    const name = decl.slice(0, at).trim();
    if (name.startsWith('--am-')) out.set(name as TokenName, decl.slice(at + 1).trim());
  }
  return out;
}

/** Every custom property declared in the first `:root` block, by name. */
export function parseTokens(css: string): Map<TokenName, string> {
  return parseTokensIn(css, ':root');
}

function hexOnly(tokens: ReadonlyMap<TokenName, string>): Map<TokenName, string> {
  const out = new Map<TokenName, string>();
  for (const [name, value] of tokens) {
    if (/^#[0-9a-fA-F]{3,8}$/.test(value)) out.set(name, value);
  }
  return out;
}

/** Colour tokens of the default (light) palette: the ones whose value is a hex literal. */
export function colourTokens(css: string): Map<TokenName, string> {
  return hexOnly(parseTokens(css));
}

/** Colour tokens declared in one block, whatever its selector. */
export function colourTokensIn(css: string, selector: string): Map<TokenName, string> {
  return hexOnly(parseTokensIn(css, selector));
}

/**
 * The colour tokens in force under one theme.
 *
 * `dark` is the light set with the dark block laid over it, which is exactly what the
 * cascade does — and it is why a token added to `:root` without a dark value is not a
 * missing token but a LIGHT colour in a dark interface. `theme.test.ts` is the guard that
 * refuses that; this function is deliberately not the one that hides it, so a caller that
 * measures the dark palette measures what a browser would paint.
 */
export function palette(css: string, theme: Theme): Map<TokenName, string> {
  const base = colourTokens(css);
  if (theme === 'light') return base;
  return new Map([...base, ...colourTokensIn(css, DARK_SELECTOR)]);
}

function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, '');
}

// ====================================================================== 3. the rules

export interface Rule {
  readonly selector: string;
  readonly declarations: ReadonlyMap<string, string>;
  readonly order: number;
  readonly origin: string;
}

/**
 * Every rule, in source order, with `@media` blocks flattened.
 *
 * Flattening is deliberate and is the conservative reading: a pair that appears only
 * under `max-width: 900px` is still a pair a reader can meet, so it belongs in the
 * census. The `@media (prefers-reduced-motion)` `:root` carries no colour.
 */
export function parseRules(css: string, origin: string): Rule[] {
  const text = stripComments(css);
  const out: Rule[] = [];
  let i = 0;
  let selector = '';
  while (i < text.length) {
    const ch = text[i];
    if (ch === '{') {
      const head = selector.trim();
      selector = '';
      // `@keyframes` holds stops (`from`, `50%`), not selectors: skipped whole, below.
      if (head.startsWith('@') && !/^@(?:-[a-z]+-)?keyframes\b/.test(head)) {
        i += 1; // descend into the at-rule; its inner rules are collected as their own
        continue;
      }
      let depth = 1;
      let j = i + 1;
      while (j < text.length && depth > 0) {
        if (text[j] === '{') depth += 1;
        else if (text[j] === '}') depth -= 1;
        j += 1;
      }
      const declarations = new Map<string, string>();
      for (const decl of splitDeclarations(text.slice(i + 1, j - 1))) {
        const at = decl.indexOf(':');
        if (at < 0) continue;
        declarations.set(decl.slice(0, at).trim().toLowerCase(), decl.slice(at + 1).trim());
      }
      if (!head.startsWith('@')) out.push({ selector: head, declarations, order: out.length, origin });
      i = j;
      continue;
    }
    if (ch === '}') {
      selector = '';
      i += 1;
      continue;
    }
    selector += ch;
    i += 1;
  }
  return out;
}

/**
 * A CSS module's text with every LOCAL class selector rewritten to the name the markup carries.
 *
 * A module declares `.ordinal` and the markup carries `_ordinal_<hash>`, so the census
 * reads each module through the bundler's own export (`scope`) rather than guessing the
 * format. A `:global(...)` segment is the other half: its classes are NOT scoped -- the
 * markup carries `am-button`, not a hashed name -- and the wrapper is not a selector the
 * matcher knows, so it is peeled off and what it held is put back untouched. Without that,
 * eight modules (the application frame, the dashboard, the front door, the knowledge base,
 * ...) contributed rules that matched no element, and the measurement said nothing about them.
 * A class selector only: the character after the dot must begin an identifier, so `0.35rem`
 * and `82ch` are untouched.
 */
export function scopeModuleCss(css: string, scope: Readonly<Record<string, string>>): string {
  const peeled: string[] = [];
  let text = '';
  let at = 0;
  for (;;) {
    const start = css.indexOf(':global(', at);
    if (start < 0) {
      text += css.slice(at);
      break;
    }
    text += css.slice(at, start);
    let depth = 0;
    let end = start + ':global'.length;
    for (; end < css.length; end += 1) {
      if (css[end] === '(') depth += 1;
      else if (css[end] === ')' && (depth -= 1) === 0) break;
    }
    peeled.push(css.slice(start + ':global('.length, end));
    text += `@@GLOBAL${peeled.length - 1}@@`;
    at = end + 1;
  }
  return text
    .replace(/\.([a-zA-Z_][A-Za-z0-9_-]*)/g, (_match, name: string) => `.${scope[name] ?? name}`)
    .replace(/@@GLOBAL(\d+)@@/g, (_match, index: string) => peeled[Number(index)] as string);
}

/** Split on `;` outside parentheses, so `color-mix(in srgb, …)` survives. */
function splitDeclarations(body: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let buf = '';
  for (const ch of body) {
    if (ch === '(') depth += 1;
    else if (ch === ')') depth -= 1;
    if (ch === ';' && depth === 0) {
      out.push(buf);
      buf = '';
    } else buf += ch;
  }
  if (buf.trim()) out.push(buf);
  return out;
}

// =============================================================== 4. the rendered markup

export interface Element {
  readonly tag: string;
  readonly classes: ReadonlySet<string>;
  readonly attrs: ReadonlyMap<string, string>;
  readonly children: Element[];
  parent: Element | null;
  /** Index among element siblings, and the sibling count, for `:first-child` etc. */
  index: number;
  siblings: number;
  /** True when the element has a non-whitespace text child of its own. */
  hasOwnText: boolean;
}

const VOID_TAGS = new Set([
  'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param',
  'source', 'track', 'wbr',
]);

/**
 * Parse `renderToStaticMarkup` output into an element tree.
 *
 * It handles exactly what React's static renderer emits: well-formed tags, double-quoted
 * attributes, void elements, HTML comments and entities. It is not a general HTML parser
 * and does not need to be — the only markup it ever sees is this application's own.
 */
export function parseMarkup(html: string): Element {
  const root: Element = {
    tag: ':root', classes: new Set(), attrs: new Map(), children: [],
    parent: null, index: 0, siblings: 1, hasOwnText: false,
  };
  const stack: Element[] = [root];
  const token = /<!--[\s\S]*?-->|<\/([a-zA-Z0-9-]+)\s*>|<([a-zA-Z0-9-]+)((?:\s+[^\s=/>]+(?:=(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*(\/?)>/g;
  let last = 0;
  let match: RegExpExecArray | null;
  const addText = (text: string) => {
    if (text.replace(/&[a-z]+;|\s/g, '').length > 0) {
      const top = stack[stack.length - 1];
      (top as { hasOwnText: boolean }).hasOwnText = true;
    }
  };
  while ((match = token.exec(html)) !== null) {
    addText(html.slice(last, match.index));
    last = token.lastIndex;
    if (match[0].startsWith('<!--')) continue;
    if (match[1]) {
      if (stack.length > 1) stack.pop();
      continue;
    }
    const tag = (match[2] as string).toLowerCase();
    const attrs = new Map<string, string>();
    const attrToken = /([^\s=/>]+)(?:=("([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
    let a: RegExpExecArray | null;
    while ((a = attrToken.exec(match[3] ?? '')) !== null) {
      attrs.set((a[1] ?? '').toLowerCase(), a[3] ?? a[4] ?? a[5] ?? '');
    }
    const parent = stack[stack.length - 1] as Element;
    const element: Element = {
      tag,
      classes: new Set((attrs.get('class') ?? '').split(/\s+/).filter(Boolean)),
      attrs,
      children: [],
      parent,
      index: parent.children.length,
      siblings: 0,
      hasOwnText: false,
    };
    parent.children.push(element);
    if (!VOID_TAGS.has(tag) && !match[4]) stack.push(element);
  }
  addText(html.slice(last));
  const settle = (node: Element): void => {
    for (const child of node.children) child.siblings = node.children.length;
    for (const child of node.children) settle(child);
  };
  settle(root);
  return root;
}

export function descendants(node: Element): Element[] {
  const out: Element[] = [];
  const walk = (n: Element): void => {
    for (const child of n.children) {
      out.push(child);
      walk(child);
    }
  };
  walk(node);
  return out;
}

// =================================================================== 5. selector matching

/** The pseudo-classes that describe a transient state rather than a position. */
const STATE_PSEUDOS = new Set(['hover', 'focus', 'focus-visible', 'focus-within', 'active', 'disabled']);
/** Pseudo-elements this module models as a virtual child of their origin. */
const PSEUDO_ELEMENTS = new Set([
  'before', 'after', 'marker', 'placeholder', 'selection', 'file-selector-button',
  '-webkit-details-marker',
]);

export interface ParsedSelector {
  /** The selector with state pseudo-classes and the pseudo-element removed. */
  readonly base: string;
  readonly states: readonly string[];
  readonly pseudoElement: string | null;
  readonly specificity: readonly [number, number, number];
  readonly source: string;
}

/** Selectors this module declines to evaluate, by the construct that defeated it. */
const UNSUPPORTED: string[] = [];
export function unsupported(): readonly string[] {
  return [...new Set(UNSUPPORTED)].sort();
}
export function resetUnsupported(): void {
  UNSUPPORTED.length = 0;
}

export function parseSelector(source: string): ParsedSelector | null {
  if (/:has\(/.test(source) || /:nth-|:not\(/.test(source)) {
    UNSUPPORTED.push(source);
    return null;
  }
  let text = source.trim();
  const states: string[] = [];
  let pseudoElement: string | null = null;
  // Pseudo-elements, written `::name` or (legacy) `:name` — this sheet always uses `::`.
  const pe = /::([a-z-]+)/.exec(text);
  if (pe) {
    if (!PSEUDO_ELEMENTS.has(pe[1] as string)) {
      UNSUPPORTED.push(source);
      return null;
    }
    pseudoElement = pe[1] as string;
    text = text.replace(/::[a-z-]+/g, '');
  }
  text = text.replace(/:([a-z-]+)\b(?!\()/g, (whole, name: string) => {
    if (STATE_PSEUDOS.has(name)) {
      states.push(name);
      return '';
    }
    return whole;
  });
  return {
    base: text.trim(),
    states,
    pseudoElement,
    specificity: specificityOf(source),
    source,
  };
}

/** CSS specificity (a, b, c); `:where()` contributes nothing, per spec. */
export function specificityOf(selector: string): readonly [number, number, number] {
  const outside = selector.replace(/:where\([^)]*\)/g, ' ');
  const ids = (outside.match(/#[\w-]+/g) ?? []).length;
  const classes =
    (outside.match(/\.[\w-]+/g) ?? []).length +
    (outside.match(/\[[^\]]*\]/g) ?? []).length +
    (outside.match(/:(?!:)[a-z-]+/g) ?? []).length;
  const types =
    (outside.match(/(?:^|[\s>+~(,])([a-z][\w-]*)/g) ?? []).length +
    (outside.match(/::[a-z-]+/g) ?? []).length;
  return [ids, classes, types];
}

function compare(a: readonly [number, number, number], b: readonly [number, number, number]): number {
  return a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
}

/** Does one compound selector (no combinators) match this element? */
function matchesCompound(element: Element, compound: string): boolean {
  let text = compound.trim().replace(/^\*/, '');
  if (text === '') return true;
  // `:where(a, b, c)` — matches if any alternative matches.
  const where = /:where\(([^)]*)\)/.exec(text);
  if (where) {
    const rest = text.replace(where[0], '');
    const anyAlternative = (where[1] ?? '')
      .split(',')
      .some((alternative) => matchesCompound(element, alternative.trim()));
    return anyAlternative && matchesCompound(element, rest);
  }
  const token = /^(?:([a-zA-Z][\w-]*)|\.([\w-]+)|\[([^\]]+)\]|:([a-z-]+))/;
  while (text.length > 0) {
    const m = token.exec(text);
    if (!m) {
      UNSUPPORTED.push(compound);
      return false;
    }
    text = text.slice(m[0].length);
    if (m[1] !== undefined && element.tag !== m[1].toLowerCase()) return false;
    if (m[2] !== undefined && !element.classes.has(m[2])) return false;
    if (m[3] !== undefined && !matchesAttribute(element, m[3])) return false;
    if (m[4] !== undefined) {
      if (m[4] === 'only-child' && element.siblings !== 1) return false;
      if (m[4] === 'first-child' && element.index !== 0) return false;
      if (m[4] === 'last-child' && element.index !== element.siblings - 1) return false;
      if (m[4] === 'empty' && (element.children.length > 0 || element.hasOwnText)) return false;
      if (m[4] === 'root' && element.tag !== 'html') return false;
      if (!['first-child', 'last-child', 'only-child', 'empty', 'root'].includes(m[4])) {
        UNSUPPORTED.push(compound);
        return false;
      }
    }
  }
  return true;
}

function matchesAttribute(element: Element, body: string): boolean {
  // `[name]`, `[name=v]`, and the three substring operators `^=`, `$=`, `*=` the sheet uses.
  const m = /^([\w-]+)(?:([\^$*]?)=['"]?([^'"\]]*)['"]?)?$/.exec(body.trim());
  if (!m) {
    UNSUPPORTED.push(`[${body}]`);
    return false;
  }
  const value = element.attrs.get((m[1] ?? '').toLowerCase());
  if (value === undefined) return false;
  const wanted = m[3];
  if (wanted === undefined) return true;
  if (m[2] === '^') return value.startsWith(wanted);
  if (m[2] === '$') return value.endsWith(wanted);
  if (m[2] === '*') return value.includes(wanted);
  return value === wanted;
}

/** Split a selector list on `,` outside parentheses: `:where(p, li)` is ONE selector. */
export function splitSelectorList(list: string): string[] {
  const out: string[] = [];
  let buf = '';
  let depth = 0;
  for (const ch of list) {
    if (ch === '(') depth += 1;
    else if (ch === ')') depth -= 1;
    if (ch === ',' && depth === 0) {
      out.push(buf);
      buf = '';
    } else buf += ch;
  }
  out.push(buf);
  return out.map((s) => s.trim()).filter(Boolean);
}

/**
 * Split a complex selector into compounds and combinators, ignoring anything inside
 * parentheses — `:where(p, li, dd)` carries spaces and commas and is ONE token.
 */
export function splitCombinators(selector: string): readonly string[] {
  const cached = COMBINATOR_PARTS.get(selector);
  if (cached !== undefined) return cached;
  const split = splitCombinatorsUncached(selector);
  COMBINATOR_PARTS.set(selector, split);
  return split;
}

/**
 * `matches()` splits the same few thousand selector strings once per ELEMENT, and the census
 * asks it about every element of every screen, so the split is memoised. The arrays are
 * frozen: a caller that mutated one would corrupt every later match.
 */
const COMBINATOR_PARTS = new Map<string, readonly string[]>();

function splitCombinatorsUncached(selector: string): readonly string[] {
  const parts: string[] = [];
  let buf = '';
  let depth = 0;
  const flush = (): void => {
    if (buf.trim()) parts.push(buf.trim());
    buf = '';
  };
  for (const ch of selector.trim()) {
    if (ch === '(') depth += 1;
    else if (ch === ')') depth -= 1;
    if (depth === 0 && (ch === '>' || ch === '+' || ch === '~')) {
      flush();
      parts.push(ch);
      continue;
    }
    if (depth === 0 && /\s/.test(ch)) {
      flush();
      continue;
    }
    buf += ch;
  }
  flush();
  return Object.freeze(parts);
}

/** Full selector match, supporting descendant, `>` and `+`. */
export function matches(element: Element, base: string): boolean {
  const parts = splitCombinators(base);
  if (parts.length === 0) return false;
  const subject = parts[parts.length - 1] as string;
  if (!matchesCompound(element, subject)) return false;
  let current: Element | null = element;
  let i = parts.length - 2;
  while (i >= 0) {
    const combinator = parts[i] === '>' || parts[i] === '+' ? parts[i] : ' ';
    const compound = combinator === ' ' ? parts[i] : parts[i - 1];
    if (compound === undefined) return false;
    if (combinator === '>') {
      current = current?.parent ?? null;
      if (!current || !matchesCompound(current, compound)) return false;
    } else if (combinator === '+') {
      const parent: Element | null = current?.parent ?? null;
      const previous: Element | undefined =
        parent && current ? parent.children[current.index - 1] : undefined;
      if (!previous || !matchesCompound(previous, compound)) return false;
      current = previous;
    } else {
      let ancestor: Element | null = current?.parent ?? null;
      while (ancestor && !matchesCompound(ancestor, compound)) ancestor = ancestor.parent;
      if (!ancestor) return false;
      current = ancestor;
    }
    i -= combinator === ' ' ? 1 : 2;
  }
  return true;
}

/**
 * The candidates a selector index offers for an element, in the order the rules were given.
 *
 * `census()` asks `matches()` about every element of every screen against every selector of
 * the stylesheet, and a rule that cannot match an element can be told from the element's own
 * class list or tag without evaluating it. Each selector is filed under ONE thing its
 * SUBJECT (the compound after the last combinator) requires -- a class, else a tag -- and
 * under nothing when the subject requires neither (`[data-x]`, `:where()`, an empty base).
 * That is a NECESSARY condition only: the candidates are still run through `matches()`, so
 * the index can never add a match, and a selector it files wrongly could only be missed if
 * its subject did not require the thing it was filed under, which `anchorOf` reads off the
 * compound the same way `matchesCompound` does.
 */
export function selectorIndex<T extends { readonly parsed: ParsedSelector }>(
  entries: readonly T[],
): (element: Element) => T[] {
  const byClass = new Map<string, number[]>();
  const byTag = new Map<string, number[]>();
  const always: number[] = [];
  const file = (map: Map<string, number[]>, key: string, at: number): void => {
    const list = map.get(key);
    if (list === undefined) map.set(key, [at]);
    else list.push(at);
  };
  entries.forEach((entry, at) => {
    const parts = splitCombinators(entry.parsed.base);
    const subject = (parts[parts.length - 1] ?? '').trim().replace(/^\*/, '');
    // `:where(...)` is an any-of, and attribute values and parenthesised arguments may hold a
    // dot that is not a class.
    const bare = subject.includes(':where(')
      ? ''
      : subject.replace(/\[[^\]]*\]/g, '').replace(/\([^)]*\)/g, '');
    const cls = /\.([\w-]+)/.exec(bare);
    const tag = /^([a-zA-Z][\w-]*)/.exec(bare);
    if (cls?.[1] !== undefined) file(byClass, cls[1], at);
    else if (tag?.[1] !== undefined) file(byTag, tag[1].toLowerCase(), at);
    else always.push(at);
  });
  return (element) => {
    const found: number[] = [...always];
    for (const name of element.classes) {
      const list = byClass.get(name);
      if (list !== undefined) found.push(...list);
    }
    const tagged = byTag.get(element.tag);
    if (tagged !== undefined) found.push(...tagged);
    return found.sort((a, b) => a - b).map((at) => entries[at] as T);
  };
}

// ============================================================= 6. colours in declarations

export type Colour =
  | { readonly kind: 'token'; readonly token: TokenName }
  | { readonly kind: 'mix'; readonly token: TokenName; readonly percent: number }
  | { readonly kind: 'transparent' }
  | { readonly kind: 'current' };

/** The colour a declaration value carries, or `null` when it carries none. */
export function readColour(value: string): Colour | null {
  const cached = COLOUR_OF_VALUE.get(value);
  if (cached !== undefined) return cached;
  const colour = readColourUncached(value);
  COLOUR_OF_VALUE.set(value, colour);
  return colour;
}

/** A declaration value reads to the same colour every time; the cascade asks per element. */
const COLOUR_OF_VALUE = new Map<string, Colour | null>();

/**
 * The paint that sits under every other layer of a multi-layer `background`.
 *
 * `radial-gradient(circle at 10% 0%, var(--am-accent-light), transparent 36%), var(--am-paper)`
 * is a faint tint in one corner over a `--am-paper` card, and text on it is judged against
 * the card. Reading the FIRST token in the value judged it against the tint, which paints a
 * fraction of the box and is the wrong end of the declaration: the colour layer, when there is
 * one, is the LAST comma-separated layer. A value with no top-level comma is returned as it was.
 */
function lastLayer(value: string): string {
  let depth = 0;
  let from = 0;
  for (let at = 0; at < value.length; at += 1) {
    if (value[at] === '(') depth += 1;
    else if (value[at] === ')') depth -= 1;
    else if (value[at] === ',' && depth === 0) from = at + 1;
  }
  return from === 0 ? value : value.slice(from);
}

function readColourUncached(raw: string): Colour | null {
  const value = lastLayer(raw);
  const mix = /color-mix\(\s*in\s+srgb\s*,\s*var\((--am-[\w-]+)\)\s*([\d.]+)%\s*,\s*transparent\s*\)/.exec(
    value,
  );
  if (mix) return { kind: 'mix', token: mix[1] as TokenName, percent: Number(mix[2]) / 100 };
  if (/\bcurrentColor\b/i.test(value)) return { kind: 'current' };
  const token = /var\((--am-[\w-]+)\)/.exec(value);
  if (token) return { kind: 'token', token: token[1] as TokenName };
  if (/^\s*(transparent|none|0)\s*$/.test(value)) return { kind: 'transparent' };
  return null;
}

/**
 * The hex a colour resolves to, composited over `backdrop`.
 *
 * `color-mix(in srgb, X p%, transparent)` is X at alpha p, so over an opaque backdrop it
 * is the ordinary source-over blend. Everything else is opaque already.
 */
export function resolve(
  colour: Colour,
  tokens: ReadonlyMap<TokenName, string>,
  backdrop: string,
  currentColour: string,
): string | null {
  if (colour.kind === 'transparent') return null;
  if (colour.kind === 'current') return currentColour;
  const hex = tokens.get(colour.token);
  if (hex === undefined) return null;
  if (colour.kind === 'token') return hex;
  const [fr, fg, fb] = parseHex(hex);
  const [br, bg, bb] = parseHex(backdrop);
  const blend = (f: number, b: number): number =>
    Math.round((f * colour.percent + b * (1 - colour.percent)) * 255);
  return `#${[blend(fr, br), blend(fg, bg), blend(fb, bb)]
    .map((c) => c.toString(16).padStart(2, '0'))
    .join('')}`;
}

/** The border/outline sides a declaration can carry a colour for. */
const EDGE_PROPERTIES = [
  'border', 'border-color', 'border-top', 'border-right', 'border-bottom', 'border-left',
  'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
  'outline', 'outline-color',
] as const;

// ===================================================================== 7. the cascade

interface Computed {
  colour: Colour | null;
  background: Colour | null;
  edges: Map<string, Colour>;
}

function emptyComputed(): Computed {
  return { colour: null, background: null, edges: new Map() };
}

function applyRule(into: Computed, rule: Rule): void {
  for (const [property, value] of rule.declarations) {
    const colour = readColour(value);
    if (property === 'color') into.colour = colour;
    else if (property === 'background' || property === 'background-color') {
      // `background: none` and a gradient-free shorthand both mean "no colour here".
      into.background = colour;
    } else if ((EDGE_PROPERTIES as readonly string[]).includes(property)) {
      if (colour === null && /^\s*0\s*$/.test(value)) into.edges.set(property, { kind: 'transparent' });
      else if (colour !== null) into.edges.set(property, colour);
    }
  }
}

export interface Occurrence {
  readonly kind: 'text' | 'edge' | 'graphic';
  readonly foreground: string;
  readonly background: TokenName;
  readonly state: string | null;
  readonly pseudo: string | null;
  readonly site: string;
  /**
   * WCAG 1.4.11 is about "user interface components", and the markup says which
   * elements those are — an interactive tag, or anything carrying a `role`. This is
   * read off the rendered element rather than decided by a list of class names.
   */
  readonly interactive: boolean;
  /**
   * True when the element's own fill already reaches 3:1 against what is behind it.
   * A boundary is only required to identify a component when nothing else does: a
   * primary button filled `--am-accent` on `--am-surface` at 7.6:1 is identifiable
   * without its border, and a text field filled `--am-paper` on `--am-paper` is not.
   */
  readonly fillDistinguishes: boolean;
}

/** The tags HTML makes operable on their own. `details` is a container; `summary` operates it. */
const INTERACTIVE_TAGS = new Set(['a', 'button', 'input', 'select', 'textarea', 'summary']);

/**
 * WIDGET roles only.
 *
 * An earlier form of this test accepted any `role`, and it was wrong in a way worth
 * keeping the note for: the only roles this tree uses are `alert`, `note` and `status`,
 * every one of them a live region or a document role rather than a control. That made
 * the failure panel and the neutral route placeholder count as "user interface
 * components", and the guard demanded 1.4.11 of a card's border. 1.4.11 says *user
 * interface component*, which the specification defines as a part of the content the
 * user OPERATES — not everything that carries an ARIA attribute.
 */
const WIDGET_ROLES = new Set([
  'button', 'link', 'checkbox', 'radio', 'switch', 'slider', 'spinbutton', 'textbox',
  'searchbox', 'combobox', 'listbox', 'menuitem', 'menuitemcheckbox', 'menuitemradio',
  'option', 'tab', 'treeitem',
]);

export function isInteractive(element: Element): boolean {
  if (INTERACTIVE_TAGS.has(element.tag) && (element.tag !== 'a' || element.attrs.has('href'))) {
    return true;
  }
  const role = element.attrs.get('role');
  return (role !== undefined && WIDGET_ROLES.has(role)) || element.attrs.has('tabindex');
}

export interface Screen {
  readonly name: string;
  readonly markup: string;
}

/**
 * A screen's markup as the product serves it: inside the application frame.
 *
 * Every page is drawn in `<main class="am-app__main">` (`app/layout.tsx`), and `globals.css`
 * remaps thirteen base tokens for everything below it (see `scopedPalettes`). `screens()`
 * renders a page on its own, wrapped only in `<html><body>`, so measured as given it would
 * carry the root palette that no reader of that page meets (S7-design-02). The wrapper is
 * applied HERE, where the cascade is evaluated, so a caller cannot take a census of the
 * unframed page by forgetting it. A screen that already carries the frame (`AppFrame`) or a
 * piece of it (the pieces seeded inside `<header class="am-app__bar">`) is left alone.
 */
export function framed(markup: string): string {
  if (/class="am-app(?:__(?:bar|utility|main))?"/.test(markup)) return markup;
  const open = '<div class="am-app"><main class="am-app__main">';
  const close = '</main></div>';
  return markup.includes('<body>')
    ? markup.replace('<body>', `<body>${open}`).replace('</body>', `${close}</body>`)
    : `${open}${markup}${close}`;
}

/**
 * A palette that applies INSIDE part of the page: the custom properties a non-root rule
 * points at other tokens, for the elements its selector matches and everything below them.
 *
 * `globals.css` has one -- `[data-dashboard-showcase], .am-app__bar, .am-app__utility,
 * .am-app__main { --am-paper: var(--am-showcase-card); ... }` -- and `palette()`, which reads
 * the `:root` blocks, cannot see it. Every authenticated screen is drawn inside
 * `.am-app__main`, so for thirteen base tokens the colour a reader meets is the OTHER token's
 * value (S7-design-02). The census therefore names the token that really supplies a colour:
 * an element inside that scope that reads `var(--am-ink-soft)` is measured as
 * `--am-showcase-soft`. Both ends of every pair are resolved at the element that declares
 * them, because a custom property is substituted where it is used, not where it is defined.
 */
export interface ScopedPalette {
  /** The selectors that open the scope. */
  readonly selectors: readonly string[];
  /** The token a base token resolves to inside it. */
  readonly alias: ReadonlyMap<TokenName, TokenName>;
}

/** Every scoped palette the rules declare. A `:root` block is a theme, not a scope: `palette()` reads it. */
export function scopedPalettes(rules: readonly Rule[]): ScopedPalette[] {
  const out: ScopedPalette[] = [];
  for (const rule of rules) {
    if (/^\s*:root/.test(rule.selector)) continue;
    const alias = new Map<TokenName, TokenName>();
    for (const [property, value] of rule.declarations) {
      if (!property.startsWith('--am-')) continue;
      const reference = /^var\((--am-[\w-]+)\)$/.exec(value.trim());
      if (reference) alias.set(property as TokenName, reference[1] as TokenName);
    }
    if (alias.size > 0) out.push({ selectors: splitSelectorList(rule.selector), alias });
  }
  return out;
}

function aliasedColour(colour: Colour, alias: ReadonlyMap<TokenName, TokenName> | null): Colour {
  if (alias === null || (colour.kind !== 'token' && colour.kind !== 'mix')) return colour;
  const token = alias.get(colour.token);
  return token === undefined ? colour : { ...colour, token };
}

/**
 * Every (foreground, background) pair that meets on these screens.
 *
 * The background of a pair is always a TOKEN, because a pair whose background is a blend
 * of a blend is not a thing anyone can reason about and this stylesheet never makes one:
 * every `color-mix` in it is a border, never a surface.
 */
export function census(
  screens: readonly Screen[],
  rules: readonly Rule[],
  tokens: ReadonlyMap<TokenName, string>,
): Map<string, Occurrence & { sites: string[] }> {
  const parsed = rules
    .map((rule) =>
      splitSelectorList(rule.selector).map((one) => ({ rule, parsed: parseSelector(one) })),
    )
    .flat()
    .filter((entry): entry is { rule: Rule; parsed: ParsedSelector } => entry.parsed !== null);

  const stateless = parsed.filter((e) => e.parsed.states.length === 0 && e.parsed.pseudoElement === null);
  const stateful = parsed.filter((e) => e.parsed.states.length > 0 && e.parsed.pseudoElement === null);
  const pseudos = parsed.filter((e) => e.parsed.pseudoElement !== null);

  const scopes = scopedPalettes(rules);
  const statelessFor = selectorIndex(stateless);
  const statefulFor = selectorIndex(stateful);
  const pseudosFor = selectorIndex(pseudos);

  const out = new Map<string, Occurrence & { sites: string[] }>();
  const record = (occurrence: Occurrence): void => {
    const key = [
      occurrence.kind, occurrence.foreground, occurrence.background,
      occurrence.state ?? '-', occurrence.pseudo ?? '-',
    ].join('|');
    const existing = out.get(key);
    if (existing) {
      if (!existing.sites.includes(occurrence.site)) existing.sites.push(occurrence.site);
      // MERGE TO THE STRICTEST SITE, never to the first one.
      //
      // The same pair occurs at many elements. `--am-line` on `--am-surface` at a 1px
      // border is a decorative card edge at forty of them and the only boundary of an
      // interactive page-action link at one. Keeping whichever was recorded first made
      // the guard's verdict depend on the order screens happen to render in, and it
      // silently exempted the one site that matters. The strictest classification wins:
      // interactive if ANY site is, and undistinguished-by-fill if ANY site is.
      out.set(key, {
        ...existing,
        interactive: existing.interactive || occurrence.interactive,
        fillDistinguishes: existing.fillDistinguishes && occurrence.fillDistinguishes,
      });
    } else out.set(key, { ...occurrence, sites: [occurrence.site] });
  };

  for (const screen of screens) {
    const root = parseMarkup(framed(screen.markup));
    const all = descendants(root);
    const computedOf = new Map<Element, Computed>();
    const order = (a: { rule: Rule; parsed: ParsedSelector }, b: typeof a): number =>
      compare(a.parsed.specificity, b.parsed.specificity) || a.rule.order - b.rule.order;

    for (const element of all) {
      const computed = emptyComputed();
      for (const entry of statelessFor(element).filter((e) => matches(element, e.parsed.base)).sort(order)) {
        applyRule(computed, entry.rule);
      }
      computedOf.set(element, computed);
    }

    /** The nearest self-or-ancestor background token; the canvas is `body`'s. */
    const backgroundOf = (element: Element | null, own: Computed | null): TokenName | null => {
      let node = element;
      let computed = own;
      while (node) {
        const background = computed?.background ?? computedOf.get(node)?.background ?? null;
        if (background && background.kind === 'token') {
          return scopeAt(node)?.get(background.token) ?? background.token;
        }
        computed = null;
        node = node.parent;
      }
      return null;
    };

    /** The aliases in force at an element: its own scope's, else the nearest ancestor's. */
    const scopeMemo = new Map<Element, ReadonlyMap<TokenName, TokenName> | null>();
    const scopeAt = (node: Element | null): ReadonlyMap<TokenName, TokenName> | null => {
      if (node === null || scopes.length === 0) return null;
      const known = scopeMemo.get(node);
      if (known !== undefined) return known;
      const own = scopes.find((scope) => scope.selectors.some((selector) => matches(node, selector)));
      const found = own !== undefined ? own.alias : scopeAt(node.parent);
      scopeMemo.set(node, found);
      return found;
    };

    const colourOf = (element: Element, own: Computed | null): Colour | null => {
      let node: Element | null = element;
      let computed = own;
      while (node) {
        const colour = computed?.colour ?? computedOf.get(node)?.colour ?? null;
        if (colour) return aliasedColour(colour, scopeAt(node));
        computed = null;
        node = node.parent;
      }
      return null;
    };

    const emit = (
      element: Element,
      computed: Computed,
      state: string | null,
      pseudo: string | null,
      site: string,
      hasText: boolean,
    ): void => {
      const background = backgroundOf(element, computed);
      if (!background) return;
      const backdrop = tokens.get(background);
      if (!backdrop) return;
      const interactive = isInteractive(element);
      if (hasText) {
        const colour = colourOf(element, computed);
        const hex = colour ? resolve(colour, tokens, backdrop, backdrop) : null;
        if (colour?.kind === 'token' && hex) {
          record({
            kind: 'text', foreground: colour.token, background, state, pseudo, site,
            interactive, fillDistinguishes: false,
          });
        }
      }
      // A pseudo-element that paints a background and carries no text is a graphic
      // object: `.am-history__event::before` is the dot that says accepted or rejected,
      // and in the history it is the only thing that says it in colour. 1.4.11.
      if (pseudo !== null && pseudo !== 'selection' && !hasText && computed.background?.kind === 'token') {
        const behind = backgroundOf(element, null);
        const painted = scopeAt(element)?.get(computed.background.token) ?? computed.background.token;
        if (behind && behind !== painted) {
          record({
            kind: 'graphic', foreground: painted,
            background: behind, state, pseudo, site,
            interactive, fillDistinguishes: false,
          });
        }
      }
      // An edge contrasts with what is OUTSIDE it: the surface the element sits on.
      const outside = backgroundOf(element.parent, null) ?? background;
      const outsideHex = tokens.get(outside);
      // The element's own fill against what is behind it. `background` is the nearest
      // self-or-ancestor, so when the element declares none this is the backdrop
      // against itself — 1:1 — which is the correct reading: it distinguishes nothing.
      const fillDistinguishes =
        outsideHex !== undefined && contrastRatio(backdrop, outsideHex) >= 3;
      for (const [property, declared] of computed.edges) {
        const colour = aliasedColour(declared, scopeAt(element));
        if (colour.kind === 'transparent' || colour.kind === 'current' || !outsideHex) continue;
        const hex = resolve(colour, tokens, outsideHex, outsideHex);
        if (!hex) continue;
        record({
          kind: pseudo === 'before' ? 'graphic' : 'edge',
          foreground: colour.kind === 'mix' ? `${colour.token}@${Math.round(colour.percent * 100)}%` : colour.token,
          background: outside,
          state,
          pseudo: pseudo ?? property,
          site,
          interactive,
          fillDistinguishes,
        });
      }
    };

    for (const element of all) {
      const computed = computedOf.get(element) as Computed;
      const site = `${screen.name} ${path(element)}`;
      emit(element, computed, null, null, site, element.hasOwnText);

      // An element is never in one state pseudo-class in isolation: `:hover` on a
      // `.am-button` inside `.am-evidence__pages` obeys BOTH `.am-button:hover` and
      // `.am-evidence__pages .am-button:hover`, and the second wins on specificity. So
      // each distinct state SET gets a full cascade of every rule whose states that set
      // satisfies, rather than one rule dropped on top of the resting style. Applying
      // them one at a time reports pairs no browser ever paints.
      const applicable = statefulFor(element).filter((e) => matches(element, e.parsed.base));
      const stateSets = new Map<string, string[]>();
      for (const entry of applicable) {
        const key = [...entry.parsed.states].sort().join(':');
        if (!stateSets.has(key)) stateSets.set(key, [...entry.parsed.states]);
      }
      for (const [key, states] of stateSets) {
        const held = new Set(states);
        const variant = emptyComputed();
        const inState = [
          ...statelessFor(element).filter((e) => matches(element, e.parsed.base)),
          ...applicable.filter((e) => e.parsed.states.every((s) => held.has(s))),
        ].sort(order);
        for (const entry of inState) applyRule(variant, entry.rule);
        emit(element, variant, key, null, `${site} {:${key}}`, element.hasOwnText);
      }

      for (const entry of pseudosFor(element)) {
        const pseudo = entry.parsed.pseudoElement as string;
        if (entry.parsed.base !== '' && !matches(element, entry.parsed.base)) continue;
        if (entry.parsed.base === '' && pseudo !== 'selection') continue;
        const variant = emptyComputed();
        variant.colour = computed.colour;
        applyRule(variant, entry.rule);
        // A pseudo-element with no background of its own sits on its origin's.
        if (!variant.background) variant.background = computed.background;
        const carriesText = pseudo !== 'before';
        emit(
          element,
          variant,
          entry.parsed.states.join(':') || null,
          pseudo,
          `${site} {${entry.parsed.source.trim()}}`,
          carriesText && (element.hasOwnText || pseudo === 'placeholder' || pseudo === 'marker' || pseudo === '-webkit-details-marker' || pseudo === 'file-selector-button'),
        );
      }
    }
  }
  return out;
}

function path(element: Element): string {
  const parts: string[] = [];
  let node: Element | null = element;
  while (node && node.tag !== ':root') {
    const classes = [...node.classes].filter((c) => c.startsWith('am-') || c.length < 24);
    parts.unshift(node.tag + (classes.length ? `.${classes.join('.')}` : ''));
    node = node.parent;
  }
  return parts.slice(-3).join(' > ');
}

// =========================================================== 8. the declared census

/**
 * Pairs a single rule states outright, by declaring `color` and `background` together.
 *
 * The rendered census is the stronger evidence — it proves a pair is REACHED — but it is
 * bounded by what one server render pass can produce, and the harness cannot fire an
 * event or run an effect. `.am-form__created`, `.am-form__problem` and
 * `.am-form__chosen` appear only after a click; `.am-review__recommendation` and
 * `.am-uid` need a review screen with data in four caches. Every one of them declares
 * its ink and its tint in the SAME block, so the pair is decidable from the stylesheet
 * alone, with no markup at all.
 *
 * The two censuses are unioned. Neither is a substitute for the other: this one cannot
 * see an ink that meets a tint through inheritance, and the rendered one cannot see a
 * screen it cannot render.
 */
export function declaredPairs(rules: readonly Rule[]): Map<string, Occurrence & { sites: string[] }> {
  const out = new Map<string, Occurrence & { sites: string[] }>();
  // Every screen is drawn inside the application frame, so a pair a rule declares is met in
  // the frame's palette as well as in the root one (`scopedPalettes`): both are recorded.
  const inFrame = scopedPalettes(rules).map((scope) => scope.alias);
  const record = (foreground: TokenName, background: TokenName, site: string): void => {
    const key = ['text', foreground, background, '-', '-'].join('|');
    const existing = out.get(key);
    if (existing) existing.sites.push(site);
    else {
      out.set(key, {
        kind: 'text', foreground, background,
        state: null, pseudo: null, site, sites: [site],
        interactive: false, fillDistinguishes: false,
      });
    }
  };
  for (const rule of rules) {
    const colour = readColour(rule.declarations.get('color') ?? '');
    const background = readColour(
      rule.declarations.get('background') ?? rule.declarations.get('background-color') ?? '',
    );
    if (colour?.kind !== 'token' || background?.kind !== 'token') continue;
    const site = rule.selector.trim();
    record(colour.token, background.token, site);
    for (const alias of inFrame) {
      const foreground = alias.get(colour.token) ?? colour.token;
      const behind = alias.get(background.token) ?? background.token;
      if (foreground !== colour.token || behind !== background.token) {
        record(foreground, behind, `${site} {inside the application frame}`);
      }
    }
  }
  return out;
}

// ============================================================== 9. what a pair must clear

/** WCAG 2.1 AA, small text. Applied to every size: nothing here relies on the 18pt relief. */
export const AA_TEXT = 4.5;
/** WCAG 2.1 AA 1.4.11, non-text contrast. */
export const AA_NON_TEXT = 3;

/**
 * The threshold a pair answers to, or `null` when nothing asks anything of it.
 *
 * This is the whole of the classification, and it is a FUNCTION of what the pair is
 * rather than a list of which pairs matter. Text is text. A graphic that carries meaning
 * — the verdict dot in the decision history is the only thing that says accepted or
 * rejected in colour — is 1.4.11.
 *
 * ## `R-33`: EVERY border answers to 3:1, not only the load-bearing ones
 *
 * Until wave 42 the last clause read *"a boundary is 1.4.11 only when it is the sole thing
 * identifying a control: an interactive element, per the markup, whose own fill does not
 * already separate it from what is behind it. Everything else is a separator and WCAG asks
 * nothing of it."* That was a correct reading of 1.4.11 and it is no longer the rule this
 * product holds itself to.
 *
 * The owner ruled on 2026-09-23 (`R-33`, `D-81`) for the **product-wide** floor over the
 * targeted one, explicitly — the option `W32-CONTRAST` §3 and `W33-THEME` had each declined
 * because it turns every rule in the product into a hard line. So the threshold for an edge
 * is no longer a question about the element it surrounds. It is 3:1, everywhere.
 *
 * Two consequences worth stating, because both are the ruling and not an accident:
 *
 *   - `interactive` and `fillDistinguishes` are no longer consulted for an edge. They stay
 *     on `Occurrence` because they are measured facts about a site and the register, the
 *     report and any future ruling can still read them; nothing in the THRESHOLD reads them.
 *   - The `disabled` exception goes with them. 1.4.11 excepts an inactive component in as
 *     many words, and that exception is a floor WCAG PERMITS rather than one the owner
 *     kept: a product-wide border floor that a disabled control could sit under would be
 *     the targeted rule again, wearing the word "except".
 */
export function thresholdFor(occurrence: Occurrence): number | null {
  if (occurrence.kind === 'text') return AA_TEXT;
  // R-33. Every border, every state, both palettes.
  if (occurrence.kind === 'edge') return AA_NON_TEXT;
  // 1.4.11 excepts inactive user interface components, in as many words. It now reaches
  // graphics alone: an edge answered above, and text answered above that.
  if (occurrence.state === 'disabled') return null;
  return AA_NON_TEXT;
}
