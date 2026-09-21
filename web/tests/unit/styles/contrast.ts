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

/** Every custom property declared in the first `:root` block, by name. */
export function parseTokens(css: string): Map<TokenName, string> {
  const body = /:root\s*\{([\s\S]*?)\}/.exec(stripComments(css));
  if (!body) throw new Error('no :root block');
  const out = new Map<TokenName, string>();
  for (const decl of (body[1] ?? '').split(';')) {
    const at = decl.indexOf(':');
    if (at < 0) continue;
    const name = decl.slice(0, at).trim();
    if (name.startsWith('--am-')) out.set(name as TokenName, decl.slice(at + 1).trim());
  }
  return out;
}

/** Colour tokens: the ones whose value is a hex literal. */
export function colourTokens(css: string): Map<TokenName, string> {
  const out = new Map<TokenName, string>();
  for (const [name, value] of parseTokens(css)) {
    if (/^#[0-9a-fA-F]{3,8}$/.test(value)) out.set(name, value);
  }
  return out;
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
      if (head.startsWith('@')) {
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
      out.push({ selector: head, declarations, order: out.length, origin });
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
const STATE_PSEUDOS = new Set(['hover', 'focus', 'focus-visible', 'active', 'disabled']);
/** Pseudo-elements this module models as a virtual child of their origin. */
const PSEUDO_ELEMENTS = new Set([
  'before', 'after', 'marker', 'placeholder', 'selection', 'file-selector-button',
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
      if (m[4] === 'first-child' && element.index !== 0) return false;
      if (m[4] === 'last-child' && element.index !== element.siblings - 1) return false;
      if (m[4] === 'empty' && (element.children.length > 0 || element.hasOwnText)) return false;
      if (m[4] === 'root' && element.tag !== 'html') return false;
      if (!['first-child', 'last-child', 'empty', 'root'].includes(m[4])) {
        UNSUPPORTED.push(compound);
        return false;
      }
    }
  }
  return true;
}

function matchesAttribute(element: Element, body: string): boolean {
  const m = /^([\w-]+)(?:=['"]?([^'"\]]*)['"]?)?$/.exec(body.trim());
  if (!m) {
    UNSUPPORTED.push(`[${body}]`);
    return false;
  }
  const value = element.attrs.get((m[1] ?? '').toLowerCase());
  if (value === undefined) return false;
  return m[2] === undefined || value === m[2];
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
export function splitCombinators(selector: string): string[] {
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
  return parts;
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

// ============================================================= 6. colours in declarations

export type Colour =
  | { readonly kind: 'token'; readonly token: TokenName }
  | { readonly kind: 'mix'; readonly token: TokenName; readonly percent: number }
  | { readonly kind: 'transparent' }
  | { readonly kind: 'current' };

/** The colour a declaration value carries, or `null` when it carries none. */
export function readColour(value: string): Colour | null {
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
}

export interface Screen {
  readonly name: string;
  readonly markup: string;
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

  const out = new Map<string, Occurrence & { sites: string[] }>();
  const record = (occurrence: Occurrence): void => {
    const key = [
      occurrence.kind, occurrence.foreground, occurrence.background,
      occurrence.state ?? '-', occurrence.pseudo ?? '-',
    ].join('|');
    const existing = out.get(key);
    if (existing) {
      if (!existing.sites.includes(occurrence.site)) existing.sites.push(occurrence.site);
    } else out.set(key, { ...occurrence, sites: [occurrence.site] });
  };

  for (const screen of screens) {
    const root = parseMarkup(screen.markup);
    const all = descendants(root);
    const computedOf = new Map<Element, Computed>();
    const order = (a: { rule: Rule; parsed: ParsedSelector }, b: typeof a): number =>
      compare(a.parsed.specificity, b.parsed.specificity) || a.rule.order - b.rule.order;

    for (const element of all) {
      const computed = emptyComputed();
      for (const entry of stateless.filter((e) => matches(element, e.parsed.base)).sort(order)) {
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
        if (background && background.kind === 'token') return background.token;
        computed = null;
        node = node.parent;
      }
      return null;
    };

    const colourOf = (element: Element, own: Computed | null): Colour | null => {
      let node: Element | null = element;
      let computed = own;
      while (node) {
        const colour = computed?.colour ?? computedOf.get(node)?.colour ?? null;
        if (colour) return colour;
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
      if (hasText) {
        const colour = colourOf(element, computed);
        const hex = colour ? resolve(colour, tokens, backdrop, backdrop) : null;
        if (colour?.kind === 'token' && hex) {
          record({ kind: 'text', foreground: colour.token, background, state, pseudo, site });
        }
      }
      // A pseudo-element that paints a background and carries no text is a graphic
      // object: `.am-history__event::before` is the dot that says accepted or rejected,
      // and in the history it is the only thing that says it in colour. 1.4.11.
      if (pseudo !== null && pseudo !== 'selection' && !hasText && computed.background?.kind === 'token') {
        const behind = backgroundOf(element, null);
        if (behind && behind !== computed.background.token) {
          record({
            kind: 'graphic', foreground: computed.background.token,
            background: behind, state, pseudo, site,
          });
        }
      }
      // An edge contrasts with what is OUTSIDE it: the surface the element sits on.
      const outside = backgroundOf(element.parent, null) ?? background;
      const outsideHex = tokens.get(outside);
      for (const [property, colour] of computed.edges) {
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
      const applicable = stateful.filter((e) => matches(element, e.parsed.base));
      const stateSets = new Map<string, string[]>();
      for (const entry of applicable) {
        const key = [...entry.parsed.states].sort().join(':');
        if (!stateSets.has(key)) stateSets.set(key, [...entry.parsed.states]);
      }
      for (const [key, states] of stateSets) {
        const held = new Set(states);
        const variant = emptyComputed();
        const inState = [
          ...stateless.filter((e) => matches(element, e.parsed.base)),
          ...applicable.filter((e) => e.parsed.states.every((s) => held.has(s))),
        ].sort(order);
        for (const entry of inState) applyRule(variant, entry.rule);
        emit(element, variant, key, null, `${site} {:${key}}`, element.hasOwnText);
      }

      for (const entry of pseudos) {
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
          carriesText && (element.hasOwnText || pseudo === 'placeholder' || pseudo === 'marker' || pseudo === 'file-selector-button'),
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
  for (const rule of rules) {
    const colour = readColour(rule.declarations.get('color') ?? '');
    const background = readColour(
      rule.declarations.get('background') ?? rule.declarations.get('background-color') ?? '',
    );
    if (colour?.kind !== 'token' || background?.kind !== 'token') continue;
    const key = ['text', colour.token, background.token, '-', '-'].join('|');
    const existing = out.get(key);
    if (existing) existing.sites.push(rule.selector.trim());
    else {
      out.set(key, {
        kind: 'text', foreground: colour.token, background: background.token,
        state: null, pseudo: null, site: rule.selector.trim(), sites: [rule.selector.trim()],
      });
    }
  }
  return out;
}
