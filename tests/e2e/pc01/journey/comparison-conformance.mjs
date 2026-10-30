#!/usr/bin/env node
/** Static comparison manifest/corpus census. This never launches a browser or claims acceptance. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../../../..');
const manifest = JSON.parse(readFileSync(resolve(here, 'manifest.json'), 'utf8'));
const api = JSON.parse(readFileSync(resolve(root, 'contracts/api/v1/openapi.json'), 'utf8'));
const operations = new Map(Object.entries(api.paths).flatMap(([path, item]) =>
  Object.entries(item).filter(([, value]) => value?.operationId).map(([method, value]) =>
    [value.operationId, { method: method.toUpperCase(), path, responses: value.responses }])));
const steps = manifest.write.steps.filter((step) => step.name.startsWith('cmp-'));
assert.ok(steps.length >= 14, 'version/C4 comparison actions disappeared');
assert.equal(new Set(manifest.write.steps.map((step) => step.name)).size, manifest.write.steps.length, 'duplicate step name');
for (const step of steps) {
  assert.equal(step.requires_provider_mode, 'recorded', step.name);
  assert.notEqual(step.pending_v3_activation, true, `${step.name}: comparison must not hide behind AR activation`);
  assert.notEqual(step.reads_only, true, `${step.name}: real controls are pressed`);
  assert.ok(step.actions.length > 0, `${step.name}: missing actions`);
  for (const call of step.expects_api) {
    const operation = operations.get(call.operationId);
    assert.ok(operation, `${step.name}: unknown operation ${call.operationId}`);
    assert.equal(call.method, operation.method, `${step.name}: method`);
    assert.equal(call.path, operation.path, `${step.name}: path`);
    assert.ok(String(call.expect_status) in operation.responses, `${step.name}: unpublished status`);
    if (call.method !== 'GET') assert.ok(step.expects_request.some((check) =>
      check.of === call.operationId && check.requires_idempotency_key === true), `${step.name}: command key not asserted`);
  }
}
const upload = steps.find((step) => step.name === 'cmp-version-upload-synthetic-five');
const attached = upload.actions.filter((action) => action.do === 'attach_file');
const key = JSON.parse(readFileSync(resolve(root, 'fixtures/comparison/vs1/answer_key.json'), 'utf8'));
assert.equal(attached.length, key.versions.length);
for (const action of attached) {
  const expected = key.versions.find((version) => action.fixture === `fixtures/comparison/${version.file}`);
  assert.ok(expected, `unrecognised corpus file ${action.fixture}`);
  const bytes = readFileSync(resolve(root, action.fixture));
  assert.equal(bytes.length, expected.bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), expected.sha256);
}
const review = readFileSync(resolve(root, 'docs/program/compare/EXPOSURE-REVIEW-CMP.md'), 'utf8');
const rows = [...review.matchAll(/^\| (C[34]) `([^`]+)`/gm)];
assert.equal(rows.length, 56, 'exposure census');
assert.equal(rows.filter((row) => row[1] === 'C3').length, 32);
assert.equal(rows.filter((row) => row[1] === 'C4').length, 24);
assert.equal(new Set(rows.map((row) => row[2])).size, 56);
for (const row of rows) assert.ok(operations.has(row[2]), `unknown exposure operation ${row[2]}`);
const c4 = steps.filter((step) => step.name.startsWith('cmp-stage-'));
assert.deepEqual(c4.map((step) => step.actions[0].phase), ['upload','assembly','swapped_map','full_run','repair_undo','verdict','journal','promote']);
const docs = c4[0].actions[0].documents;
assert.equal(docs.length, 4); assert.equal(docs.filter((doc) => doc.stage === 'P').length, 1);
for (const doc of docs) {
  const bytes = readFileSync(resolve(root, doc.fixture));
  assert.equal(bytes.length, doc.bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), doc.sha256);
  if (doc.derived_from) assert.equal(createHash('sha256').update(readFileSync(resolve(root, doc.derived_from))).digest('hex'), doc.source_sha256);
}
assert.equal(c4.find((step) => step.actions[0].phase === 'journal').expects_download.length, 3);
assert.ok(review.includes('Execution UNVERIFIED'));
console.log(`STATIC CONFORMANCE: ${steps.length} comparison steps, exact VS-1/SP-1/declared graphic derivative bytes, 56 exposure rows. Browser/worker actions NOT EXECUTED.`);
