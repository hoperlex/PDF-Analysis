#!/usr/bin/env node
/**
 * Turn the two browser envelopes into one release verdict.
 *
 * This file deliberately does not drive a browser. `journey.mjs` and `refusals.mjs`
 * produce the observations; this checker prevents a shorter, recorded or partially
 * executed drive from being presented as the public-alpha acceptance run.
 */

import { createHash } from 'node:crypto';
import { lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (!flag.startsWith('--') || i + 1 >= argv.length) {
      throw new Error(`verify-acceptance: ${flag} needs a value`);
    }
    args[flag.slice(2)] = argv[++i];
  }
  for (const name of [
    'journey',
    'refusals',
    'out',
    'candidate-sha',
    'deployed-sha',
    'origin',
    'candidate-build-id',
    'journey-exit',
    'refusals-exit',
  ]) {
    if (args[name] === undefined) throw new Error(`verify-acceptance: --${name} is required`);
  }
  return args;
}

function readJson(path) {
  try {
    return { value: JSON.parse(readFileSync(resolve(path), 'utf8')), error: null };
  } catch (error) {
    return { value: null, error: error.message };
  }
}

const REPOSITORY_ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const BUILD_INPUTS = [
  'src/', 'db/', 'contracts/', 'fixtures/recorded/', 'release-notes/',
  'docs/program/P02_LOCK.json', 'VERSION', 'uv.lock',
];

function independentlyMeasuredBuildId() {
  const dockerfile = readFileSync(resolve(REPOSITORY_ROOT, 'infra/deploy/Dockerfile.api'), 'utf8');
  const runtimeSources = new Set(
    [...dockerfile.matchAll(/^COPY ([^\s]+) (\/app\/[^\s]+)$/gm)]
      .filter(([, source, destination]) => destination === `/app/${source}`)
      .map(([, source]) => source),
  );
  for (const source of BUILD_INPUTS) {
    if (!runtimeSources.has(source)) throw new Error(`Dockerfile.api omits build input ${source}`);
  }
  const names = [];
  function walk(relative) {
    const absolute = resolve(REPOSITORY_ROOT, relative);
    const stat = lstatSync(absolute);
    if (stat.isSymbolicLink()) throw new Error(`build input is a symlink: ${relative}`);
    if (stat.isDirectory()) {
      for (const child of readdirSync(absolute).sort()) {
        if (child === '__pycache__') continue;
        walk(`${relative}${relative.endsWith('/') ? '' : '/'}${child}`);
      }
    } else if (stat.isFile() && !relative.endsWith('.pyc')) {
      names.push(relative);
    }
  }
  for (const source of BUILD_INPUTS) walk(source);
  const manifest = createHash('sha256');
  for (const name of names.sort()) {
    const digest = createHash('sha256').update(readFileSync(resolve(REPOSITORY_ROOT, name))).digest('hex');
    manifest.update(`${name}\t${digest}\n`);
  }
  return `b${manifest.digest('hex').slice(0, 16)}`;
}

