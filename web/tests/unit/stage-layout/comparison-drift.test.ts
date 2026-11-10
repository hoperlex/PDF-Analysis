/**
 * `CMP-WEB-01` — the comparison cells of the two sets and their limits are the server's own tables.
 *
 * The form fills «Только Claude» and «Только Codex» from `comparisonKitCells` of `entities/stage-layout`; the server accepts a named set only
 * if the models and efforts of its four comparison cells are the table `COMPARISON_PRESET_CELLS` of `src/auditmanager/runs/stage_layout.py`
 * (`kit_does_not_match_cells`), and a cell the revision lacks takes `COMPARISON_DEFAULT_MAX_OUTPUT_TOKENS` and
 * `COMPARISON_DEFAULT_TIMEOUT_SECONDS`. The web has no other way to know them, so this test reads the Python source and compares, exactly as
 * `block-schemes-drift.test.ts` does for the schemes: a kind, a model, an effort or a limit changed on one side and not the other is red here
 * instead of a refusal an administrator meets.
 *
 * The parser is a function of the source text, so each case below can be shown to fail on a source that was altered.
 */

import { describe, expect, it } from 'vitest';

import { COMPARISON_LAYOUT_KIND_VALUES } from '@/shared/api';
import {
  COMPARISON_DEFAULT_EFFORT, COMPARISON_DEFAULT_TIMEOUT, COMPARISON_DEFAULT_TOKENS, COMPARISON_KIND_LABELS, NAMED_KITS, comparisonKitCells,
  newComparisonCell,
} from '@/entities/stage-layout';

import { modelConstants, readStageLayoutSource } from './stage-layout-source';

const SOURCE = readStageLayoutSource();

/** The text from `marker` to the first `close` after it; throws when either is missing, so a moved table is red, not empty. */
function block(source: string, marker: string, close: string): string {
  const start = source.indexOf(marker);
  if (start < 0) throw new Error(`stage_layout.py has no ${marker}`);
  const end = source.indexOf(close, start);
  if (end < 0) throw new Error(`${marker} is not closed by ${JSON.stringify(close)}`);
  return source.slice(start, end);
}

/** `"comparison_report": 8_000` -> {comparison_report: 8000}. */
function numbers(text: string): Map<string, number> {
  return new Map([...text.matchAll(/"(comparison_[a-z_]+)": ([0-9_]+)/g)].map(
    (match): [string, number] => [match[1] as string, Number((match[2] as string).replaceAll('_', ''))],
  ));
}

interface ServerComparison {
  readonly kinds: readonly string[];
  readonly tokens: Map<string, number>;
  readonly timeouts: Map<string, number>;
  /** kit -> kind -> "model:effort". */
  readonly presets: Map<string, Map<string, string>>;
}

/** `{kind: (_SONNET, "high") for kind in COMPARISON_KINDS}` or one `"kind": (_ASTRA, "high")` per kind. */
function presetOf(text: string, kinds: readonly string[], constants: Map<string, string>): Map<string, string> {
  const model = (name: string): string => {
    const value = constants.get(name);
    if (value === undefined) throw new Error(`unknown model constant ${name}`);
    return value;
  };
  const out = new Map<string, string>();
  const every = /\{kind: \((_[A-Z0-9_]+), "(low|medium|high)"\) for kind in COMPARISON_KINDS\}/.exec(text);
  if (every !== null) {
    for (const kind of kinds) out.set(kind, `${model(every[1] as string)}:${every[2]}`);
    return out;
  }
  for (const match of text.matchAll(/"(comparison_[a-z_]+)": \((_[A-Z0-9_]+), "(low|medium|high)"\)/g)) {
    out.set(match[1] as string, `${model(match[2] as string)}:${match[3]}`);
  }
  return out;
}

function parseServerComparison(source: string): ServerComparison {
  const constants = modelConstants(source);
  const kinds = [...block(source, 'COMPARISON_KINDS: Final', '\n)').matchAll(/"(comparison_[a-z_]+)"/g)].map((match) => match[1] as string);
  const presetBlock = block(source, 'COMPARISON_PRESET_CELLS: Final', '\n}\n');
  const claude = block(presetBlock, 'KIT_CLAUDE_ONLY: {', 'KIT_CODEX_ONLY: {');
  const codex = presetBlock.slice(presetBlock.indexOf('KIT_CODEX_ONLY: {'));
  return {
    kinds,
    tokens: numbers(block(source, 'COMPARISON_DEFAULT_MAX_OUTPUT_TOKENS: Final', '\n}')),
    timeouts: numbers(block(source, 'COMPARISON_DEFAULT_TIMEOUT_SECONDS: Final', '\n}')),
    presets: new Map([['claude_only', presetOf(claude, kinds, constants)], ['codex_only', presetOf(codex, kinds, constants)]]),
  };
}

/** What the web holds for the same four questions, in the shape the parser returns. */
function web(): ServerComparison {
  const kinds = [...COMPARISON_LAYOUT_KIND_VALUES] as string[];
  const presets = new Map<string, Map<string, string>>();
  for (const kit of NAMED_KITS) {
    presets.set(kit, new Map(comparisonKitCells(kit, []).map((cell): [string, string] => [cell.work_kind, `${cell.model_id}:${cell.effort}`])));
  }
  return {
    kinds,
    tokens: new Map(COMPARISON_LAYOUT_KIND_VALUES.map((kind): [string, number] => [kind, COMPARISON_DEFAULT_TOKENS[kind]])),
    timeouts: new Map(COMPARISON_LAYOUT_KIND_VALUES.map((kind): [string, number] => [kind, COMPARISON_DEFAULT_TIMEOUT[kind]])),
    presets,
  };
}

