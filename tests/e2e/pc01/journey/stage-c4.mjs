/** C4 semantic UI actions over real SP-1 bytes. No browser/network is started on import. */
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { readFileSync } from 'node:fs';

export const C4_PRODUCES = {
  upload: ['cmp_stage_documents', 'cmp_stage_last_upload_id', 'cmp_stage_last_candidate_id'],
  assembly: ['cmp_stage_pair_id', 'cmp_stage_assembly_id'], swapped_map: ['cmp_stage_swapped_revision_id'],
  full_run: ['cmp_stage_initial_run_id', 'cmp_stage_run_id'],
  repair_undo: ['cmp_stage_run_id', 'cmp_stage_repair_id', 'cmp_stage_recompute_run_id', 'cmp_stage_recompute_revision_id'],
  verdict: ['cmp_stage_card_id'], journal: [], promote: ['cmp_stage_promoted_card_id'],
};

const BOUND = 180000;
const id = (value, prefix) => assert.match(value ?? '', new RegExp(`^${prefix}_[0-9A-HJKMNP-TV-Z]{26}$`));
const body = (exchange) => { try { return JSON.parse(exchange.responseBody); } catch { return null; } };
const path = (exchange) => { try { return new URL(exchange.url).pathname; } catch { return ''; } };
const key = (exchange) => Object.entries(exchange.requestHeaders ?? {}).find(([name]) => name.toLowerCase() === 'idempotency-key')?.[1];

async function observed(page, method, suffix, { after = 0, accept = () => true, bound = BOUND } = {}) {
  const start = Date.now();
  while (Date.now() - start < bound) {
    await page.settle({ settleMs: 100, timeoutMs: 700 });
    const records = page.exchanges().slice(after).filter((e) => e.method === method && path(e).endsWith(suffix));
    for (const exchange of records.reverse()) {
      if (exchange.status === null || exchange.responseBody === null) continue;
      assert.ok(exchange.status >= 200 && exchange.status < 300,
        `${method} ${suffix}: ${exchange.status} ${exchange.responseBody?.slice(0, 250)}`);
      if (method !== 'GET') assert.ok(key(exchange), `${method} ${suffix}: missing command key`);
      const value = body(exchange);
      if (accept(value, exchange)) return { value, exchange };
    }
    await new Promise((done) => setTimeout(done, 200));
  }
  throw new Error(`${method} ${suffix}: no matching successful observed response within ${bound} ms`);
}

async function visible(page, selector, bound = BOUND) {
  const result = await page.waitFor(`(() => { const e=document.querySelector(${JSON.stringify(selector)}); return e && e.getClientRects().length ? true : null; })()`,
    { boundMs: bound, what: selector });
  assert.ok(result.ok, `missing visible control ${selector}`);
}
async function click(page, text, selector = 'button') {
  await page.click(selector, { text });
  await page.settle({ settleMs: 150, timeoutMs: 700 });
}
async function checked(page, selector, wanted = true) {
  await visible(page, selector);
  const value = await page.evaluate(`document.querySelector(${JSON.stringify(selector)}).checked`);
  if (value !== wanted) await page.click(selector);
  assert.equal(await page.evaluate(`document.querySelector(${JSON.stringify(selector)}).checked`), wanted, selector);
}
async function checkedLabel(page, label, wanted = true) {
  const expression = `(() => { const l=Array.from(document.querySelectorAll('label')).find(e=>e.textContent.trim()===${JSON.stringify(label)}); const e=l?.querySelector('input[type="checkbox"]'); return e ? {checked:e.checked} : null; })()`;
  const found = await page.waitFor(expression, { boundMs: BOUND, what: label });
  assert.ok(found.ok, `missing checkbox ${label}`);
  if (found.value.checked !== wanted) await page.click('label', { text: label });
  assert.equal((await page.evaluate(expression)).checked, wanted, label);
}
async function tab(page, name) { await page.click(`[data-stage-tab="${name}"]`); await visible(page, `#stage-panel-${name}`); }
async function choosePair(page, pair) { await visible(page, '[data-stage-pair-select]'); await page.select('[data-stage-pair-select]', { optionValue: pair }); }

