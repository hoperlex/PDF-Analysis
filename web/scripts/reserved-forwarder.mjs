#!/usr/bin/env node
/**
 * Reserved npm-script forwarder.
 *
 * FF-01 froze the nine `make` targets and OD-16 forbids adding one for the frontend, so
 * every P03 command is `npm --prefix web run ...`. The names below are reserved here by
 * the toolchain owner so a later session fills one in rather than inventing a new name
 * that no runbook mentions. Until its owner lands, a reserved script fails explicitly
 * and says who owns it: silence would be indistinguishable from a passing suite.
 *
 * A later owner replaces the `scripts` entry in package.json with the real command. No
 * one renames a reserved name.
 *
 * **Releasing a name is a three-file edit and all three are required.** The `scripts`
 * entry, the `RESERVED` entry here, and `web/FRONTEND_LOCK.json` `reserved_scripts` must
 * be changed together, and `web/tests/guards/reserved-scripts.guard.test.ts` holds them
 * to it. Two names were released by `W22-WEB` because two of the three had drifted:
 *
 *   - `test:unit` (`D-29`) exited 1 from this forwarder while all 38 files under
 *     `web/tests/unit/` passed under `npm test`. Nothing was unguarded -- `make gate`
 *     runs them -- but the named command lied, and a person who ran it concluded the
 *     suite was broken. It now runs the directory it is named after;
 *   - `e2e:pc01` (`D-26`) was taken by `W21-E2E`, whose journey is committed at
 *     `tests/e2e/pc01/journey/`; `package.json` already pointed at it and only this
 *     entry and the lock still said the name was unclaimed.
 *
 * `csv:verify` is genuinely unclaimed: `web/tests/contract/csv/` does not exist.
 */

const RESERVED = {
  'csv:verify': {
    owner: 'the CSV export lane (B5 produces, B8 downloads)',
    delivers: 'verification of the seventeen frozen CSV columns of P02_SEAMS.md section 6',
    path: 'web/tests/contract/csv/**',
  },
};

const name = process.argv[2];
const entry = name === undefined ? undefined : RESERVED[name];

if (entry === undefined) {
  console.error(
    `reserved-forwarder: '${String(name)}' is not a reserved script. ` +
      `Reserved names are: ${Object.keys(RESERVED).sort().join(', ')}.`,
  );
  process.exit(2);
}

console.error(
  [
    `npm run ${name}: NOT IMPLEMENTED - this is a reserved forwarder, not a passing test run.`,
    '',
    `  owner:    ${entry.owner}`,
    `  delivers: ${entry.delivers}`,
    `  path:     ${entry.path}`,
    '',
    'The name is reserved by web/package.json so the command that eventually runs this',
    'suite is already written down. Fill it in; do not rename it, and do not add a',
    'Makefile target for it (OD-16).',
  ].join('\n'),
);
process.exit(1);
