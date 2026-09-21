/**
 * The six negative fixtures, driven **through the browser**, at the app's own upload
 * control.
 *
 * **Why this file exists.** `PA-01` criterion 9 says *"each of the five refusals answers
 * with its own typed code through HTTP"*. `W21-CERT` and `W24-CERT2` drove it with `curl`
 * and said why: the instrument the criterion names is HTTP, and the client-side pre-check
 * refuses three of these files before a browser could send them. Both were right about the
 * criterion. The consequence is that **nobody had ever seen what the screen shows** — and
 * `W15-RUN`, `W19-RUN` and `D-16` are all findings that only appeared when a person, or a
 * browser standing in for one, looked at a screen that every server-side measurement said
 * was fine.
 *
 * So this is not a second measurement of the API. The API's answer is frozen input here.
 * What is measured is the **rendered text**: whether a person who drops the wrong file in
 * is told something true and actionable, or is told `server_error` for a fault the system
 * understands precisely.
 *
 * **What it asserts, per fixture:**
 *
 *   1. *where* the refusal happened — the client pre-check, or the server — and that it is
 *      the place this file declares, because "the browser never sent it" and "the server
 *      refused it" are different products and a screen that confuses them is a screen that
 *      lies about where the limit is;
 *   2. that the upload control's own state agrees — a pre-check refusal **disables**
 *      `Upload`, a server refusal does not;
 *   3. the typed code and the `constraint` classifier, read off the envelope the browser
 *      itself received, not off a parallel `curl`;
 *   4. that the screen rendered the **specific** refusal and not the generic one. A
 *      failure classified `server_error`, `unknown`, `unrecognized` or `transport` for a
 *      fault the catalog names is a finding, whatever the status was;
 *   5. that the rendered text actually contains the rule the file broke, in words —
 *      not merely that a panel appeared;
 *   6. that nothing was published: the address never becomes a version's address, and no
 *      `POST` answered 2xx.
 *
 * **Read the rendered body, never the status** (`D-28`): `/projects/<anything>` answers
 * 200 and renders an error state. Every verdict below is taken from `innerText` and from
 * the marker attributes `web/src` defines, and the status is evidence beside them.
 *
 * **Where the expectations live, since `W28-GUARD`.** They were written in this file's own
 * source, and this file stated the cost: `make gate` could not read them, so a renamed
 * marker turned the script red only when someone ran it. **They are now
 * `manifest.json`'s `refusals` section**, read below, and
 * `tests/e2e/test_pc01_journey_conformance.py` checks them at gate time against the route
 * tree, the contract and `web/src` — with no browser, no origin and no stack.
 *
 * What the gate still cannot see is behaviour: that the envelope really carries that
 * `constraint`, that the screen really renders it, that `Upload` really goes unpressable,
 * that nothing was published. **That is what this script is for**, and the split is named
 * in the manifest's own `$comment` rather than quietly claimed by the guard.
 *
 * Run:
 *
 *   node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500
 *
 * Exit 0 means all six behaved as declared. Non-zero prints every finding and names the
 * envelope file. No dependency: `cdp.mjs`, committed, drives the browser.
 */