async function upload(page, action, state, repositoryRoot) {
  const documents = []; let candidateId;
  for (const source of action.documents) {
    const after = page.exchanges().length;
    await page.attachFile('input[type="file"][accept=".pdf,.zip,application/pdf,application/zip"]', resolve(repositoryRoot, source.fixture));
    await click(page, 'Загрузить новый набор');
    const made = (await observed(page, 'POST', `/projects/${state.project_uid}/stage-uploads`, { after })).value;
    id(made.upload_id, 'stu');
    const candidate = (await observed(page, 'GET', `/stage-uploads/${made.upload_id}`, {
      after, accept: (value) => value?.candidates?.some((item) => item.state === 'proposed'),
    })).value.candidates.find((item) => item.state === 'proposed');
    id(candidate.candidate_id, 'suc');
    candidateId = candidate.candidate_id;
    const scope = 'article:has(select)';
    await page.select(scope, { label: 'Стадия', optionValue: source.stage });
    await page.select(scope, { label: 'Раздел', optionValue: 'AR' });
    await page.fill(scope, source.designation, { label: 'Шифр документа' });
    await click(page, 'Подтвердить документ', scope + ' button');
    const published = (await observed(page, 'POST', `/stage-upload-candidates/${candidate.candidate_id}/confirmation`, { after })).value;
    id(published.document_uid, 'doc');
    documents.push({ ...source, document_uid: published.document_uid, upload_id: made.upload_id });
  }
  return { cmp_stage_documents: documents, cmp_stage_last_upload_id: documents.at(-1).upload_id,
    cmp_stage_last_candidate_id: candidateId };
}

async function assembly(page, state) {
  const sources = state.cmp_stage_documents;
  assert.equal(sources.length, 4, 'SP-1 must contain one P and three R documents');
  await page.click('summary', { text: 'Создать сборку Р и связать со стадией П' });
  const scope = 'details:has(input[maxlength="200"])';
  const old = sources.find((s) => s.stage === 'P');
  await page.select(scope, { label: 'Документ П', optionValue: old.document_uid });
  await page.fill(scope, 'SP-1 · Р1 + Р2 + Р3', { label: 'Название сборки' });
  const checks = await page.evaluate(`Array.from(document.querySelectorAll(${JSON.stringify(scope + ' fieldset input[type="checkbox"]')})).length`);
  assert.equal(checks, 3, 'assembly UI must offer exactly this synthetic project’s three R documents');
  for (let index = 0; index < checks; index += 1) await checked(page, `${scope} fieldset label:nth-of-type(${index + 1}) input`);
  const after = page.exchanges().length;
  await click(page, 'Создать сборку', scope + ' button');
  const made = (await observed(page, 'POST', `/projects/${state.project_uid}/stage-assemblies`, { after })).value;
  id(made.assembly_id, 'sas'); assert.equal(made.members.length, 3);
  await click(page, 'Подтвердить пару П ↔ сборка Р', scope + ' button');
  const pair = (await observed(page, 'POST', `/projects/${state.project_uid}/stage-pairs`, { after })).value;
  id(pair.pair_id, 'stp'); assert.equal(pair.assembly_id, made.assembly_id);
  await choosePair(page, pair.pair_id);
  return { cmp_stage_pair_id: pair.pair_id, cmp_stage_assembly_id: made.assembly_id };
}

