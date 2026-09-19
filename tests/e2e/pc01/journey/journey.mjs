#!/usr/bin/env node
/**
 * The PC-01 end-to-end journey.
 *
 *     npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500
 *
 * **What it is for.** `D-5` -- `POST /api/v1/runs` answered 500 twice on 2026-09-16 --
 * closed *not reproducible*, permanently, because the harness that saw it logged status
 * lines only and then died with its worktree. Three browser harnesses since then have each
 * lived outside the repository and each one is gone. This file is the instrument, in the
 * tree, under a name `web/package.json` reserved for it before it existed.
 *
 * **What it records.** For every request the browser makes: method, URL, the request
 * headers that matter, whether the request carried a credential, the request body, the
 * status, the response headers that matter, and **the response body**. Plus what the page
 * rendered, the links it offered, its console errors and any uncaught exception. The body
 * is fetched from the browser before its process ends, which is precisely the step whose
 * absence made `D-5` unanswerable.
 *
 * **Cold loads.** Every route is visited by a **separate browser process with its own
 * throwaway profile**: no cache, no storage, no cookies, no prior client state. `D-16` --
 * "no screen can reach anything after a page reload" -- survived four certifications
 * because every one of them navigated within a single warm page. `cdp.mjs` offers no way
 * to reuse a browser, so this property cannot be lost by forgetting it.
 *
 * **One origin, no credential.** The browser is given an origin and nothing else. It
 * follows the app's own links to find every identifier it uses -- it is handed no project,
 * document, version or run id, and it holds no token. `T-6` says the credential lives in
 * the BFF route handler server-side; the journey asserts the browser never presented one.
 *
 * **Two phases, one instrument, one exit code.** The *write* half -- create a project,
 * upload the AR PDF, start a run, wait for the run's terminal -- is `write.mjs`, driven
 * from the `write` section of the same `manifest.json` and recorded into the same
 * envelope. `W21-E2E` left it named in `D-30` rather than written unexecuted; `W22-E2E`
 * built it against a stack it could write to. `--phase read|write|all` selects, and the
 * default is `all`: a phase that is skipped is printed and recorded as skipped, because a
 * partial green that does not say so is `D-23` in a different costume.
 *
 * **Order: write first, then read.** The read walk discovers every identifier by following
 * the links the pages render and is handed nothing, so it is not coupled to what the write
 * half just made -- but running the write half first means the origin has, at minimum, one
 * project with a document, a version and a published run in it, which is the state the read
 * walk needs and used to have to assume.
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';
import { runWritePhase } from './write.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {
    origin: process.env.E2E_PC01_ORIGIN,
    manifest: null,
    out: null,
    phase: process.env.E2E_PC01_PHASE ?? 'all',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (flag === '--origin') args.origin = argv[++i];
    else if (flag === '--manifest') args.manifest = argv[++i];
    else if (flag === '--out') args.out = argv[++i];
    else if (flag === '--phase') args.phase = argv[++i];
    else {
      console.error(`e2e:pc01: unknown argument '${flag}'`);
      process.exit(2);
    }
  }
  if (!['read', 'write', 'all'].includes(args.phase)) {
    console.error(`e2e:pc01: --phase must be read, write or all (got '${args.phase}')`);
    process.exit(2);
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));

if (!args.origin) {
  console.error(
    [
      'e2e:pc01: no origin.',
      '',
      '  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT',
      '  E2E_PC01_ORIGIN=http://127.0.0.1:PORT npm --prefix web run e2e:pc01',
      '',
      'There is deliberately no default. A default origin is how a journey ends up',
      'driving another lane\'s stack, and FF-01 section 5 forbids sharing live service',
      'state between lanes.',
    ].join('\n'),
  );
  process.exit(2);
}

const ORIGIN = args.origin.replace(/\/+$/, '');
const MANIFEST_PATH = resolve(args.manifest ?? join(HERE, 'manifest.json'));
const OUT_DIR = resolve(args.out ?? process.env.E2E_PC01_OUT ?? join(HERE, '.out'));

const manifest = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'));
const ID = manifest.identifier_pattern;
const API_PREFIX = manifest.api_prefix;

/** `{project_uid}` -> the captured value, or a hard failure naming what is missing. */
function fill(template, captured) {
  return template.replace(/\{([a-z_]+)\}/g, (_, name) => {
    const value = captured[name];
    if (value === undefined) {
      throw new Error(
        `route needs {${name}} but no earlier route captured it; ` +
          `captured so far: ${Object.keys(captured).join(', ') || '(nothing)'}`,
      );
    }
    return value;
  });
}

/** An API expectation, made concrete: `GET /bff/v1/projects/prj_.../documents`. */
function concreteApi(expectation, captured) {
  return `${expectation.method} ${API_PREFIX}${fill(expectation.path, captured)}`;
}

/** `GET /bff/v1/findings/fnd_01.../decisions` -> `GET /bff/v1/findings/{id}/decisions`. */
function shapeOf(call) {
  return call.replace(new RegExp(`[a-z]{3,4}_${ID}`, 'g'), '{id}');
}