import { mkdirSync, writeFileSync, readFileSync, existsSync, statSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..', '..');

/**
 * The declaration, read from `manifest.json`. `W28-GUARD`.
 *
 * `rule` is the envelope rule id from `fixtures/synthetic/ar/README.md`. `refused_by` is
 * the claim `W27-REFUSE` set out to check, taken from `W21-CERT`'s `curl` table plus
 * `precheckUploadFile`'s two browser-visible rules. `must_say` is the substring the screen
 * has to render for the refusal to be *actionable* rather than merely present, and the
 * manifest splits it in two: `expects_rendered` is the application's own words, which the
 * gate checks against `web/src`, and `expects_rendered_from_envelope` is what the SERVER
 * supplies, which only a live drive can see. This script needs both, in one list.
 *
 * The rest of this file is unchanged, so `--cases` files written against the old shape --
 * `fixtures/redden-refusals.json` among them -- still declare exactly what they did.
 */
const REFUSALS = JSON.parse(readFileSync(resolve(HERE, 'manifest.json'), 'utf8')).refusals;

function manifestCases(section) {
  if (section === undefined || !Array.isArray(section.cases) || section.cases.length === 0) {
    throw new Error(
      'manifest.json declares no `refusals` section. It is where the six live since ' +
        'W28-GUARD, and it is what tests/e2e/test_pc01_journey_conformance.py checks.',
    );
  }
  return section.cases.map((declared) => ({
    ...declared,
    // the manifest says `expect_status`, as its write half does; this file says `status`
    status: declared.expect_status,
    must_say: [
      ...(declared.expects_rendered ?? []),
      ...(declared.expects_rendered_from_envelope ?? []),
    ],
  }));
}

const CASES = manifestCases(REFUSALS);

/** The classifications that mean "the client could not say what went wrong". Declared. */
const GENERIC_KINDS_DECLARED = REFUSALS?.generic_kinds ?? null;

/** Where the negative fixtures live, declared once and read by both checkers. */
const FIXTURE_DIR = REFUSALS?.fixture_dir ?? 'fixtures/synthetic/ar/negative';

/**
 * Proving it can fail.
 *
 * A refusal drive that cannot go red is a screenshot with an exit code. `--cases <file>`
 * replaces the table above with a declaration read from disk, and
 * `fixtures/redden-refusals.json` beside this file declares things that are not true of
 * this application: a client-side refusal claimed to happen at the server, a constraint
 * the envelope does not carry, and a sentence no screen renders. Expected: non-zero, with
 * one finding per wrong claim.
 *
 * That fixture is not read by anything else, so its deliberate wrongs redden nothing.
 */
function casesFrom(path) {
  const declared = JSON.parse(readFileSync(path, 'utf8'));
  if (!Array.isArray(declared) || declared.length === 0) {
    throw new Error(`${path} must hold a non-empty array of case declarations`);
  }
  return declared;
}

/**
 * The classifications that mean "the client could not say what went wrong".
 *
 * Declared in `manifest.json` since `W28-GUARD`, so the gate can hold the six cases to
 * not declaring one of them -- which is the cheapest way to make a failing drive pass.
 */
const GENERIC_KINDS = new Set(GENERIC_KINDS_DECLARED ?? []);
if (GENERIC_KINDS.size === 0) {
  throw new Error('manifest.json declares no `refusals.generic_kinds`; check 4 would be vacuous.');
}

const ID = '[0-9A-HJKMNP-TV-Z]{26}';
const API_PREFIX = '/bff/v1';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 || i === process.argv.length - 1 ? fallback : process.argv[i + 1];
}

