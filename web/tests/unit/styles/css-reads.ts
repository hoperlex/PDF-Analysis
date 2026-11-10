/**
 * Readers of a stylesheet's text for the width tests of the browser walks (`narrow-walk-v4.test.ts`, `narrow-walk-v5.test.ts`).
 *
 * The suite renders markup under `environment: 'node'` and cannot measure a width, so each cause of a layout fault is held as the
 * declarations that cured it, read from the right `@media` block. These four readers are the whole instrument; each test that uses
 * them first runs them on a fixture that lacks the rule (so the check can fail) and then on the real module (so it reads this tree).
 */

import { parseRules } from './contrast';

export const COMMENT = /\/\*[\s\S]*?\*\//g;

/** The text inside every `@media (<query>) { ... }` of a stylesheet, with its braces matched. */
export function mediaBlocks(css: string, query: string): readonly string[] {
  const text = css.replace(COMMENT, '');
  const head = `@media (${query})`;
  const blocks: string[] = [];
  let at = text.indexOf(head);
  while (at >= 0) {
    const open = text.indexOf('{', at);
    let depth = 1;
    let end = open + 1;
    while (end < text.length && depth > 0) {
      if (text[end] === '{') depth += 1;
      else if (text[end] === '}') depth -= 1;
      end += 1;
    }
    blocks.push(text.slice(open + 1, end - 1));
    at = text.indexOf(head, end);
  }
  return blocks;
}

/** The stylesheet without any `@media` block: its base rules. */
export function withoutMedia(css: string): string {
  let text = css.replace(COMMENT, '');
  for (let at = text.indexOf('@media'); at >= 0; at = text.indexOf('@media')) {
    const open = text.indexOf('{', at);
    let depth = 1;
    let end = open + 1;
    while (end < text.length && depth > 0) {
      if (text[end] === '{') depth += 1;
      else if (text[end] === '}') depth -= 1;
      end += 1;
    }
    text = text.slice(0, at) + text.slice(end);
  }
  return text;
}

export function declares(css: string, selector: string, property: string, value: RegExp): boolean {
  return parseRules(css, 'test').some(
    (rule) =>
      rule.selector.split(',').some((part) => part.trim() === selector) && value.test(rule.declarations.get(property) ?? ''),
  );
}

/** Whether some `@media (<query>)` block of the sheet declares it. */
export function declaresIn(css: string, query: string, selector: string, property: string, value: RegExp): boolean {
  return mediaBlocks(css, query).some((block) => declares(block, selector, property, value));
}