async function swappedMap(page, state) {
  await choosePair(page, state.cmp_stage_pair_id); await tab(page, 'sheets');
  await click(page, 'Принять видимые точные подсказки');
  const mapScope = '#stage-panel-sheets';
  await visible(page, '[data-stage-map-row="1"]');
  const rightSelect = `${mapScope} select`;
  const selects = await page.evaluate(`Array.from(document.querySelectorAll(${JSON.stringify(rightSelect)})).map((e,i)=>({index:i,value:e.value,options:Array.from(e.options).map(o=>({value:o.value,text:o.textContent}))}))`);
  const panes = selects.filter((s) => s.options.some((o) => o.value.startsWith('cpr_')));
  assert.ok(panes.length >= 2, 'native profile selectors absent');
  const passports = page.exchanges().filter((e) => /\/sheet-passports$/.test(path(e))).map(body).filter(Boolean).flatMap((value) => value.items ?? []);
  const leftPages = passports.filter((p) => p.side === 'left').sort((a,b) => a.page_number-b.page_number);
  const rightPages = passports.filter((p) => p.side === 'right');
  assert.equal(leftPages.length, 6); assert.equal(rightPages.length, 6);
  // The first two matched rows are deliberately crossed through the UI. Identities
  // are discovered from profile responses/selects; page labels never become IDs.
  const rows = await page.evaluate(`Array.from(document.querySelectorAll('[data-stage-map-row]')).map(e=>({row:e.dataset.stageMapRow,text:e.innerText}))`);
  assert.ok(rows.length >= 5, 'SP-1 high-confidence matching did not produce its five pairs');
  const rightOptions = panes[1].options.filter((o) => o.value.startsWith('cpr_'));
  assert.ok(rightOptions.length >= 2);
  await page.select(`${mapScope} select:has(option[value="${rightOptions[1].value}"])`, { optionValue: rightOptions[1].value });
  await click(page, 'Перенести Р сюда', '[data-stage-map-row="0"] button');
  await page.select(`${mapScope} select:has(option[value="${rightOptions[0].value}"])`, { optionValue: rightOptions[0].value });
  await click(page, 'Перенести Р сюда', '[data-stage-map-row="1"] button');
  const after = page.exchanges().length;
  await click(page, 'Сохранить решение эксперта');
  const map = (await observed(page, 'POST', `/stage-pairs/${state.cmp_stage_pair_id}/sheet-map`, { after })).value;
  id(map.revision_id, 'slk');
  assert.ok(map.items.filter((row) => row.relation === 'paired').length >= 5);
  assert.ok(map.items.some((row) => row.left_profile_id === leftPages[0].profile_id && row.right_profile_id === rightOptions[1].value), 'first source profile was not actually swapped');
  assert.ok(map.items.some((row) => row.left_profile_id === leftPages[1].profile_id && row.right_profile_id === rightOptions[0].value), 'second source profile was not actually swapped');
  return { cmp_stage_swapped_revision_id: map.revision_id };
}

async function startRun(page, state, { restart = false } = {}) {
  await choosePair(page, state.cmp_stage_pair_id);
  await checkedLabel(page, 'С описанием изменений ИИ', true);
  if (restart) await checkedLabel(page, 'Пересчитать заново', true);
  const after = page.exchanges().length;
  await click(page, 'Запустить полное сравнение');
  const estimate = (await observed(page, 'GET', '/chain-estimate', { after })).value;
  assert.equal(estimate.route.provider_mode, 'recorded', 'C4 journey refuses a live route');
  assert.ok(estimate.calls > 0 && estimate.images > 0, 'recorded C4 must reserve actual source images');
  await checked(page, '[data-stage-estimate] input[type="checkbox"]');
  await click(page, 'Подтвердить');
  const started = (await observed(page, 'POST', `/stage-pairs/${state.cmp_stage_pair_id}/chain-runs`, { after })).value;
  id(started.run_id, 'crn'); assert.equal(started.with_ai, true);
  let run = started;
  let windowAfter = after;
  for (let window = 0; window < 32; window += 1) {
    run = (await observed(page, 'GET', `/stage-chain-runs/${started.run_id}`, { after: windowAfter,
      accept: (value) => value?.state === 'completed' || value?.state === 'paused' || value?.state === 'failed' })).value;
    if (run.state === 'completed') break;
    assert.notEqual(run.state, 'failed', `full C4 failed: ${run.failure_reason}`);
    assert.ok(['overrun', 'budget_overrun'].includes(run.pause_reason), `unexpected pause ${run.pause_reason}`);
    const resumeAfter = page.exchanges().length;
    await click(page, 'Продолжить');
    const fresh = (await observed(page, 'GET', '/chain-estimate', { after: resumeAfter })).value;
    assert.equal(fresh.route.provider_mode, 'recorded');
    await checked(page, '[data-stage-estimate] input[type="checkbox"]');
    await click(page, 'Подтвердить');
    await observed(page, 'POST', `/stage-chain-runs/${run.run_id}/resume`, { after: resumeAfter });
    // A prior paused response must never satisfy the next window wait.
    windowAfter = resumeAfter;
    run = (await observed(page, 'GET', `/stage-chain-runs/${run.run_id}`, { after: resumeAfter,
      accept: (value) => ['completed','running','queued','failed'].includes(value?.state) })).value;
    if (run.state === 'completed') break;
    windowAfter = page.exchanges().length;
  }
  assert.equal(run.state, 'completed', 'C4 graphic consent windows exceeded the bounded walkthrough');
  assert.deepEqual(run.steps.map((s) => s.step_no), [1,2,3,4,5,6,7]);
  assert.ok(run.steps.every((s) => s.state === 'completed'));
  const receiptsPath = process.env.E2E_C4_RECORDED_RECEIPTS;
  assert.ok(receiptsPath, 'E2E_C4_RECORDED_RECEIPTS must name the explicit synthetic-worker receipt file');
  const receipts = readFileSync(receiptsPath, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).filter((r) => r.run_id === run.run_id);
  assert.ok(receipts.length > 0 && receipts.every((r) => r.fixture === 'synthetic-c4/1' && r.provider_mode === 'recorded'));
  assert.ok(receipts.some((r) => r.images > 0 && r.images <= 8 && r.png_sha256.length === r.images),
    'no actual source-image request receipt for this full run');
  return run;
}