const failures = [];
const records = [];
const captured = {};

function fail(route, message) {
  failures.push(`${route}: ${message}`);
}

const PHASE = args.phase;
const REPOSITORY_ROOT = resolve(HERE, '..', '..', '..', '..');
const STAMP = new Date().toISOString().replace(/[:.]/g, '-');

// ---- the write half ----------------------------------------------------------------
let write = null;
if (PHASE === 'read') {
  console.log('phase: read only -- the write half was NOT run.');
} else if (manifest.write === undefined) {
  // A manifest with no write section is a manifest that cannot catch `D-5`. That is a
  // finding about this journey, not a quiet omission.
  failures.push(
    'write: this manifest declares no `write` section, so the journey makes no POST at ' +
      'all -- which is exactly what D-30 says the read half cannot catch',
  );
} else {
  console.log(`write half: ${manifest.write.steps.length} step(s), fixture ${manifest.write.fixture}\n`);
  write = await runWritePhase({
    origin: ORIGIN,
    manifest,
    repositoryRoot: REPOSITORY_ROOT,
    stamp: STAMP,
  });
  failures.push(...write.failures);
  if (write.stopped !== null) {
    failures.push(
      `write: the write half stopped at '${write.stopped}'; ` +
        `${write.records.length} of ${manifest.write.steps.length} step(s) were checked, ` +
        'and an unfinished write half is not a pass',
    );
  }
  console.log('');
}

// ---- the read walk -------------------------------------------------------------------
if (PHASE === 'write') {
  console.log('phase: write only -- the read walk was NOT run.');
}
for (const route of PHASE === 'write' ? [] : manifest.routes) {
  const url = ORIGIN + fill(route.path, captured);

  const record = await withColdBrowser(async (page) => {
    await page.goto(url);
    const landedOn = await page.evaluate('document.location.pathname');
    const title = await page.evaluate('document.title');
    const bodyText = await page.evaluate(
      "document.body ? document.body.innerText.replace(/\\n{3,}/g, '\\n\\n') : ''",
    );
    const links = await page.evaluate(
      "Array.from(document.querySelectorAll('a')).map((a) => a.getAttribute('href'))",
    );
    return {
      name: route.name,
      url,
      landedOn,
      title,
      bodyText,
      links,
      exchanges: page.exchanges(),
      consoleErrors: page.consoleErrors(),
      pageErrors: page.pageErrors(),
    };
  });

  // ---- the document itself, redirects included -------------------------------------
  // `/` is a redirect, so "the document" is a chain and not one response. Every hop is
  // kept with its own status and `location`: a 200 reached through a 307 and a 200 served
  // directly are different facts, and collapsing them is how a journey stops being
  // evidence.
  // Only documents fetched over HTTP. The review screen's PDF pane opens a `blob:` URL
  // and Chrome's built-in viewer at `chrome-extension://...`, both of which the protocol
  // reports as documents; treating either as the landing page would mean the route's
  // verdict came from the viewer rather than from the application.
  const documents = record.exchanges.filter(
    (e) => e.resourceType === 'Document' && /^https?:/.test(e.url),
  );
  record.documentChain = documents.map((e) => ({
    url: e.url,
    status: e.status,
    redirectedTo: e.redirectedTo ?? null,
    location: e.responseHeaders?.location ?? null,
  }));
  const landed = documents[documents.length - 1];
  record.documentStatus = landed?.status ?? null;
  if (record.documentStatus !== 200) {
    fail(
      route.name,
      `the document answered ${record.documentStatus} at ${landed?.url ?? url} ` +
        `(chain: ${record.documentChain.map((h) => `${h.status} ${h.url}`).join(' -> ') || 'none'})`,
    );
  }

  // ---- a declared redirect actually redirected ------------------------------------
  if (route.redirects_to && record.landedOn !== route.redirects_to) {
    fail(
      route.name,
      `declares it redirects to ${route.redirects_to} but the browser landed on ${record.landedOn}`,
    );
  }

  // ---- the page rendered something -----------------------------------------------
  if (!record.bodyText || record.bodyText.trim().length === 0) {
    fail(route.name, 'rendered an empty body');
  }

  // ---- an uncaught exception is a red, a console message is a note -----------------
  if (record.pageErrors.length > 0) {
    fail(route.name, `threw ${record.pageErrors.length} uncaught exception(s): ${record.pageErrors[0]}`);
  }

  // ---- T-6: the browser holds no credential ---------------------------------------
  const credentialled = record.exchanges.filter((e) => e.requestCarriedAuthorization);
  record.requestsCarryingAuthorization = credentialled.map((e) => `${e.method} ${e.url}`);
  if (credentialled.length > 0) {
    fail(
      route.name,
      `${credentialled.length} browser request(s) carried an Authorization header; ` +
        `T-6 puts the credential in the BFF, server-side: ${record.requestsCarryingAuthorization.join(', ')}`,
    );
  }

  // ---- the declared API calls were made -------------------------------------------
  const observed = record.exchanges
    .filter((e) => new URL(e.url).pathname.startsWith(API_PREFIX))
    .map((e) => `${e.method} ${new URL(e.url).pathname}`);
  record.observedApi = [...new Set(observed)];

  const required = (route.expects_api ?? []).map((e) => concreteApi(e, captured));
  // An optional call may name an identifier this walk never captured -- the review screen
  // opens a *finding*, and no earlier route hands out a finding uid. Optional calls are
  // therefore matched by shape, with every identifier segment collapsed to `{id}`.
  const optionalShapes = (route.optional_api ?? []).map(
    (e) => `${e.method} ${API_PREFIX}${e.path}`.replace(/\{[a-z_]+\}/g, '{id}'),
  );
  record.requiredApi = required;
  record.optionalApi = optionalShapes;
  for (const expectation of required) {
    if (!record.observedApi.includes(expectation)) {
      fail(
        route.name,
        `declares ${expectation} but the browser did not make it. ` +
          `It made: ${record.observedApi.join(' | ') || '(no API call at all)'}`,
      );
    }
  }

  // Undeclared traffic on the seam is drift in the other direction: the app grew a call
  // the written-down journey does not know about. The manifest is the claim, so this
  // reddens rather than being logged and forgotten.
  const declared = new Set(required);
  const undeclaredTemplated = record.observedApi.filter(
    (call) => !declared.has(call) && !optionalShapes.includes(shapeOf(call)),
  );
  record.undeclaredApi = undeclaredTemplated;
  if (undeclaredTemplated.length > 0) {
    fail(
      route.name,
      `made ${undeclaredTemplated.length} API call(s) no route in the manifest declares: ` +
        undeclaredTemplated.join(' | '),
    );
  }

  // ---- follow the app's own link to the next identifier ----------------------------
  if (route.follow) {
    const pattern = new RegExp(route.follow.href_pattern.replaceAll('%ID%', ID));
    const hit = (record.links ?? [])
      .filter((href) => typeof href === 'string')
      .map((href) => pattern.exec(href))
      .find((m) => m !== null);
    if (hit === undefined) {
      fail(
        route.name,
        `rendered no link matching ${route.follow.href_pattern} so the journey cannot ` +
          `reach ${route.follow.capture}. Links offered: ${(record.links ?? []).join(' | ') || '(none)'}`,
      );
      record.captured = null;
    } else {
      captured[route.follow.capture] = hit[1];
      record.captured = { [route.follow.capture]: hit[1] };
    }
  }

  records.push(record);
  const verdict = failures.some((f) => f.startsWith(`${route.name}:`)) ? 'RED ' : 'ok  ';
  console.log(
    `${verdict}${route.name.padEnd(10)} ${String(record.documentStatus).padEnd(4)} ` +
      `api=${record.observedApi.length} auth=${credentialled.length} ` +
      `console=${record.consoleErrors.length} ${record.captured ? JSON.stringify(record.captured) : ''}`,
  );

  // A route that could not capture the identifier the next route needs makes every
  // route after it meaningless rather than red. Stop and say so.
  if (route.follow && record.captured === null) {
    console.error(
      `\ne2e:pc01: stopping at '${route.name}' -- the walk cannot continue without ` +
        `${route.follow.capture}. The routes after it were NOT checked.`,
    );
    break;
  }
}

