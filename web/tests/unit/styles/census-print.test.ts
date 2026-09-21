import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'vitest';

import { census, declaredPairs, colourTokens, contrastRatio, parseRules, resolve, unsupported, readColour } from './contrast';
import { screens } from './screens';

const WEB = fileURLToPath(new URL('../../..', import.meta.url));
const GLOBALS = join(WEB, 'src', 'app', 'globals.css');
const MODULE = join(WEB, 'src', 'widgets', 'run-progress', 'ui', 'run-progress.module.css');

describe('print', () => {
  it('census', () => {
    const globals = readFileSync(GLOBALS, 'utf8');
    const tokens = colourTokens(globals);
    const rules = [...parseRules(globals, 'globals.css'), ...parseRules(readFileSync(MODULE, 'utf8'), 'run-progress.module.css')];
    const rendered = screens();
    const found = census(rendered, rules, tokens);
    const declared = declaredPairs(rules);
    console.log('\nDECLARED-ONLY (not reached by any rendered screen):');
    for (const [key, o] of declared) {
      if (!found.has(key)) {
        const bg = tokens.get(o.background) as string;
        const fg = tokens.get(o.foreground as `--am-${string}`) as string;
        console.log(`  ${contrastRatio(fg, bg).toFixed(2).padStart(6)}  ${o.foreground.padEnd(24)} on ${o.background.padEnd(22)} ${o.sites.join(' | ')}`);
      }
    }
    const rows = [...found.values()].map((o) => {
      const bg = tokens.get(o.background) as string;
      const colour = readColour(o.foreground.includes('@')
        ? `color-mix(in srgb, var(${o.foreground.split('@')[0]}) ${o.foreground.split('@')[1]?.replace('%','')}%, transparent)`
        : `var(${o.foreground})`);
      const fg = colour ? resolve(colour, tokens, bg, bg) : null;
      return { ...o, ratio: fg ? contrastRatio(fg, bg) : NaN, fgHex: fg, bgHex: bg };
    });
    rows.sort((a, b) => a.kind.localeCompare(b.kind) || a.ratio - b.ratio);
    console.log(`\nSCREENS: ${rendered.length}   PAIRS: ${rows.length}\n`);
    for (const r of rows) {
      console.log(
        `${r.kind.padEnd(8)} ${String(r.ratio.toFixed(2)).padStart(6)}  ${r.foreground.padEnd(26)} on ${r.background.padEnd(22)} state=${(r.state ?? '-').padEnd(14)} pseudo=${(r.pseudo ?? '-').padEnd(22)} n=${r.sites.length}  e.g. ${r.sites[0]}`,
      );
    }
    console.log('\nUNSUPPORTED SELECTORS:');
    for (const s of unsupported()) console.log('  ' + s);
  });
});