async function fullRun(page, state) {
  const run = await startRun(page, state);
  return { cmp_stage_initial_run_id: run.run_id, cmp_stage_run_id: run.run_id };
}

async function repairUndo(page, state) {
  await choosePair(page, state.cmp_stage_pair_id);
  await page.select('[data-stage-run-select]', { optionValue: state.cmp_stage_initial_run_id });
  const after = page.exchanges().length;
  await page.click('summary', { text: 'Автоматические исправления связей' });
  // The repair query mounts with the run controls, before its details are opened.
  const repairs = (await observed(page, 'GET', `/stage-chain-runs/${state.cmp_stage_initial_run_id}/sheet-link-repairs`)).value;
  const applied = repairs.items.find((r) => r.state === 'applied');
  assert.ok(applied, 'swapped SP-1 map produced no HIGH deterministic repair; never skip undo');
  await click(page, 'Откатить исправление');
  const undone = (await observed(page, 'POST', `/stage-link-repairs/${applied.repair_id}/undo`, { after })).value;
  assert.equal(undone.state, 'undone');
  await tab(page, 'sheets');
  await click(page, 'Пересчитать текст');
  const recomputed = (await observed(page, 'POST', '/text-evidence/recomputation', { after })).value;
  id(recomputed.run_id, 'crn');
  const completed = recomputed.state === 'completed' ? recomputed : (await observed(page, 'GET', `/stage-chain-runs/${recomputed.run_id}`, { after,
    accept: (v) => ['completed','failed'].includes(v?.state) })).value;
  assert.equal(completed.state, 'completed');
  const fresh = await startRun(page, state, { restart: true });
  return { cmp_stage_run_id: fresh.run_id, cmp_stage_repair_id: applied.repair_id, cmp_stage_recompute_run_id: recomputed.run_id,
    cmp_stage_recompute_revision_id: recomputed.link_revision_id };
}

async function verdict(page, state) {
  await choosePair(page, state.cmp_stage_pair_id);
  await page.select('[data-stage-run-select]', { optionValue: state.cmp_stage_run_id });
  await tab(page, 'changes');
  const cards = (await observed(page, 'GET', `/stage-chain-runs/${state.cmp_stage_run_id}/cards`)).value;
  const card = cards.items.find((c) => c.class_name !== 'SERVICE_STRUCTURE');
  assert.ok(card && card.evidence.length > 0, 'no evidence-bound editable card');
  await checked(page, '#stage-panel-changes label:has(input[type="checkbox"]) input');
  const selector = `article[aria-labelledby="stage-card-${card.card_id}"]`;
  for (let opened = 0; opened < 5; opened += 1) {
    const closed = await page.evaluate(`document.querySelector(${JSON.stringify(`details:not([open]):has(${selector}) > summary`)}) !== null`);
    if (!closed) break;
    await page.click(`details:not([open]):has(${selector}) > summary`);
  }
  await checked(page, `${selector} input[type="radio"][name="verdict-${card.card_id}"]`);
  const after = page.exchanges().length;
  await click(page, 'Сохранить решения');
  const saved = (await observed(page, 'POST', `/stage-chain-runs/${state.cmp_stage_run_id}/card-verdicts`, { after })).value;
  assert.ok(saved.items.some((v) => v.card_id === card.card_id && v.decision === 'accepted'));
  return { cmp_stage_card_id: card.card_id };
}

