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
assert.ok(steps.length >= 6, 'comparison actions disappeared');
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
assert.equal(rows.length, 55, 'exposure census');
assert.equal(rows.filter((row) => row[1] === 'C3').length, 32);
assert.equal(rows.filter((row) => row[1] === 'C4').length, 23);
assert.equal(new Set(rows.map((row) => row[2])).size, 55);
for (const row of rows) assert.ok(operations.has(row[2]), `unknown exposure operation ${row[2]}`);
console.log(`STATIC CONFORMANCE: ${steps.length} comparison steps, exact VS-1 bytes, 55 exposure rows. Browser actions NOT EXECUTED.`);
