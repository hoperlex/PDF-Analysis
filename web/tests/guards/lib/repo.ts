/**
 * Shared helpers for the guard and contract suites.
 *
 * These live under `tests/guards/lib/` rather than a `tests/support/` of their own so the
 * whole helper surface sits inside a path this session owns. The contract suite imports
 * them across the directory boundary on purpose.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** `<repo>/web` */
export const WEB_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');

/** The repository root. The frozen contract lives under it and is read-only here. */
export const REPO_ROOT = resolve(WEB_ROOT, '..');

export const CONTRACT_PATH = join(REPO_ROOT, 'contracts', 'api', 'v1', 'openapi.json');
export const SNAPSHOT_PATH = join(WEB_ROOT, 'openapi', 'openapi.json');
export const GENERATED_DIR = join(WEB_ROOT, 'src', 'shared', 'api', 'generated');
export const GENERATOR_PATH = join(WEB_ROOT, 'scripts', 'generate-api-client.mjs');
export const LOCK_PATH = join(WEB_ROOT, 'FRONTEND_LOCK.json');
export const SEAMS_PATH = join(REPO_ROOT, 'docs', 'program', 'P02_SEAMS.md');

export function readText(path: string): string {
  return readFileSync(path, 'utf8');
}

export function readJson<T>(path: string): T {
  return JSON.parse(readText(path)) as T;
}

export function sha256File(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

/** Every file under `root`, as repo-relative POSIX paths, sorted and deterministic. */
export function walkFiles(root: string, predicate: (path: string) => boolean = () => true): string[] {
  const found: string[] = [];
  const visit = (dir: string): void => {
    for (const entry of readdirSync(dir).sort()) {
      if (entry === 'node_modules' || entry === '.next') continue;
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) visit(full);
      else if (predicate(full)) found.push(full);
    }
  };
  visit(root);
  return found;
}

/** A path as the repository sees it, for readable assertion messages. */
export function repoRelative(path: string): string {
  return relative(REPO_ROOT, path).split('\\').join('/');
}
