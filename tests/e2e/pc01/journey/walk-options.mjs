/**
 * The read walk's options, as pure rules (`D-380`, lane J2).
 *
 * `journey.mjs` runs on import, so the rules a flag implies live here, where `walk-options.test.mjs` can
 * call them without a browser, a stand or a process exit.
 *
 * ## What each option is for
 *
 * The journey declares ONE width (the manifest's `viewport`, 780) and walks ONE state (dispatch open, a stand
 * that holds whatever the write half left). Three layout faults of 0.17.1 needed another width or another state
 * to show, and passed the walk:
 *
 *  * a phone width (the stage controls' select ended at 399 px at 390 px);
 *  * dispatch paused (the frame's end group ended at 471 px);
 *  * the stage catalog with a confirmed pair (the pairs table widened the page to 839 px).
 *
 * `--width` / `--height` change the read walk's viewport and the width assertion with it, `--paused` holds
 * dispatch paused around the read walk (`dispatch.mjs`), and `--state <name>` makes the walk require that the
 * routes which declare `read_state.<name>` are really in it, so a read of "the stage catalog with a pair" cannot
 * pass on a stand that holds no pair.
 */

/** A phone is 360 to 430 px wide, a wide screen is 1920; anything outside is a typo, not a width. */
export const MIN_DIMENSION = 240;
export const MAX_DIMENSION = 3840;

/** `--width 390` -> 390, or a hard stop: a viewport nobody meant must not quietly become the declared one. */
export function parseDimension(flag, text) {
  if (typeof text !== 'string' || !/^[0-9]{1,5}$/.test(text.trim())) {
    throw new Error(`${flag} must be a whole number of pixels (got ${JSON.stringify(text)})`);
  }
  const value = Number(text.trim());
  if (value < MIN_DIMENSION || value > MAX_DIMENSION) {
    throw new Error(`${flag} must be between ${MIN_DIMENSION} and ${MAX_DIMENSION} px (got ${value})`);
  }
  return value;
}

/**
 * The viewport the read walk lays routes out at, and that the width assertion holds them to.
 *
 * `declared` is the manifest's `viewport`. A flag overrides one of its two numbers; the other stays as declared.
 * `requested` says the numbers are not the manifest's, which the finding's wording and the envelope both carry.
 */
export function readViewport(declared, { width = null, height = null } = {}) {
  if (declared === undefined || declared === null) return null;
  const requested = width !== null || height !== null;
  return {
    width: width ?? declared.width,
    height: height ?? declared.height,
    requested,
  };
}

/** `{project: 'prj_X'}` -> `?project=prj_X`; an empty object -> `''`. Keys keep their declared order. */
export function queryString(entries) {
  const pairs = Object.entries(entries ?? {});
  if (pairs.length === 0) return '';
  return `?${pairs.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&')}`;
}

/**
 * A route's `query` made concrete: each value is a template over what earlier routes captured.
 * `fill` is the walk's own template filler (it throws on a name nothing captured), passed in so the
 * rule is not written twice.
 */
export function routeQuery(route, fill) {
  const out = {};
  for (const [key, template] of Object.entries(route.query ?? {})) out[key] = fill(template);
  return out;
}

/**
 * What the screen shows, condition by condition: `{ ok, seen }`, `seen` being how many nodes each condition found
 * (a condition may demand a pattern its text must match). The screen is in the state when every condition holds.
 * Always answers, so a finding can say what was there.
 */
export function stateProbeExpression(state) {
  const conditions = state.present ?? [];
  return `(() => {
    const conditions = ${JSON.stringify(conditions)};
    const seen = conditions.map((c) => {
      const pattern = c.text_matches === undefined ? null : new RegExp(c.text_matches);
      return Array.from(document.querySelectorAll(c.selector))
        .filter((el) => pattern === null || pattern.test((el.innerText ?? '').trim())).length;
    });
    const ok = conditions.every((c, i) => seen[i] >= (c.min_count ?? 1));
    return { ok, seen };
  })()`;
}

/**
 * The same, shaped for `Page.waitFor`, which stops at the first value that is not `null`/`false`/`''`: the probe
 * while the screen IS in the state, `null` while it is not.
 */
export function stateExpression(state) {
  return `(() => { const reading = ${stateProbeExpression(state)}; return reading.ok ? reading : null; })()`;
}

/** The state is reached when the wait ended on a reading, not on its bound. */
export function stateReached(waited) {
  return waited !== null && waited !== undefined && waited.ok === true;
}

/**
 * Why a route is not in the state the walk was asked to hold it in: one finding, with what the screen showed.
 * `waited` is the `waitFor` result, with the final `detail` (the probe once the wait gave up) attached by the caller.
 */
export function stateFindings(where, name, state, waited, bodyText) {
  if (stateReached(waited)) return [];
  const conditions = (state.present ?? [])
    .map((c) => `${c.selector}${c.text_matches === undefined ? '' : ` matching /${c.text_matches}/`}`)
    .join(' + ');
  const last = waited?.detail === undefined ? '(no reading)' : JSON.stringify(waited.detail);
  return [
    `${where}: this read asks for the state '${name}' and the screen did not reach it within ` +
      `${state.bound_ms} ms (${conditions}); last reading ${last}. A read of the wrong state is ` +
      `not a read of this one: it rendered ${JSON.stringify((bodyText ?? '').replace(/\s+/g, ' ').slice(0, 240))}`,
  ];
}

/**
 * While dispatch is paused, a screen that reads the pause state must SAY it is paused. The frame's strip
 * (`[data-pause-status]`) is drawn for a session the queue is open to, and such a screen asks
 * `getExecutionDispatch`; a screen that made that call and shows another word is not the state under test.
 */
export function pausedFindings(where, observedApi, marker) {
  const asked = observedApi.some((call) => /^GET \S*\/execution\/dispatch$/.test(call));
  if (!asked) return [];
  if (marker === 'paused') return [];
  return [
    `${where}: dispatch is paused for this read and the frame's strip reads ${JSON.stringify(marker)} ` +
      '(`[data-pause-status]`), not "paused": the walk is not in the state it was asked to hold',
  ];
}