const plain = (comparison: ServerComparison) => ({
  kinds: comparison.kinds,
  tokens: [...comparison.tokens],
  timeouts: [...comparison.timeouts],
  presets: [...comparison.presets].map(([kit, table]) => [kit, [...table]]),
});

describe('the comparison cells of the sets are the server\'s tables', () => {
  it('reads four kinds, four limits, four timeouts and four cells of each set out of the Python source, so the parser can be wrong only loudly', () => {
    const server = parseServerComparison(SOURCE);
    expect(server.kinds).toEqual(['comparison_pair_check', 'comparison_sheet_changes', 'comparison_spec', 'comparison_report']);
    expect(server.tokens.size).toBe(4);
    expect(server.timeouts.size).toBe(4);
    expect([...server.presets.keys()]).toEqual(['claude_only', 'codex_only']);
    for (const table of server.presets.values()) expect(table.size).toBe(4);
  });

  it('has the same kinds, in the same order, as the contract\'s enum and as the labels', () => {
    expect(parseServerComparison(SOURCE).kinds).toEqual([...COMPARISON_LAYOUT_KIND_VALUES]);
    expect(Object.keys(COMPARISON_KIND_LABELS).sort()).toEqual([...COMPARISON_LAYOUT_KIND_VALUES].sort());
  });

  it('has the same answer limit and call window for every kind', () => {
    const server = parseServerComparison(SOURCE);
    const mine = web();
    expect([...mine.tokens]).toEqual([...server.tokens]);
    expect([...mine.timeouts]).toEqual([...server.timeouts]);
  });

  it('fills each set with the model and the effort of every kind that the server\'s set has, and with the limits of the kind', () => {
    const server = parseServerComparison(SOURCE);
    for (const kit of NAMED_KITS) {
      expect([...(web().presets.get(kit) ?? [])], kit).toEqual([...(server.presets.get(kit) ?? [])]);
      expect(comparisonKitCells(kit, []).map((cell) => [cell.work_kind, cell.max_output_tokens, cell.timeout_seconds])).toEqual(
        COMPARISON_LAYOUT_KIND_VALUES.map((kind) => [kind, server.tokens.get(kind), server.timeouts.get(kind)]),
      );
    }
  });

  it('gives a kind chosen in «Свой набор» the effort the sets use, and the limits of the kind', () => {
    expect(COMPARISON_DEFAULT_EFFORT).toBe('high');
    const server = parseServerComparison(SOURCE);
    for (const table of server.presets.values()) {
      for (const pair of table.values()) expect(pair.endsWith(`:${COMPARISON_DEFAULT_EFFORT}`)).toBe(true);
    }
    expect(newComparisonCell('comparison_spec', 'gpt-6-astra', 'high')).toEqual({
      work_kind: 'comparison_spec', model_id: 'gpt-6-astra', effort: 'high', max_output_tokens: server.tokens.get('comparison_spec'),
      timeout_seconds: server.timeouts.get('comparison_spec'),
    });
  });
});

describe('the comparison of the web and the server can disagree, and this test sees it', () => {
  const same = plain(web());

  it('is equal on the source as it stands', () => {
    expect(plain(parseServerComparison(SOURCE))).toEqual(same);
  });

  it('is red when a kind of a set moves to another model', () => {
    const altered = SOURCE.replace('"comparison_spec": (_ASTRA, "high")', '"comparison_spec": (_SOL, "high")');
    expect(altered).not.toBe(SOURCE);
    expect(plain(parseServerComparison(altered))).not.toEqual(same);
  });

  it('is red when the effort of the Claude set changes', () => {
    const altered = SOURCE.replace('{kind: (_SONNET, "high") for kind in COMPARISON_KINDS}', '{kind: (_SONNET, "medium") for kind in COMPARISON_KINDS}');
    expect(altered).not.toBe(SOURCE);
    expect(plain(parseServerComparison(altered))).not.toEqual(same);
  });

  it('is red when a limit or a window changes', () => {
    const tokens = SOURCE.replace('"comparison_report": 8_000', '"comparison_report": 8_001');
    const timeout = SOURCE.replace('"comparison_sheet_changes": 1_800', '"comparison_sheet_changes": 1_801');
    expect(tokens).not.toBe(SOURCE);
    expect(timeout).not.toBe(SOURCE);
    expect(plain(parseServerComparison(tokens))).not.toEqual(same);
    expect(plain(parseServerComparison(timeout))).not.toEqual(same);
  });

  it('is red when a fifth kind appears on the server', () => {
    const altered = SOURCE.replace('"comparison_spec", "comparison_report",\n)', '"comparison_spec", "comparison_report", "comparison_extra",\n)');
    expect(altered).not.toBe(SOURCE);
    expect(plain(parseServerComparison(altered))).not.toEqual(same);
  });

  it('refuses a source in which the table has moved, instead of reading nothing', () => {
    expect(() => parseServerComparison(SOURCE.replaceAll('COMPARISON_PRESET_CELLS: Final', 'RENAMED: Final'))).toThrow(/COMPARISON_PRESET_CELLS/);
  });
});
