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
 */

const RESERVED = {
  'test:unit': {
    owner: 'Gate B sessions B7 and B8',
    delivers: 'unit tests for the _pages, widgets, features and entities slices',
    path: 'web/tests/unit/**',
  },
  'e2e:pc01': {
    owner: 'the P3-QA-01 lane',
    delivers: 'the end-to-end PC-01 journey suite and its Playwright configuration',
    path: 'tests/e2e/pc01/**',
  },
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
