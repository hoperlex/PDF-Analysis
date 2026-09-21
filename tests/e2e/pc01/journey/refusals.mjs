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
 * **Why the expectations are written here and not in `manifest.json`.** `manifest.json`'s
 * `write` section declares steps that *succeed* — it has `forbids_rendered` and no
 * `requires_rendered`, and its gate-time guard in
 * `tests/e2e/test_pc01_journey_conformance.py` reads it on that understanding. Extending
 * that format to carry refusals is a real piece of work with a real guard change behind
 * it, and this session's deliverable is the measurement. The cost is stated rather than
 * hidden: **the table below is not read by `make gate`**, so a renamed marker turns this
 * script red only when someone runs it. That is the same residue `W21-E2E` stated for the
 * read walk, one notch worse, and it is the next session's to close.
 *
 * Run:
 *
 *   node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500
 *
 * Exit 0 means all six behaved as declared. Non-zero prints every finding and names the
 * envelope file. No dependency: `cdp.mjs`, committed, drives the browser.
 */

import { mkdirSync, writeFileSync, existsSync, statSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..', '..');

/**
 * The six fixtures, and what each one's refusal is claimed to be.
 *
 * `rule` is the envelope rule id from `fixtures/synthetic/ar/README.md`. `refused_by` is
 * the claim this session set out to check, taken from `W21-CERT`'s `curl` table plus
 * `precheckUploadFile`'s two browser-visible rules. `must_say` is the substring the screen
 * has to render for the refusal to be *actionable* rather than merely present.
 */
const CASES = [
  {
    fixture: 'not_a_pdf.txt',
    rule: 'ENV-PDF',
    refused_by: 'client',
    precheck_problem: 'not_pdf',
    must_say: ['not a PDF', 'Nothing was sent'],
  },
  {
    fixture: 'companion_archive.zip',
    rule: 'ENV-PDF',
    refused_by: 'client',
    precheck_problem: 'not_pdf',
    must_say: ['not a PDF', 'Nothing was sent'],
  },
  {
    fixture: 'oversize.pdf',
    rule: 'ENV-SIZE',
    refused_by: 'client',
    precheck_problem: 'too_large',
    must_say: ['25 MiB', 'Nothing was sent'],
  },
  {
    fixture: 'encrypted.pdf',
    rule: 'ENV-ENCRYPTED',
    refused_by: 'server',
    status: 422,
    error_code: 'validation_failed',
    constraint: 'not_encrypted',
    failure_kind: 'unsupported_input',
    must_say: ['outside the accepted envelope', 'not_encrypted'],
  },
  {
    fixture: 'image_only.pdf',
    rule: 'ENV-TEXT',
    refused_by: 'server',
    status: 422,
    error_code: 'validation_failed',
    constraint: 'every_page_has_extractable_text',
    failure_kind: 'unsupported_input',
    must_say: ['outside the accepted envelope', 'every_page_has_extractable_text'],
  },
  {
    fixture: 'too_many_pages.pdf',
    rule: 'ENV-PAGES',
    refused_by: 'server',
    status: 422,
    error_code: 'validation_failed',
    constraint: '1 <= page_count <= 30',
    failure_kind: 'unsupported_input',
    must_say: ['outside the accepted envelope', 'page_count'],
  },
];

/** The classifications that mean "the client could not say what went wrong". */
const GENERIC_KINDS = new Set(['server_error', 'unknown', 'unrecognized', 'transport']);

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
  const file = resolve(REPO, 'fixtures/synthetic/ar/negative', testCase.fixture);
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
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');

  const started = Date.now();
  const seeded = await seedProject(origin, stamp);
  console.log(`seeded project ${seeded.projectUid} ("${seeded.name}")`);

  const cases = only === null ? CASES : CASES.filter((c) => c.fixture === only);
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
