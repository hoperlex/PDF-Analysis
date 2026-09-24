/**
 * The PC-01 journey's **sign-in**: one session, obtained the way a reviewer obtains one.
 *
 * `D-92`. The journey was written for an application without authorization and this one
 * has had authorization since wave 34, so a walk of empty profiles reached route 2 of 15
 * and stopped. This file is the repair, and it is a design decision rather than a patch;
 * the argument is in `docs/program/W44-JOURNEY.md` and the part that constrains the code
 * is repeated here, because the next person to change this file will read the file.
 *
 * ## What was decided, in three sentences
 *
 * 1. **The session is obtained once, by driving the application's own sign-in screen** --
 *    a cold browser at `/login`, two fields typed through the browser's editing pipeline,
 *    the submit control pressed at its own coordinates. No `fetch`, no hand-built request,
 *    no direct `POST` to the exchange: if the screen a reviewer uses stops working, this
 *    stops working, which is the whole reason the journey exists.
 * 2. **The one value it yields -- the `HttpOnly` session cookie -- is handed to every
 *    later cold browser, identically.** It is a value the caller holds, not a jar shared
 *    between processes: see `cdp.mjs`'s `withColdBrowser` for why that is the difference
 *    between a session carried deliberately and state leaking between routes.
 * 3. **The credential comes from the environment and is in no file here.** There is no
 *    default, no fallback and no value in `manifest.json` -- the manifest names the FIELD
 *    each action fills and never what to fill it with, and
 *    `tests/e2e/test_pc01_journey_conformance.py` refuses a `session` action that carries
 *    a literal, so a credential cannot reach this repository by being typed into the
 *    declaration.
 *
 * ## Why not a fresh sign-in inside every route's browser
 *
 * It was the other candidate and it is worse in two measurable ways. It would put the
 * sign-in screen's own navigation and its `POST /bff/v1/session` inside **every** route's
 * recorded exchanges, so every route would then have to declare or filter traffic that has
 * nothing to do with it -- and `journey.mjs` reddens on undeclared traffic at the seam, on
 * purpose. And it would make each route's verdict depend on the sign-in screen working,
 * so a broken `/login` would redden fifteen routes and name none of them. One sign-in,
 * checked once and named as itself, fails in one place and says which place.
 *
 * ## Why not `--session <cookie>`
 *
 * That was the second shape named in `D-92`. It puts a live credential on a command line,
 * where it reaches the process table, the shell history and every transcript of the run,
 * and it moves the sign-in out of the instrument -- so the journey would stop checking the
 * screen a reviewer signs in on, which is one of the fifteen. `E2E_PC01_LOGIN` and
 * `E2E_PC01_PASSWORD` are read here instead, and the thing that crosses the process
 * boundary is a password typed into the application, not a session handed round it.
 *
 * ## Failing loudly
 *
 * A run that cannot sign in **stops**, names the sign-in as the reason, and exits
 * non-zero. It does not walk the routes that happen to work anonymously. `D-92` survived
 * nine waves precisely because a shorter walk looked like a walk.
 */

import { withColdBrowser } from './cdp.mjs';

/** The two environment names. Written once, quoted in the failure, checked by the gate. */
export const LOGIN_ENV = 'E2E_PC01_LOGIN';
export const PASSWORD_ENV = 'E2E_PC01_PASSWORD';

/**
 * The credential, from the environment, or a hard failure naming what is missing.
 *
 * There is deliberately no default -- not even the seeded `admin`/`password` that
 * `db/migrations/versions/20260922_0006_app_user.py` publishes in its own docstring. A
 * default would be the right credential for exactly one deployment and would teach every
 * later reader that the journey knows a password, which is the habit that puts one in a
 * file.
 */
export function credentialsFromEnvironment(env = process.env) {
  const login = env[LOGIN_ENV];
  const password = env[PASSWORD_ENV];
  const missing = [];
  if (typeof login !== 'string' || login.length === 0) missing.push(LOGIN_ENV);
  if (typeof password !== 'string' || password.length === 0) missing.push(PASSWORD_ENV);
  if (missing.length > 0) {
    const error = new Error(
      [
        `e2e:pc01: no credential. ${missing.join(' and ')} ${missing.length === 1 ? 'is' : 'are'} not set.`,
        '',
        `  ${LOGIN_ENV}=<login> ${PASSWORD_ENV}=<password> \\`,
        '    npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT',
        '',
        'The BFF answers 401 without a session (wave 34, by design), so a run without a',
        'credential walks two routes of fifteen and reports on thirteen it never opened.',
        'That is D-92 and it survived nine waves, so this is a hard failure and not a skip.',
        '',
        'The credential is never read from a file in this repository and has no default.',
      ].join('\n'),
    );
    error.isMissingCredential = true;
    throw error;
  }
  return { login, password };
}