async function readServedProductVersion(origin) {
  const login = process.env.E2E_PC01_LOGIN;
  const password = process.env.E2E_PC01_PASSWORD;
  if (!login || !password) return { outcome: 'BLOCKED', reason: 'reviewer credential is absent', body: null };
  try {
    const auth = await fetch(`${origin}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ login, password }),
      signal: AbortSignal.timeout(20_000),
    });
    if (auth.status !== 200) return { outcome: 'BLOCKED', reason: `credential exchange returned ${auth.status}`, body: null };
    const issued = await auth.json();
    if (typeof issued?.token !== 'string' || !issued.token) {
      return { outcome: 'FAIL', reason: 'credential exchange returned no token', body: null };
    }
    const version = await fetch(`${origin}/api/v1/system/version`, {
      headers: { authorization: `Bearer ${issued.token}` },
      signal: AbortSignal.timeout(20_000),
    });
    if (version.status !== 200) return { outcome: 'BLOCKED', reason: `version read returned ${version.status}`, body: null };
    const body = await version.json();
    if (typeof body?.product_version !== 'string' || typeof body?.build_id !== 'string' ||
        typeof body?.contract_version !== 'string') {
      return { outcome: 'FAIL', reason: 'version response is malformed', body: null };
    }
    return { outcome: 'PASS', reason: null, body };
  } catch {
    // Never serialize a response body, credential, token, URL or transport exception.
    return { outcome: 'BLOCKED', reason: 'version service is unavailable', body: null };
  }
}

function decodeBody(body) {
  if (typeof body !== 'string') return null;
  try {
    return JSON.parse(body);
  } catch {
    return null;
  }
}

function responseObjects(journey) {
  const objects = [];
  for (const step of journey?.write?.steps ?? []) {
    for (const exchange of step.exchanges ?? []) {
      const body = decodeBody(exchange.responseBody);
      if (body !== null && typeof body === 'object') objects.push({ exchange, body });
    }
  }
  return objects;
}

function isCurrentRunReading(item, runId) {
  if (typeof runId !== 'string' || item.exchange?.method !== 'GET') return false;
  try {
    return new URL(item.exchange.url).pathname.endsWith(`/runs/${runId}`);
  } catch {
    return false;
  }
}

const args = parseArgs(process.argv.slice(2));
const expectedVersion = readFileSync(resolve(REPOSITORY_ROOT, 'VERSION'), 'utf8').trim();
const expectedContractVersion = JSON.parse(
  readFileSync(resolve(REPOSITORY_ROOT, 'contracts/api/v1/openapi.json'), 'utf8'),
).info.version;
let independentBuildId = null;
let buildInputError = null;
try {
  independentBuildId = independentlyMeasuredBuildId();
} catch (error) {
  buildInputError = error instanceof Error ? error.message : 'build inputs are unavailable';
}
const servedVersion = await readServedProductVersion(args.origin);
const journeyRead = readJson(args.journey);
const refusalsRead = readJson(args.refusals);
const journey = journeyRead.value;
const refusals = refusalsRead.value;
const findings = [];
if (buildInputError !== null) findings.push(buildInputError);
if (servedVersion.reason !== null) findings.push(servedVersion.reason);
const buildIdPattern = /^b[0-9a-f]{16}$/;
const buildParity = buildInputError === null && servedVersion.outcome === 'PASS' &&
  buildIdPattern.test(args['candidate-build-id']) &&
  args['candidate-build-id'] === independentBuildId &&
  servedVersion.body.build_id === independentBuildId &&
  servedVersion.body.product_version === expectedVersion &&
  servedVersion.body.contract_version === expectedContractVersion;
if (!buildIdPattern.test(args['candidate-build-id'])) findings.push('candidate build ID is malformed');
if (independentBuildId !== null && args['candidate-build-id'] !== independentBuildId) {
  findings.push('shell and verifier measured different candidate builds');
}
if (servedVersion.body !== null) {
  if (servedVersion.body.build_id !== independentBuildId) findings.push('served API build differs from candidate');
  if (servedVersion.body.product_version !== expectedVersion) findings.push('served product version differs from candidate');
  if (servedVersion.body.contract_version !== expectedContractVersion) findings.push('served contract version differs from candidate');
}

// How many cold routes a complete read phase walks: the number the journey manifest beside
// this file declares, not a literal. Until W50 this was `16` written six times, and a wave that
// added a screen left the gate green while this release check would have failed on the stand.
// `tests/e2e/test_pc01_journey_conformance.py` holds the manifest's routes to the `page.tsx`
// set in every gate, so this is the number of screens the checked-out candidate has. An
// unreadable manifest declares nothing, and nothing equals it: the verdict is FAIL.
const manifestRead = readJson(fileURLToPath(new URL('./manifest.json', import.meta.url)));
const declaredRoutes = Array.isArray(manifestRead.value?.routes)
  ? manifestRead.value.routes.length
  : null;
if (declaredRoutes === null) {
  findings.push(`journey manifest is unavailable: ${manifestRead.error ?? 'it declares no routes'}`);
}

const expect = (condition, message) => {
  if (!condition) findings.push(message);
};

const shaPattern = /^[0-9a-f]{40}$/;
const identityOk =
  shaPattern.test(args['candidate-sha']) &&
  shaPattern.test(args['deployed-sha']) &&
  args['candidate-sha'] === args['deployed-sha'];
expect(shaPattern.test(args['candidate-sha']), 'candidate SHA is not a full lowercase SHA-1');
expect(shaPattern.test(args['deployed-sha']), 'deployed SHA is not a full lowercase SHA-1');
expect(args['candidate-sha'] === args['deployed-sha'], 'candidate SHA and deployed SHA differ');

const journeyExit = Number.parseInt(args['journey-exit'], 10);
const refusalsExit = Number.parseInt(args['refusals-exit'], 10);
expect(Number.isInteger(journeyExit), 'journey exit code is not an integer');
expect(Number.isInteger(refusalsExit), 'refusals exit code is not an integer');

if (journeyRead.error !== null) findings.push(`journey envelope is unavailable: ${journeyRead.error}`);
if (refusalsRead.error !== null) findings.push(`refusal envelope is unavailable: ${refusalsRead.error}`);

const runId = journey?.write?.captured?.run_id ?? null;
const currentRunReadings = responseObjects(journey).filter((item) =>
  isCurrentRunReading(item, runId),
);
const terminalReading = [...currentRunReadings]
  .reverse()
  .find((item) => ['published', 'partial', 'failed'].includes(item.body?.state));
const dependencyUnavailable = currentRunReadings.some(
  ({ body }) =>
    body?.error_code === 'dependency_unavailable' ||
    body?.terminal_reason === 'dependency_unavailable' ||
    (body?.stages ?? []).some((stage) => stage?.error_code === 'dependency_unavailable'),
);
const failedTextAnalysis = currentRunReadings.some(({ body }) =>
  (body?.stages ?? []).some(
    (stage) => stage?.stage_id === 'text_analysis' && stage?.status === 'failed',
  ),
);

if (journey !== null) {
  expect(journey.phase === 'all', `journey phase is ${JSON.stringify(journey.phase)}, expected "all"`);
  expect(journey.session?.opened === true, 'sign-in did not open a session');
  expect(journey.viewport?.width === 780, 'journey viewport width is not 780px');
  expect(journey.viewport?.height === 900, 'journey viewport height is not 900px');
  expect(journey.write?.ran === true, 'write phase did not run');
  expect(journey.write?.stepsDeclared === 3, 'write phase does not declare exactly 3 steps');
  expect(journey.write?.stepsChecked === 3, 'write phase did not check 3/3 steps');
  expect(journey.write?.stoppedAt === null, 'write phase stopped before completion');
  expect(
    journey.routesDeclared === declaredRoutes,
    `read phase does not declare exactly the ${declaredRoutes} routes of the manifest`,
  );
  expect(
    journey.routesChecked === declaredRoutes,
    `read phase did not check ${declaredRoutes}/${declaredRoutes} cold routes`,
  );
  expect(Array.isArray(journey.failures) && journey.failures.length === 0, 'journey contains findings');
  expect(
    Array.isArray(journey.records) && journey.records.length === declaredRoutes,
    'journey has no record for every route',
  );
  for (const record of journey.records ?? []) {
    expect(record?.width?.innerWidth === 780, `${record?.name ?? 'unknown route'} was not measured at 780px`);
    expect(
      Number.isFinite(record?.width?.scrollWidth) &&
        record.width.scrollWidth <= record.width.innerWidth,
      `${record?.name ?? 'unknown route'} has horizontal overflow or no width reading`,
    );
  }
  expect(terminalReading !== undefined, 'the newly created run has no terminal status reading');
  expect(
    ['published', 'partial'].includes(terminalReading?.body?.state),
    `the newly created run ended as ${JSON.stringify(terminalReading?.body?.state ?? null)}`,
  );
  expect(
    terminalReading?.body?.provider_mode === 'live',
    `the newly created run reports provider_mode ${JSON.stringify(terminalReading?.body?.provider_mode ?? null)}, expected "live"`,
  );
  expect(!failedTextAnalysis, 'the newly created run has a failed text_analysis stage');
}

if (refusals !== null) {
  expect(Array.isArray(refusals.records), 'refusal envelope has no records array');
  expect(refusals.records?.length === 6, 'refusal phase did not drive exactly 6 fixtures');
  for (const record of refusals.records ?? []) {
    expect(
      Array.isArray(record.findings) && record.findings.length === 0,
      `${record.fixture ?? 'unknown refusal fixture'} contains a refusal finding`,
    );
  }
}

expect(journeyExit === 0, `journey process exited ${journeyExit}`);
expect(refusalsExit === 0, `refusal process exited ${refusalsExit}`);

const journeyFailuresClean = Array.isArray(journey?.failures) && journey.failures.length === 0;
const writeComplete =
  journey?.phase === 'all' &&
  journey?.write?.ran === true &&
  journey?.write?.stepsChecked === 3 &&
  journey?.write?.stepsDeclared === 3 &&
  journey?.write?.stoppedAt === null;
const routesComplete =
  journey?.phase === 'all' &&
  declaredRoutes !== null &&
  journey?.routesChecked === declaredRoutes &&
  journey?.routesDeclared === declaredRoutes;
const widthComplete =
  journey?.viewport?.width === 780 &&
  journey?.viewport?.height === 900 &&
  declaredRoutes !== null &&
  journey?.records?.length === declaredRoutes &&
  journey.records.every(
    (record) =>
      record?.width?.innerWidth === 780 &&
      Number.isFinite(record?.width?.scrollWidth) &&
      record.width.scrollWidth <= record.width.innerWidth,
  );
const providerComplete =
  journeyExit === 0 &&
  journeyFailuresClean &&
  !failedTextAnalysis &&
  terminalReading?.body?.provider_mode === 'live' &&
  ['published', 'partial'].includes(terminalReading?.body?.state);
const refusalRecordsValid =
  Array.isArray(refusals?.records) &&
  refusals.records.length === 6 &&
  refusals.records.every((record) => Array.isArray(record?.findings));
const refusalsComplete =
  refusalsExit === 0 &&
  refusalRecordsValid &&
  refusals.records.every((record) => record.findings.length === 0);
const refusalHasFinding =
  Array.isArray(refusals?.records) &&
  refusals.records.some(
    (record) => Array.isArray(record?.findings) && record.findings.length > 0,
  );
const refusalsBlockedByDependency =
  dependencyUnavailable && refusalsExit === 99 && refusalsRead.error !== null;

const phases = {
    apiBuild: {
      outcome: buildParity ? 'PASS' : servedVersion.outcome === 'BLOCKED' &&
        buildInputError === null && args['candidate-build-id'] === independentBuildId ? 'BLOCKED' : 'FAIL',
      candidateMeasured: independentBuildId,
      servedMeasured: servedVersion.body?.build_id ?? null,
      productVersion: servedVersion.body?.product_version ?? null,
      contractVersion: servedVersion.body?.contract_version ?? null,
    },
    identity: {
      outcome: identityOk ? 'PASS' : 'FAIL',
    },
    signIn: { outcome: journey?.session?.opened === true ? 'PASS' : 'FAIL' },
    write: {
      outcome: writeComplete ? 'PASS' : 'FAIL',
      checked: journey?.write?.stepsChecked ?? 0,
      declared: journey?.write?.stepsDeclared ?? 0,
    },
    coldRoutes: {
      outcome: routesComplete ? 'PASS' : 'FAIL',
      checked: journey?.routesChecked ?? 0,
      declared: journey?.routesDeclared ?? 0,
    },
    width780: {
      outcome: widthComplete ? 'PASS' : 'FAIL',
    },
    providerLive: {
      outcome: dependencyUnavailable ? 'BLOCKED' : providerComplete ? 'PASS' : 'FAIL',
      observed: terminalReading?.body?.provider_mode ?? null,
    },
    refusals: {
      outcome: refusalsComplete
        ? 'PASS'
        : refusalsBlockedByDependency && !refusalHasFinding
          ? 'BLOCKED'
          : 'FAIL',
      checked: refusals?.records?.length ?? 0,
      declared: 6,
    },
};

// The root verdict is a projection of the required phase verdicts. In particular, a provider
// outage cannot turn into PASS merely because the browser observed a legitimate `partial`
// terminal and exited zero. FAIL wins over BLOCKED; PASS requires every phase to pass.
const phaseOutcomes = Object.values(phases).map((phase) => phase.outcome);
const verdict = phaseOutcomes.includes('FAIL')
  ? 'FAIL'
  : phaseOutcomes.includes('BLOCKED')
    ? 'BLOCKED'
    : 'PASS';
const evidence = {
  schema: 'w48-alpha-acceptance/v1',
  candidateSha: args['candidate-sha'],
  deployedSha: args['deployed-sha'],
  origin: journey?.origin ?? refusals?.origin ?? null,
  phases,
  processes: { journeyExit, refusalsExit },
  humanChecklist: { required: true, automated: false, outcome: 'PENDING' },
  findings,
  verdict,
};

mkdirSync(dirname(resolve(args.out)), { recursive: true });
writeFileSync(resolve(args.out), `${JSON.stringify(evidence, null, 2)}\n`);
console.log(`acceptance evidence: ${resolve(args.out)}`);
console.log(`acceptance verdict: ${verdict}`);
for (const finding of findings) console.error(`  - ${finding}`);
process.exit(verdict === 'PASS' ? 0 : verdict === 'BLOCKED' ? 2 : 1);