function pathOf(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

function decodeJson(text) {
  if (typeof text !== 'string' || text.length === 0) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

/** Everything the browser sent at the BFF seam during one drive. */
function apiExchanges(page) {
  return page
    .exchanges()
    .filter((e) => pathOf(e.url).startsWith(API_PREFIX))
    .map((e) => ({
      method: e.method,
      path: pathOf(e.url),
      status: e.status,
      statusText: e.statusText ?? null,
      correlationId: e.responseHeaders?.['x-correlation-id'] ?? null,
      requestContentType: e.requestHeaders?.['content-type'] ?? null,
      carriedAuthorization: e.requestCarriedAuthorization ?? null,
      responseBody: e.responseBody ?? null,
    }));
}

/** Read the panel `web/src` renders for a refusal, by its own marker attributes. */
const READ_PANEL = `(() => {
  const pick = (sel, attr) => {
    const el = document.querySelector(sel);
    return el === null ? null : {
      marker: el.getAttribute(attr),
      text: (el.innerText ?? '').trim(),
      panel: (el.closest('.am-state')?.innerText ?? '').trim(),
      role: el.closest('[role]')?.getAttribute('role') ?? null,
      tone: (el.closest('.am-state')?.className ?? null),
    };
  };
  const submit = Array.from(document.querySelectorAll('form button[type="submit"]'))
    .find((b) => (b.innerText ?? '').trim() === 'Upload') ?? null;
  return {
    precheck: pick('[data-precheck-problem]', 'data-precheck-problem'),
    uploadFailure: pick('[data-upload-failure]', 'data-upload-failure'),
    alertText: (document.querySelector('[role="alert"]')?.innerText ?? '').trim() || null,
    submitDisabled: submit === null ? null : submit.disabled === true,
    chosen: (Array.from(document.querySelectorAll('p')).map((p) => (p.innerText ?? '').trim())
      .find((t) => t.startsWith('Chosen: ')) ?? null),
    retryOffered: Array.from(document.querySelectorAll('button'))
      .some((b) => (b.innerText ?? '').trim().startsWith('Retry')),
    body: document.body ? document.body.innerText.replace(/\\n{3,}/g, '\\n\\n') : '',
  };
})()`;

/** Create one project through the app's own control, so no existing data is disturbed. */
async function seedProject(origin, stamp) {
  return await withColdBrowser(async (page) => {
    await page.goto(`${origin}/projects`);
    const name = `W27-REFUSE ${stamp}`;
    await page.fill('#new-project-name', name);
    await page.click('form button[type="submit"]', { text: 'Create' });
    await page.settle();
    const waited = await page.waitFor(
      `(() => {
        const el = document.querySelector('[data-created-project]');
        return el === null ? null : el.getAttribute('data-created-project');
      })()`,
      { boundMs: 30000, what: 'the screen to state the project it created' },
    );
    if (!waited.ok) {
      throw new Error(
        `the project screen never stated a created project within ${waited.boundMs} ms; ` +
          `readings: ${waited.readings.map((r) => `${r.atMs}ms ${r.seen}`).join(' | ')}`,
      );
    }
    const uid = String(waited.value);
    if (!new RegExp(`^prj_${ID}$`).test(uid)) {
      throw new Error(`the screen stated ${JSON.stringify(uid)}, which is not a project uid`);
    }
    return { projectUid: uid, name };
  });
}

/** One fixture, one cold browser, at the app's own upload control. */
async function drive(origin, projectUid, testCase, stamp) {
  const file = resolve(REPO, FIXTURE_DIR, testCase.fixture);
  if (!existsSync(file)) {
    return { fixture: testCase.fixture, drivingError: `${file} is not on disk`, findings: [`${testCase.fixture}: the fixture is not on disk at ${file}`] };
  }
  const bytesOnDisk = statSync(file).size;

  const record = {
    fixture: testCase.fixture,
    rule: testCase.rule,
    declared: testCase,
    bytesOnDisk,
    at: `/projects/${projectUid}`,
    attached: null,
    afterChoosing: null,
    clickedUpload: false,
    afterUpload: null,
    finalLocation: null,
    api: [],
    consoleErrors: [],
    pageErrors: [],
    timingsMs: {},
    findings: [],
  };
  const fail = (m) => record.findings.push(`${testCase.fixture}: ${m}`);
  const t0 = Date.now();

  try {
    await withColdBrowser(async (page) => {
      await page.goto(`${origin}/projects/${projectUid}`);
      record.landedOn = await page.location();

      // ---- the user chooses the file -------------------------------------------
      record.attached = await page.attachFile('#upload-file', file);
      if (record.attached.size !== bytesOnDisk) {
        fail(`the browser attached ${record.attached.size} bytes but the fixture is ${bytesOnDisk} on disk`);
      }
      await page.fill('#upload-title', `W27-REFUSE ${testCase.fixture} ${stamp}`);
      record.timingsMs.settleAfterChoosing = await page.settle();
      record.afterChoosing = await page.evaluate(READ_PANEL);

      const refusedByClient = record.afterChoosing.precheck !== null;
      record.refusedBy = refusedByClient ? 'client' : null;

      // ---- the user presses Upload, if the app still lets them ------------------
      if (!refusedByClient) {
        record.clickedUpload = true;
        await page.click('form button[type="submit"]', { text: 'Upload' });
        // Either the screen renders a failure, or it navigates to the published version.
        const waited = await page.waitFor(
          `(() => {
            if (document.querySelector('[data-upload-failure]') !== null) return 'failure';
            if (/^\\/projects\\/prj_${ID}\\/versions\\/ver_${ID}$/.test(document.location.pathname)) return 'published';
            return null;
          })()`,
          { boundMs: 60000, pollMs: 250, what: 'the upload to be refused or to publish a version' },
        );
        record.uploadOutcome = { ...waited, readings: waited.readings };
        record.timingsMs.settleAfterUpload = await page.settle();
        if (!waited.ok) {
          fail(
            `after ${waited.waitedMs} ms (bound ${waited.boundMs} ms) the screen neither ` +
              `refused the upload nor published a version. It said nothing a person could act on.`,
          );
        } else if (waited.value === 'published') {
          fail('the upload PUBLISHED A VERSION. The envelope rule this fixture breaks was not enforced.');
        }
        record.refusedBy = 'server';
      }

      record.afterUpload = await page.evaluate(READ_PANEL);
      record.finalLocation = await page.location();
      record.api = apiExchanges(page);
      record.consoleErrors = page.consoleErrors();
      record.pageErrors = page.pageErrors();
    });
  } catch (error) {
    record.drivingError = error.message;
    fail(`could not be driven: ${error.message}`);
  }

  record.timingsMs.total = Date.now() - t0;

  // ---- assertions over what was recorded ---------------------------------------
  const seen = record.afterUpload ?? record.afterChoosing;
  if (seen === null) return record;

  // 1. where the refusal happened
  if (record.refusedBy !== testCase.refused_by) {
    fail(
      `this file declares the refusal happens at the ${testCase.refused_by}, and the drive ` +
        `shows it at the ${record.refusedBy}.`,
    );
  }

  const uploads = record.api.filter((e) => e.method === 'POST' && /\/documents$/.test(e.path));
  record.uploadCalls = uploads.map((e) => `${e.method} ${e.path} -> ${e.status}`);

  if (testCase.refused_by === 'client') {
    // 2. the control's own state
    if (record.afterChoosing.submitDisabled !== true) {
      fail('the pre-check refused the file but Upload is still pressable.');
    }
    if (uploads.length !== 0) {
      fail(
        `the screen says "Nothing was sent" but the browser sent ${uploads.length} upload ` +
          `request(s): ${record.uploadCalls.join(', ')}`,
      );
    }
    // 3. the typed problem
    const problem = record.afterChoosing.precheck?.marker ?? null;
    if (problem !== testCase.precheck_problem) {
      fail(`the pre-check reported '${problem}' and this file declares '${testCase.precheck_problem}'.`);
    }
  } else {
    if (record.afterChoosing.precheck !== null) {
      fail(
        `the pre-check refused this file client-side ('${record.afterChoosing.precheck.marker}'), ` +
          `so the server's typed refusal never reaches a person.`,
      );
    }
    if (uploads.length !== 1) {
      fail(`the browser made ${uploads.length} upload request(s); exactly one was expected.`);
    }
    const call = uploads[0] ?? null;
    if (call !== null) {
      if (call.status !== testCase.status) {
        fail(`uploadDocument answered ${call.status} and this file declares ${testCase.status}.`);
      }
      const envelope = decodeJson(call.responseBody);
      if (envelope === undefined) {
        fail(`uploadDocument's body did not decode as JSON: ${JSON.stringify((call.responseBody ?? '').slice(0, 200))}`);
      } else {
        record.envelope = envelope;
        if (envelope.error_code !== testCase.error_code) {
          fail(`the envelope carried error_code '${envelope.error_code}' and this file declares '${testCase.error_code}'.`);
        }
        const constraint = envelope.details?.constraint ?? null;
        if (constraint !== testCase.constraint) {
          fail(`the envelope carried details.constraint ${JSON.stringify(constraint)} and this file declares ${JSON.stringify(testCase.constraint)}.`);
        }
      }
      // 4. the screen's own classification
      const kind = record.afterUpload.uploadFailure?.marker ?? null;
      if (kind === null) {
        fail('the server refused the upload and the screen rendered no [data-upload-failure] at all.');
      } else if (GENERIC_KINDS.has(kind)) {
        fail(
          `the screen classified a refusal the catalog names precisely as '${kind}' — ` +
            `a generic failure for a fault the system understands.`,
        );
      } else if (kind !== testCase.failure_kind) {
        fail(`the screen classified it '${kind}' and this file declares '${testCase.failure_kind}'.`);
      }
      // A refusal no retry can fix must offer no retry.
      if (record.afterUpload.retryOffered) {
        fail('the screen offered a retry for a file no retry can make acceptable.');
      }
    }
  }

  // 5. the rendered words
  const rendered = seen.body ?? '';
  record.renderedPanel =
    (record.afterUpload?.uploadFailure?.panel ?? null) ??
    (record.afterChoosing?.precheck?.panel ?? null);
  for (const needle of testCase.must_say) {
    if (!rendered.includes(needle)) {
      fail(`the screen never rendered ${JSON.stringify(needle)}. What it rendered: ${JSON.stringify(rendered.slice(0, 600))}`);
    }
  }
  if ((record.renderedPanel ?? '').length === 0) {
    fail('no refusal panel was rendered at all.');
  }

  // 6. nothing was published, and no credential left the browser
  if (new RegExp(`^/projects/prj_${ID}/versions/ver_${ID}$`).test(record.finalLocation ?? '')) {
    fail(`the browser ended on ${record.finalLocation}, a published version's own address.`);
  }
  for (const call of record.api) {
    if (call.carriedAuthorization === true) {
      fail(`${call.method} ${call.path} carried an Authorization header from the browser (T-6).`);
    }
  }

  return record;
}

async function main() {
  const origin = arg('origin');
  if (origin === null) {
    console.error('--origin is required. There is no default: this drive writes real state.');
    process.exit(2);
  }
  const outDir = resolve(process.cwd(), arg('out', '.out'));
  mkdirSync(outDir, { recursive: true });
  const only = arg('only');
  const casesFile = arg('cases');
  const table = casesFile === null ? CASES : casesFrom(resolve(process.cwd(), casesFile));
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');

  const started = Date.now();
  if (casesFile !== null) console.log(`cases declared by ${casesFile} (not the built-in table)`);
  const seeded = await seedProject(origin, stamp);
  console.log(`seeded project ${seeded.projectUid} ("${seeded.name}")`);

  const cases = only === null ? table : table.filter((c) => c.fixture === only);
  const records = [];
  for (const testCase of cases) {
    process.stdout.write(`\n-- ${testCase.fixture} (${testCase.rule}) `);
    const record = await drive(origin, seeded.projectUid, testCase, stamp);
    records.push(record);
    console.log(`${record.findings.length === 0 ? 'as declared' : `${record.findings.length} FINDING(S)`} in ${record.timingsMs.total} ms`);
    console.log(`   refused by: ${record.refusedBy ?? '(nothing refused it)'}`);
    console.log(`   API:        ${(record.uploadCalls ?? []).join(', ') || '(no upload request)'}`);
    console.log(`   screen:     ${JSON.stringify((record.renderedPanel ?? '').replace(/\n/g, ' ⏎ '))}`);
    for (const finding of record.findings) console.log(`   ! ${finding}`);
  }

  const envelope = {
    origin,
    stamp,
    project: seeded,
    elapsedMs: Date.now() - started,
    records,
  };
  const out = join(outDir, 'refusals.json');
  writeFileSync(out, JSON.stringify(envelope, null, 2));

  const findings = records.flatMap((r) => r.findings);
  console.log(`\nenvelope: ${out}`);
  console.log(`${cases.length} fixture(s) driven, ${findings.length} finding(s), ${envelope.elapsedMs} ms`);
  process.exit(findings.length === 0 ? 0 : 1);
}

await main();
