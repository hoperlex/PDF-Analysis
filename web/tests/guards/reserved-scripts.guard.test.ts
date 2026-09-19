/**
 * Guard: a reserved npm script is reserved in exactly one place, and a landed one is
 * released everywhere.
 *
 * Three documents describe the same fact and nothing held them together:
 *
 *   - `web/package.json` routes the name, either to a real command or to the forwarder;
 *   - `web/scripts/reserved-forwarder.mjs` carries the `RESERVED` entry the forwarder
 *     prints when the name is run before its owner lands;
 *   - `web/FRONTEND_LOCK.json` `reserved_scripts` records the reservation in the seal.
 *
 * `D-29` and half of `D-26` are both what happens when they drift apart. `npm run
 * test:unit` forwarded to the placeholder and **exited 1 while all 38 files under
 * `web/tests/unit/` passed** — they run under `npm test`, so `make gate` covered them and
 * nothing was unguarded, but the named command lied, and a person who ran it concluded
 * the suite was broken. `e2e:pc01` was still reserved for `P3-QA-01` a day after
 * `W21-E2E` had taken the name and committed the journey, and could not edit the lock to
 * say so.
 *
 * The rule this enforces:
 *
 *     A name the forwarder still reserves must be routed to the forwarder and listed in
 *     the lock. A name routed to a real command must be reserved in neither.
 *
 * So releasing a reservation is a three-file edit that the suite requires be complete,
 * and forgetting one of the three is red rather than silent.
 */

import { describe, expect, it } from 'vitest';
import { join } from 'node:path';

import { LOCK_PATH, WEB_ROOT, readJson, readText } from './lib/repo';

const MANIFEST_PATH = join(WEB_ROOT, 'package.json');
const FORWARDER_PATH = join(WEB_ROOT, 'scripts', 'reserved-forwarder.mjs');
const FORWARDER_COMMAND = 'node scripts/reserved-forwarder.mjs';

interface Manifest {
  readonly scripts: Record<string, string>;
}
interface Lock {
  readonly reserved_scripts: Record<string, string>;
}

const manifest = readJson<Manifest>(MANIFEST_PATH);
const lock = readJson<Lock>(LOCK_PATH);

/**
 * The names the forwarder itself still reserves, read out of its source.
 *
 * Read rather than imported: importing would execute a module whose whole purpose is to
 * `process.exit` on the argument it is given.
 */
function forwarderReservations(source: string): string[] {
  const start = source.indexOf('const RESERVED = {');
  if (start < 0) throw new Error('reserved-forwarder.mjs has no RESERVED map');
  const block = source.slice(start, source.indexOf('\n};', start));
  // A key at the map's own indent, however the value is written. An earlier version of
  // this required the entry to open a block -- `'name': {` at end of line -- and a
  // mutation that re-reserved a landed name on a single line SURVIVED the whole guard,
  // because the reader simply did not see it. The detector must not depend on formatting
  // the thing it inspects is free to change.
  return [...block.matchAll(/^ {2}'([^']+)'\s*:/gm)].map((m) => m[1] as string);
}

/** The scripts routed at the forwarder, whatever name they carry. */
function forwardedScripts(scripts: Record<string, string>): string[] {
  return Object.entries(scripts)
    .filter(([, command]) => command.startsWith(FORWARDER_COMMAND))
    .map(([name]) => name);
}