/** The session mount, from the manifest, as a path: `/bff/v1/session`. */
function sessionPath(manifest) {
  return `${manifest.api_prefix}${manifest.session.api.path}`;
}

/**
 * Everything the sign-in browser sent, with the one body that holds a password removed.
 *
 * The form posts `login=...&password=...` and `cdp.mjs` records request bodies, because
 * `D-5` is a `POST` nobody kept. So the redaction is by ADDRESS -- the exchange mount this
 * manifest declares -- rather than by searching for the password's text: `/account/password`
 * is a real route of this application, and a journey that blanked every string containing
 * the word would corrupt its own evidence.
 */
function withoutCredentials(exchanges, mount) {
  return exchanges.map((exchange) => {
    let path = null;
    try {
      path = new URL(exchange.url).pathname;
    } catch {
      path = null;
    }
    if (path !== mount) return exchange;
    return {
      ...exchange,
      requestBody: exchange.requestBody === null ? null : '(redacted: the sign-in form post)',
      requestBodyTruncated: false,
    };
  });
}

/**
 * Drive the sign-in screen once and return the cookie every later browser is handed.
 *
 * Returns `{ ok, cookies, record, failures }`. It throws only when the credential is
 * absent, because that is an operator error with a fix in the message; everything the
 * APPLICATION got wrong comes back as a finding so the envelope is still written.
 */
