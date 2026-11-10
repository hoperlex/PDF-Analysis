/**
 * `HOSTS-ENSEMBLE-01` — the three schemes of the blocks row and the two sets are the server's own lists.
 *
 * The form offers `BLOCK_SCHEMES` of `entities/stage-layout` and fills a set from `kitCells`; the server validates a revision against
 * `BLOCK_SCHEMES` and `PRESET_CELLS` of `src/auditmanager/runs/stage_layout.py` and refuses what is not on them. The web has no other
 * way to know the lists (the contract carries no scheme id), so this test reads the Python source and compares: a scheme added,
 * removed or re-modelled on one side and not the other is red here instead of a refusal an administrator meets.
 */

import { describe, expect, it } from 'vitest';

import { BLOCK_SCHEMES, kitCells } from '@/entities/stage-layout';

import { modelConstants as constantsOf, readStageLayoutSource } from './stage-layout-source';

const SOURCE = readStageLayoutSource();

/** `_OPUS, _SONNET = "claude-opus-5-5", "claude-sonnet-5-5"` -> {_OPUS: ..., _SONNET: ...}. */
const modelConstants = (): Map<string, string> => constantsOf(SOURCE);

/** The (role, model, effort) triples of one `(("leg1", _OPUS, "medium"), ...)` tuple. */
function triples(text: string, constants: Map<string, string>): string[] {
  return [...text.matchAll(/\("(main|leg1|leg2|judge)", (_[A-Z0-9_]+), "(low|medium|high)"\)/g)].map((match) => {
    const model = constants.get(match[2] as string);
    if (model === undefined) throw new Error(`unknown model constant ${match[2]}`);
    return `${match[1]}:${model}:${match[3]}`;
  });
}

function serverSchemes(): { id: string; cells: string[] }[] {
  const constants = modelConstants();
  const start = SOURCE.indexOf('BLOCK_SCHEMES: Final');
  const end = SOURCE.indexOf('\n)\n', start);
  const body = SOURCE.slice(start, end);
  return body.split('BlockScheme(').slice(1).map((entry) => ({
    id: /^"([a-z_]+)"/.exec(entry)?.[1] as string,
    cells: triples(entry.slice(entry.indexOf('(('), entry.length), constants),
  }));
}

describe('the schemes of the blocks row are the server\'s closed list', () => {
  it('reads three schemes out of the Python source, so the parser can be wrong only loudly', () => {
    const server = serverSchemes();
    expect(server.map((scheme) => scheme.id)).toEqual(['claude_opus_judge_sonnet', 'codex_astra_sol_judge', 'codex_astra_single']);
    expect(server.every((scheme) => scheme.cells.length > 0)).toBe(true);
  });

  it('has the same ids, in the same order, with the same role, model and effort of every cell', () => {
    const web = BLOCK_SCHEMES.map((scheme) => ({
      id: scheme.id,
      cells: scheme.cells.map((cell) => `${cell.role}:${cell.model_id}:${cell.effort}`),
    }));
    expect(web).toEqual(serverSchemes());
  });

  it('fills each set with the blocks row of the scheme the server\'s set has', () => {
    const preset = SOURCE.slice(SOURCE.indexOf('PRESET_CELLS: Final'));
    const server = (kit: string) => {
      const table = preset.slice(preset.indexOf(`${kit}: {`));
      const row = /"blocks": (BLOCK_SCHEMES\[\d\])/.exec(table)?.[1] as string;
      const index = Number(/\[(\d)\]/.exec(row)?.[1]);
      return serverSchemes()[index]?.cells ?? [];
    };
    const blocksOf = (kit: 'claude_only' | 'codex_only') =>
      kitCells(kit).filter((cell) => cell.row === 'blocks').map((cell) => `${cell.role}:${cell.model_id}:${cell.effort}`);
    expect(blocksOf('claude_only')).toEqual(server('KIT_CLAUDE_ONLY'));
    expect(blocksOf('codex_only')).toEqual(server('KIT_CODEX_ONLY'));
  });
});
