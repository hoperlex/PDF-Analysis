import assert from 'node:assert/strict';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

import {
  MAX_DIMENSION,
  MIN_DIMENSION,
  declaredRefusals,
  isDeclaredRefusal,
  parseDimension,
  pausedFindings,
  pickFollowed,
  queryString,
  readViewport,
  requiredReads,
  routeQuery,
  stateExpression,
  stateFindings,
  stateProbeExpression,
  stateReached,
  stateRouteQuery,
  stateView,
} from './walk-options.mjs';
import { widthFindings } from './width.mjs';

test('D-380: --width is a whole number of pixels in a plausible range, and anything else stops the run', () => {
  assert.equal(parseDimension('--width', '390'), 390);
  assert.equal(parseDimension('--width', ' 1280 '), 1280);
  for (const bad of ['', 'wide', '390px', '-390', '3.5', '0', String(MIN_DIMENSION - 1), String(MAX_DIMENSION + 1), undefined, null, '1e3']) {
    assert.throws(() => parseDimension('--width', bad), /--width/, String(bad));
  }
});

test('D-380: a flag overrides one number of the declared viewport and the other stays declared', () => {
  const declared = { width: 780, height: 900 };
  assert.deepEqual(readViewport(declared, {}), { width: 780, height: 900, requested: false });
  assert.deepEqual(readViewport(declared, { width: 390 }), { width: 390, height: 900, requested: true });
  assert.deepEqual(readViewport(declared, { width: 390, height: 844 }), { width: 390, height: 844, requested: true });
  assert.deepEqual(readViewport(declared, { height: 600 }), { width: 780, height: 600, requested: true });
  assert.equal(readViewport(undefined, { width: 390 }), null, 'no declared viewport and no way to hold a width: nothing to override');
});

test('D-380: the width assertion holds a route to the REQUESTED width and reports the overflow in pixels', () => {
  const phone = readViewport({ width: 780, height: 900 }, { width: 390, height: 844 });
  const wide = { scrollWidth: 471, clientWidth: 390, innerWidth: 390, offenders: [{ tag: 'div', className: 'bar', id: '', left: 0, right: 471, width: 471, text: 'Выдача приостановлена' }], offenderCount: 1 };
  const [finding] = widthFindings('queue', wide, phone);
  assert.match(finding, /^queue: the screen scrolls sideways at the requested width\./);
  assert.match(finding, /scrollWidth 471 > innerWidth 390/);
  assert.match(finding, /overflowing by 81 px/);
  assert.deepEqual(widthFindings('queue', { ...wide, scrollWidth: 390 }, phone), []);
  // A page laid out at another width than the one asked for is a finding of its own, not a comparison at a width nobody stated.
  assert.match(widthFindings('queue', { ...wide, innerWidth: 780, scrollWidth: 700 }, phone)[0], /laid out at 780 px and this run requests 390 px/);
  // The manifest's own width keeps its old wording.
  assert.match(widthFindings('queue', { ...wide, innerWidth: 780, scrollWidth: 843 }, { width: 780, height: 900 })[0], /at the declared width/);
});

test('D-380: a route names the journey\'s project in the address, so the stand\'s project count does not decide what is read', () => {
  const route = { name: 'stage-compare', path: '/stage-comparison', query: { project: '{project_uid}' } };
  const fill = (template) => template.replace('{project_uid}', 'prj_01ABC');
  assert.deepEqual(routeQuery(route, fill), { project: 'prj_01ABC' });
  assert.equal(queryString(routeQuery(route, fill)), '?project=prj_01ABC');
  assert.equal(queryString({}), '');
  assert.equal(queryString(undefined), '');
  assert.deepEqual(routeQuery({ name: 'x' }, fill), {});
  assert.equal(queryString({ a: 'b c', d: 'e&f' }), '?a=b%20c&d=e%26f');
  // A route whose query names something no earlier route captured fails loudly, as a path does.
  assert.throws(() => routeQuery(route, () => { throw new Error('route needs {project_uid} but no earlier route captured it'); }), /needs \{project_uid\}/);
});

