/**
 * The Python source of the stage layout, read for the drift tests of `tests/unit/stage-layout`: the web has no other way to know the
 * server's closed lists (the contract carries no scheme id and no table of a set), so a test reads `src/auditmanager/runs/stage_layout.py`
 * and compares. Not a test itself.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { REPO_ROOT } from '../../guards/lib/repo';

export function readStageLayoutSource(): string {
  return readFileSync(join(REPO_ROOT, 'src/auditmanager/runs/stage_layout.py'), 'utf8');
}

/** `_OPUS, _SONNET = "claude-opus-5-5", "claude-sonnet-5-5"` -> {_OPUS: ..., _SONNET: ...}. */
export function modelConstants(source: string): Map<string, string> {
  const constants = new Map<string, string>();
  for (const line of source.split('\n')) {
    const match = /^(_[A-Z0-9_]+(?:, _[A-Z0-9_]+)*) = ("[^"]+"(?:, "[^"]+")*)$/.exec(line);
    if (match === null) continue;
    const names = (match[1] as string).split(', ');
    const values = [...(match[2] as string).matchAll(/"([^"]+)"/g)].map((value) => value[1] as string);
    names.forEach((name, at) => constants.set(name, values[at] as string));
  }
  return constants;
}