mkdirSync(OUT_DIR, { recursive: true });
const envelopePath = join(OUT_DIR, 'journey.json');
writeFileSync(
  envelopePath,
  JSON.stringify(
    {
      origin: ORIGIN,
      manifest: MANIFEST_PATH,
      phase: PHASE,
      startedAt: new Date().toISOString(),
      write:
        write === null
          ? { ran: false, why: PHASE === 'read' ? 'phase: read' : 'no write section' }
          : {
              ran: true,
              fixture: write.fixture,
              stepsChecked: write.records.length,
              stepsDeclared: manifest.write.steps.length,
              stoppedAt: write.stopped,
              captured: write.captured,
              steps: write.records,
            },
      captured,
      routesChecked: records.length,
      routesDeclared: manifest.routes.length,
      failures,
      records,
    },
    null,
    2,
  ),
);

console.log(`\nenvelope: ${envelopePath}`);
console.log(
  `write steps checked: ${write === null ? 'not run' : `${write.records.length}/${manifest.write.steps.length}`}`,
);
console.log(
  `routes checked: ${PHASE === 'write' ? 'not run' : `${records.length}/${manifest.routes.length}`}`,
);

if (PHASE !== 'write' && records.length < manifest.routes.length) {
  failures.push(
    `only ${records.length} of ${manifest.routes.length} routes were reached; ` +
      'an unfinished walk is not a pass',
  );
}

if (failures.length > 0) {
  console.error(`\ne2e:pc01 FAILED -- ${failures.length} finding(s):\n`);
  for (const f of failures) console.error(`  - ${f}`);
  console.error(`\nEvery request, status, header and body is in ${envelopePath}.`);
  process.exit(1);
}

console.log('e2e:pc01 OK');