/** Just enough of a page for the state expression: nodes with text, selected by an exact selector string. */
function pageOf(nodes) {
  return { document: { querySelectorAll: (selector) => nodes[selector] ?? [] } };
}

const CONFIRMED_PAIR = {
  bound_ms: 20000,
  present: [
    { selector: '[data-pair-counters]', text_matches: 'Сопоставлено: [1-9]' },
    { selector: 'section table' },
  ],
};

test('D-380: the confirmed-pair state needs the counter to count a pair AND the table to be drawn', () => {
  const probe = (nodes) => runInNewContext(stateProbeExpression(CONFIRMED_PAIR), pageOf(nodes));
  const withPair = probe({ '[data-pair-counters]': [{ innerText: 'Сопоставлено: 1 · Возможных пар: 0' }], 'section table': [{ innerText: 'x' }] });
  assert.deepEqual({ ok: withPair.ok, seen: [...withPair.seen] }, { ok: true, seen: [1, 1] });
  const noPair = probe({ '[data-pair-counters]': [{ innerText: 'Сопоставлено: 0 · Возможных пар: 4' }], 'section table': [] });
  assert.equal(noPair.ok, false, 'no confirmed pair is not the state');
  assert.deepEqual([...noPair.seen], [0, 0]);
  const noTable = probe({ '[data-pair-counters]': [{ innerText: 'Сопоставлено: 2 · Возможных пар: 0' }] });
  assert.equal(noTable.ok, false, 'a counter without its table is not the state');
  assert.deepEqual([...noTable.seen], [1, 0]);
  const chooser = probe({});
  assert.equal(chooser.ok, false, 'the chooser a stand with several projects shows is not the state');
});

test('D-380: the wait expression is null until the screen is in the state, because waitFor stops at the first reading that is not', () => {
  // `Page.waitFor` ends on any value that is not null/false/'': an expression that always answered an object would report
  // every screen as in the state at once. This is the control that shows the wait would not do that.
  const wait = (nodes) => runInNewContext(stateExpression(CONFIRMED_PAIR), pageOf(nodes));
  assert.equal(wait({}), null);
  assert.equal(wait({ '[data-pair-counters]': [{ innerText: 'Сопоставлено: 0' }], 'section table': [{ innerText: 'x' }] }), null);
  const reading = wait({ '[data-pair-counters]': [{ innerText: 'Сопоставлено: 3' }], 'section table': [{ innerText: 'x' }] });
  assert.equal(reading.ok, true);
  assert.equal(stateReached({ ok: true, value: reading }), true);
  assert.equal(stateReached({ ok: false, value: null }), false);
  assert.equal(stateReached(null), false);
  assert.equal(stateReached(undefined), false);
});

test('D-380: a route that is not in the asked-for state is a finding that says what the screen showed', () => {
  const waited = { ok: false, value: null, detail: { ok: false, seen: [0, 0] } };
  const [finding] = stateFindings('stage-compare', 'confirmed_pair', CONFIRMED_PAIR, waited, 'Сравнение стадий\nВыберите проект');
  assert.match(finding, /^stage-compare: this read asks for the state 'confirmed_pair'/);
  assert.match(finding, /within 20000 ms/);
  assert.match(finding, /last reading \{"ok":false,"seen":\[0,0\]\}/);
  assert.match(finding, /Выберите проект/);
  assert.deepEqual(stateFindings('stage-compare', 'confirmed_pair', CONFIRMED_PAIR, { ok: true, value: { ok: true, seen: [1, 1] } }, ''), []);
});