describe('the three documents that reserve a script name agree', () => {
  const reserved = forwarderReservations(readText(FORWARDER_PATH));

  it('the forwarder still reserves at least one name, so this guard has something to check', () => {
    // A guard whose subject vanished would pass while checking nothing. When the last
    // reservation is released this assertion is the thing that says so out loud, and the
    // session that releases it deletes the forwarder and this file together.
    expect(reserved.length).toBeGreaterThan(0);
  });

  it('every name the forwarder reserves is routed to the forwarder', () => {
    for (const name of reserved) {
      expect(manifest.scripts[name], `package.json has no script '${name}'`).toBe(
        `${FORWARDER_COMMAND} ${name}`,
      );
    }
  });

  it('every script routed to the forwarder is a name the forwarder reserves', () => {
    // The other direction: a `scripts` entry pointing at the forwarder for a name it does
    // not know exits 2 with "is not a reserved script", which is a worse lie than D-29's.
    expect(forwardedScripts(manifest.scripts).sort()).toEqual([...reserved].sort());
  });

  it('the lock reserves exactly the names the forwarder reserves', () => {
    // This is the assertion that would have reddened on D-26's half: the lock kept
    // `e2e:pc01` after the forwarder entry for it became dead.
    expect(Object.keys(lock.reserved_scripts).sort()).toEqual([...reserved].sort());
  });

  it('a released name is reserved nowhere and runs something real', () => {
    for (const name of ['test:unit', 'e2e:pc01']) {
      expect(reserved, `${name} is still reserved by the forwarder`).not.toContain(name);
      expect(Object.keys(lock.reserved_scripts)).not.toContain(name);
      expect(manifest.scripts[name], `package.json dropped '${name}'`).toBeDefined();
      expect(manifest.scripts[name]).not.toContain('reserved-forwarder');
    }
  });

  it('test:unit runs the suite it is named after, and not a subset of it', () => {
    // `D-29` exactly. The name promises `web/tests/unit/**`, so the command must run that
    // directory -- not `tests/unit/review`, and not the whole suite under another name.
    expect(manifest.scripts['test:unit']).toBe('vitest run tests/unit');
  });
});

// ---------------------------------------------------------------------------------------
// The guard, shown able to fail
// ---------------------------------------------------------------------------------------

describe('each detector reddens on the exact drift it exists to catch', () => {
  const RESERVED_SOURCE = [
    'const RESERVED = {',
    "  'csv:verify': {",
    "    owner: 'the CSV export lane',",
    '  },',
    '};',
  ].join('\n');

  it('reads the reserved names out of the forwarder rather than assuming them', () => {
    expect(forwarderReservations(RESERVED_SOURCE)).toEqual(['csv:verify']);
  });

  it('sees an entry however it is formatted, block or single line', () => {
    // The mutation that survived: re-reserving a landed name on one line. The reader now
    // finds it, so the assertions above can fail on it.
    expect(
      forwarderReservations("const RESERVED = {\n  'test:unit': { owner: 'x' },\n};"),
    ).toEqual(['test:unit']);
    expect(forwarderReservations("const RESERVED = {\n  'a:b' : {\n},\n};")).toEqual(['a:b']);
  });

  it('does not read a quoted string from beyond the map as a reservation', () => {
    // The block ends at the map's closing brace, so prose below it is not scanned.
    expect(
      forwarderReservations("const RESERVED = {\n  'a:b': {},\n};\n  'not:a:name': 1"),
    ).toEqual(['a:b']);
  });

  it('a name released in package.json but left in the forwarder is visible', () => {
    // D-26's half, reconstructed: the command is real, the reservation is not withdrawn.
    const stale = forwarderReservations(
      RESERVED_SOURCE.replace("const RESERVED = {", "const RESERVED = {\n  'e2e:pc01': {\n    owner: 'the P3-QA-01 lane',\n  },"),
    );
    expect(stale).toContain('e2e:pc01');
    expect(stale).not.toEqual(Object.keys(lock.reserved_scripts));
  });

  it('a script still pointed at the forwarder is detected as forwarded', () => {
    // D-29's shape: the name exists, the suite exists, and the command is the placeholder.
    expect(
      forwardedScripts({
        'test:unit': `${FORWARDER_COMMAND} test:unit`,
        test: 'vitest run',
      }),
    ).toEqual(['test:unit']);
  });

  it('a real command is not mistaken for a forwarded one', () => {
    expect(forwardedScripts({ 'test:unit': 'vitest run tests/unit' })).toEqual([]);
  });
});