export async function openSession({ origin, manifest }) {
  const spec = manifest.session;
  const failures = [];
  if (spec === undefined) {
    failures.push(
      'session: this manifest declares no `session` section, so the journey cannot sign ' +
        'in -- and the BFF answers 401 without a session. That is D-92.',
    );
    return { ok: false, cookies: [], record: null, failures };
  }

  const { login, password } = credentialsFromEnvironment();
  const values = { login, password };
  const mount = sessionPath(manifest);

  const record = {
    at: spec.at,
    url: origin + spec.at,
    cookie: spec.cookie,
    actions: [],
    landedOn: null,
    refusal: null,
    // Presence and attributes, never the value. The same rule `cdp.mjs` applies to
    // `Authorization`: what is evidence is that a session exists and what it is protected
    // by, not what it says.
    cookieObtained: null,
    exchanges: [],
    consoleErrors: [],
    pageErrors: [],
    startedWith: null,
  };

  let cookie = null;
  try {
    await withColdBrowser(async (page) => {
      record.startedWith = page.startedWith();
      await page.goto(record.url);
      record.landedOnBefore = await page.location();

      for (const action of spec.actions) {
        const entry = { do: action.do, selector: action.selector, text: action.text ?? null };
        record.actions.push(entry);
        if (action.do === 'fill') {
          const value = values[action.from];
          if (typeof value !== 'string') {
            throw new Error(
              `session: action fills '${action.from}', which is not one of the two the ` +
                'environment supplies (login, password)',
            );
          }
          entry.from = action.from;
          // The value is not recorded, here or anywhere. `page.fill` reads the control
          // back and throws when the application did not take the keystrokes, so "it was
          // typed" is still checked -- by the browser, not by an echo in a file.
          entry.value = '(never recorded)';
          await page.fill(action.selector, value, { text: action.text ?? null });
        } else if (action.do === 'click') {
          entry.result = await page.click(action.selector, { text: action.text ?? null });
        } else {
          throw new Error(
            `session: unknown action '${action.do}'; the sign-in screen is a form and ` +
              'this half knows fill and click',
          );
        }
      }

      await page.settle();

      // The application's own answer to "did this work": the address it sends a signed-in
      // browser to. Not the cookie -- a cookie is set on a refusal too if anything ever
      // goes wrong in the exchange, and the landing is what a reviewer sees.
      const waited = await page.waitFor(
        `(() => (document.location.pathname === ${JSON.stringify(spec.lands_on)}
           ? document.location.pathname : null))()`,
        { boundMs: spec.bound_ms, what: `the address to become ${spec.lands_on}` },
      );
      record.waitedMs = waited.waitedMs;
      record.boundMs = waited.boundMs;
      record.readings = waited.readings;
      record.landedOn = await page.location();

      // The refusal the screen renders, by its own marker attribute. It is read whether or
      // not the landing arrived, because "it refused and said why" and "nothing happened"
      // are different findings and a reader needs to be told which.
      record.refusal = await page.evaluate(`(() => {
        const el = document.querySelector('[data-sign-in-refusal]');
        return el === null ? null : {
          value: el.getAttribute('data-sign-in-refusal'),
          text: (el.innerText ?? '').trim().slice(0, 300),
        };
      })()`);

      if (!waited.ok) {
        failures.push(
          `session: after ${waited.waitedMs} ms (bound ${waited.boundMs} ms) the browser ` +
            `was at ${JSON.stringify(record.landedOn)} and not at ${spec.lands_on}` +
            (record.refusal === null
              ? '. The screen rendered no refusal either, so the exchange neither ' +
                'accepted nor refused.'
              : `. The screen refused with '${record.refusal.value}': ${JSON.stringify(record.refusal.text)}`),
        );
      } else if (record.refusal !== null) {
        failures.push(
          `session: the browser reached ${spec.lands_on} and the screen ALSO rendered the ` +
            `refusal '${record.refusal.value}', which are two different answers to one ` +
            'attempt',
        );
      }

      cookie = await page.cookieFor(spec.cookie);
      if (cookie === null) {
        failures.push(
          `session: the exchange set no '${spec.cookie}' cookie, so there is nothing to ` +
            'carry into the walk. Cookies the profile holds: ' +
            `${(await page.cookieNames()).join(', ') || '(none)'}`,
        );
      } else {
        record.cookieObtained = {
          name: cookie.name,
          httpOnly: cookie.httpOnly === true,
          sameSite: cookie.sameSite ?? null,
          path: cookie.path ?? null,
          secure: cookie.secure === true,
          expiresInS:
            typeof cookie.expires === 'number' && cookie.expires > 0
              ? Math.round(cookie.expires - Date.now() / 1000)
              : null,
        };
        // The application says the browser cannot read it. That is a claim about this
        // exchange and it is cheap to check here, where the browser is already open.
        if (cookie.httpOnly !== true) {
          failures.push(
            `session: '${spec.cookie}' came back WITHOUT HttpOnly, so page script can read ` +
              'the session identifier. `app/bff/session/store.ts` says it is HttpOnly.',
          );
        }
      }

      record.exchanges = withoutCredentials(page.exchanges(), mount);
      record.consoleErrors = page.consoleErrors();
      record.pageErrors = page.pageErrors();

      // The exchange's own status, from the browser's record rather than from the screen.
      const seen = record.exchanges.filter((e) => {
        try {
          return new URL(e.url).pathname === mount && e.method === spec.api.method;
        } catch {
          return false;
        }
      });
      record.api = seen.map((e) => `${e.method} ${mount} -> ${e.status}`);
      if (seen.length === 0) {
        failures.push(
          `session: the browser never made ${spec.api.method} ${mount}; pressing the ` +
            'control sent nothing at all',
        );
      } else if (seen[seen.length - 1].status !== spec.api.expect_status) {
        failures.push(
          `session: ${spec.api.method} ${mount} answered ${seen[seen.length - 1].status} ` +
            `and this manifest declares ${spec.api.expect_status}`,
        );
      }

      for (const exchange of record.exchanges) {
        if (exchange.requestCarriedAuthorization) {
          failures.push(
            `session: the browser presented an Authorization header on ` +
              `${exchange.method} ${exchange.url}; T-6 puts the credential in the BFF`,
          );
        }
      }

      if (record.pageErrors.length > 0) {
        failures.push(
          `session: the sign-in screen threw ${record.pageErrors.length} uncaught ` +
            `exception(s): ${record.pageErrors[0]}`,
        );
      }
    });
  } catch (error) {
    if (error.isMissingCredential) throw error;
    failures.push(`session: the sign-in screen could not be driven: ${error.message}`);
    record.drivingError = error.message;
  }

  const ok = failures.length === 0 && cookie !== null;
  return {
    ok,
    // One declaration, built once, handed unchanged to every cold browser after this.
    cookies:
      cookie === null
        ? []
        : [
            {
              name: cookie.name,
              value: cookie.value,
              url: origin,
              path: cookie.path ?? '/',
              httpOnly: cookie.httpOnly === true,
              sameSite: cookie.sameSite ?? 'Strict',
            },
          ],
    record,
    failures,
  };
}