test('D-380: while dispatch is paused a screen that asked for the pause state must show "paused"', () => {
  const asked = ['GET /bff/v1/me', 'GET /bff/v1/execution/dispatch'];
  assert.deepEqual(pausedFindings('queue', asked, 'paused'), []);
  assert.match(pausedFindings('queue', asked, 'running')[0], /strip reads "running"/);
  assert.match(pausedFindings('queue', asked, null)[0], /strip reads null/);
  // A screen that never asked (a guest's sign-in, a viewer) is not held to a strip it does not draw.
  assert.deepEqual(pausedFindings('sign-in', ['GET /bff/v1/releases'], null), []);
  // A different operation under the same prefix is not the pause read.
  assert.deepEqual(pausedFindings('x', ['GET /bff/v1/execution/dispatch-history'], null), []);
});

test('D-380: the walk prefers the identity its own write half made to the first link, and says so when the page does not offer it', () => {
  assert.deepEqual(pickFollowed([], 'doc_B'), { value: undefined, note: null }, 'nothing offered: nothing to follow');
  assert.deepEqual(pickFollowed(['doc_A', 'doc_B'], undefined), { value: 'doc_A', note: null }, 'nothing captured: the first link, as before');
  assert.deepEqual(pickFollowed(['doc_A', 'doc_B'], 'doc_B'), { value: 'doc_B', note: null }, 'the journey\'s own, though it is not first');
  const missing = pickFollowed(['doc_A', 'doc_C'], 'doc_B');
  assert.equal(missing.value, 'doc_A', 'the walk goes on with the first so the rest of the routes are read');
  assert.match(missing.note, /offers 2 link\(s\) for it and none is the journey's own doc_B/, 'but never silently');
});

test('D-380: a refusal a read route declares is the state under test, and only that call with only that status', () => {
  const route = {
    optional_api: [
      { method: 'GET', path: '/stage-pairs/{stage_pair_id}/sheet-map', operationId: 'getStageSheetMap', refusal: true, expect_status: 404 },
      { method: 'GET', path: '/stage-pairs/{stage_pair_id}/chain-runs', operationId: 'listStageChainRuns' },
    ],
  };
  const refusals = declaredRefusals(route, '/bff/v1');
  assert.deepEqual(refusals, [{ shape: 'GET /bff/v1/stage-pairs/{id}/sheet-map', status: 404 }]);
  assert.equal(isDeclaredRefusal(refusals, 'GET /bff/v1/stage-pairs/{id}/sheet-map', 404), true);
  assert.equal(isDeclaredRefusal(refusals, 'GET /bff/v1/stage-pairs/{id}/sheet-map', 500), false, 'the same call failing otherwise is a finding');
  assert.equal(isDeclaredRefusal(refusals, 'GET /bff/v1/stage-pairs/{id}/chain-runs', 404), false, 'an optional call is not a declared refusal');
  assert.equal(isDeclaredRefusal(refusals, 'POST /bff/v1/stage-pairs/{id}/sheet-map', 404), false, 'another method is another call');
  assert.deepEqual(declaredRefusals({}, '/bff/v1'), []);
});

/** The knowledge base as the manifest declares it: a default tab that reads the journal, and two states that are not that tab. */
const KNOWLEDGE_BASE = {
  name: 'knowledge-base',
  path: '/knowledge-base',
  expects_api: [{ method: 'GET', path: '/decisions', operationId: 'listDecisions' }],
};
const MEMORY_LIST = {
  bound_ms: 30000,
  query: { kind: 'memory' },
  expects_api: [{ method: 'GET', path: '/decision-memory/cases', operationId: 'listDecisionMemoryCases' }],
  present: [{ selector: 'table[data-memory-table] tr[data-memory-case]' }],
};
const MEMORY_CASE = {
  bound_ms: 30000,
  query: { kind: 'memory', mcase: '{memory_case_id}' },
  bind: { case_id: 'memory_case_id' },
  expects_api: [{ method: 'GET', path: '/decision-memory/cases/{case_id}', operationId: 'getDecisionMemoryCase' }],
  present: [{ selector: '[data-memory-case-view]' }],
};
const fillFrom = (known) => (template) => template.replace(/\{([a-z_]+)\}/g, (_, name) => {
  if (known[name] === undefined) throw new Error(`route needs {${name}} but no earlier route captured it`);
  return known[name];
});

test('D-503: a named state opens the tab or the case the route\'s ordinary address does not, and no state changes the address', () => {
  const fill = fillFrom({ memory_case_id: 'dmc_01ABC' });
  // No state: the route's address, exactly as before (the cold walk of the knowledge base is «Замечания»).
  assert.deepEqual(stateRouteQuery(KNOWLEDGE_BASE, undefined, fill), {});
  assert.equal(queryString(stateRouteQuery(KNOWLEDGE_BASE, undefined, fill)), '');
  assert.deepEqual(stateRouteQuery({ query: { project: '{memory_case_id}' } }, undefined, fill), { project: 'dmc_01ABC' });
  // A state that declares no query (the confirmed pair) leaves the route's own query alone.
  assert.deepEqual(stateRouteQuery({ query: { project: '{memory_case_id}' } }, { bound_ms: 1, present: [] }, fill), { project: 'dmc_01ABC' });
  // A state that does declare one opens what it names, the route's keys kept and the state's winning.
  assert.equal(queryString(stateRouteQuery(KNOWLEDGE_BASE, MEMORY_LIST, fill)), '?kind=memory');
  assert.equal(queryString(stateRouteQuery(KNOWLEDGE_BASE, MEMORY_CASE, fill)), '?kind=memory&mcase=dmc_01ABC');
  assert.deepEqual(stateRouteQuery({ query: { kind: 'all', project: 'prj_X' } }, MEMORY_LIST, fill), { kind: 'memory', project: 'prj_X' });
  // An identity nothing captured fails loudly: a case state on a stand whose write half made no case is not a quiet default.
  assert.throws(() => stateRouteQuery(KNOWLEDGE_BASE, MEMORY_CASE, fillFrom({})), /needs \{memory_case_id\}/);
});

test('D-503: a state\'s own reads replace the route\'s, and a state with none leaves them', () => {
  assert.deepEqual(requiredReads(KNOWLEDGE_BASE, undefined).map((e) => e.operationId), ['listDecisions']);
  assert.deepEqual(requiredReads(KNOWLEDGE_BASE, MEMORY_LIST).map((e) => e.operationId), ['listDecisionMemoryCases'], 'the memory tab does not read the journal');
  assert.deepEqual(requiredReads(KNOWLEDGE_BASE, { bound_ms: 1, present: [] }).map((e) => e.operationId), ['listDecisions']);
  assert.deepEqual(requiredReads({ name: 'x' }, undefined), []);
  assert.deepEqual(requiredReads({ name: 'x' }, { bound_ms: 1, present: [] }), []);
  // An empty list is a statement ("this state reads nothing"), not a missing one.
  assert.deepEqual(requiredReads(KNOWLEDGE_BASE, { ...MEMORY_LIST, expects_api: [] }), []);
});

test('D-503: a state names an identity the write half captured, under the contract\'s own name when it binds one', () => {
  const known = { project_uid: 'prj_X', memory_case_id: 'dmc_01ABC' };
  assert.equal(stateView(known, undefined), known, 'no state: the very same map');
  assert.equal(stateView(known, null), known);
  assert.deepEqual(stateView(known, MEMORY_LIST), known, 'a state with no bind adds nothing');
  const view = stateView(known, MEMORY_CASE);
  assert.equal(view.case_id, 'dmc_01ABC');
  assert.equal(view.memory_case_id, 'dmc_01ABC');
  assert.equal(known.case_id, undefined, 'the captured map is not written to');
  // The read it declares is addressed by the bound name.
  assert.equal(fillFrom(view)(MEMORY_CASE.expects_api[0].path), '/decision-memory/cases/dmc_01ABC');
  // A bind to a name nothing captured stays undefined, so the path fails loudly instead of reading `/cases/undefined`.
  assert.throws(() => fillFrom(stateView({ project_uid: 'prj_X' }, MEMORY_CASE))(MEMORY_CASE.expects_api[0].path), /needs \{case_id\}/);
});