async function journal(page, state) {
  await choosePair(page, state.cmp_stage_pair_id);
  await page.select('[data-stage-run-select]', { optionValue: state.cmp_stage_run_id });
  await tab(page, 'journal');
  for (const grouping of ['designation','section','system']) {
    const after = page.exchanges().length;
    await page.select('#stage-panel-journal', { label: 'Группировать', optionValue: grouping });
    const got = (await observed(page, 'GET', `/stage-chain-runs/${state.cmp_stage_run_id}/journal`, {
      after: grouping === 'designation' ? 0 : after, accept: (v) => v?.grouping === grouping })).value;
    assert.ok(got.accepted_count >= 1 && got.groups.length > 0);
    assert.ok(got.groups.every((g) => typeof g.key === 'string' && typeof g.label === 'string' && Array.isArray(g.rows)));
    assert.ok(got.groups.flatMap((g) => g.rows).some((c) => c.card_id === state.cmp_stage_card_id));
  }
  for (const label of ['Excel ↓','PDF ↓','HTML ↓']) {
    const enabled = `Array.from(document.querySelectorAll('#stage-panel-journal button')).some(e=>e.textContent.trim()===${JSON.stringify(label)}&&!e.disabled)`;
    assert.ok((await page.waitFor(enabled, { boundMs: BOUND, what: `enabled download ${label}` })).ok);
    await click(page, label, '#stage-panel-journal button');
    assert.ok((await page.waitFor(enabled, { boundMs: BOUND, what: `completed download ${label}` })).ok);
  }
  return {};
}

async function promote(page, state) {
  await choosePair(page, state.cmp_stage_pair_id);
  await page.select('[data-stage-run-select]', { optionValue: state.cmp_stage_run_id });
  await tab(page, 'sheets');
  await visible(page, 'details:has([data-stage-masked-fragment]) > summary');
  await page.click('details:has([data-stage-masked-fragment]) > summary');
  await visible(page, '[data-stage-masked-fragment]');
  await click(page, 'На экспертную проверку', '[data-stage-masked-fragment] button');
  const form = '[aria-label="Экспертная проверка свидетельств"]';
  await page.fill(form, 'Синтетический SP-1: повторная экспертная проверка контекста.',
    { label: 'Причина экспертной проверки', tag: 'textarea' });
  const after = page.exchanges().length;
  await click(page, 'Создать карточку проверки', form + ' button');
  const card = (await observed(page, 'POST', `/stage-chain-runs/${state.cmp_stage_run_id}/review-cards`, { after })).value;
  id(card.card_id, 'ccd'); assert.equal(card.class_name, 'REVIEW'); assert.equal(card.verdict, undefined);
  assert.ok(card.evidence_ids.some((value) => value.startsWith('stf_')) && card.evidence.every((e) => e.absence_proven === false));
  return { cmp_stage_promoted_card_id: card.card_id };
}

const PHASES = { upload, assembly, swapped_map: swappedMap, full_run: fullRun, repair_undo: repairUndo, verdict, journal, promote };
export async function stageC4Action({ page, action, captured, repositoryRoot }) {
  assert.ok(PHASES[action.phase], `unknown C4 phase ${action.phase}`);
  await page.select('main', { label: 'Проект', optionValue: captured.project_uid });
  await visible(page, '[data-stage-workspace]');
  const values = await PHASES[action.phase](page, action.phase === 'upload' ? action : captured,
    action.phase === 'upload' ? captured : undefined, repositoryRoot);
  assert.deepEqual(Object.keys(values).sort(), C4_PRODUCES[action.phase].slice().sort());
  return { captured: values, phase: action.phase, executed: true };
}
