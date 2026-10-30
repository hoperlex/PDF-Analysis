/** Reproducible source census only. Never starts an API, browser, worker or scan. */
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const sourceRoot = process.argv.find((value) => value.startsWith('--source-root='))?.slice('--source-root='.length) ?? root;
const read = (file) => readFileSync(resolve(sourceRoot, file), 'utf8');
const line = (text, offset) => text.slice(0, offset).split('\n').length;
const api = JSON.parse(read('contracts/api/v1/openapi.json'));
const security = read('src/auditmanager/api/security.py');
const adapters = read('src/auditmanager/bootstrap/adapters.py');
const composition = read('src/auditmanager/bootstrap/composition.py');
const routers = ['comparison_stage_pairs', 'comparison_stage_links', 'comparison_stage_runs',
  'comparison_stage_text', 'comparison_stage_uploads', 'comparison_stage_c4'];
const operations = new Map(Object.entries(api.paths).flatMap(([path, item]) => Object.entries(item)
  .filter(([, value]) => value?.operationId).map(([method, value]) => [value.operationId, { ...value, method: method.toUpperCase(), path }])));
const rows = [];
for (const router of routers) {
  const file = `src/auditmanager/api/routers/${router}.py`;
  const source = read(file);
  const adapterName = source.match(/\b(ComparisonStage\w+)Port\b/)?.[1] + 'Adapter';
  const adapterOffset = adapters.indexOf(`class ${adapterName}(`);
  assert.ok(adapterOffset >= 0, `missing adapter class ${adapterName}`);
  const followingClass = adapters.indexOf('\nclass ', adapterOffset + 1);
  const adapterSource = adapters.slice(adapterOffset, followingClass < 0 ? undefined : followingClass);
  for (const match of source.matchAll(/operation_id\s*=\s*["']([^"']+)["']/g)) {
    const name = match[1], operation = operations.get(name);
    assert.ok(operation, name);
    const roleIndex = security.indexOf(`"${name}"`);
    assert.ok(roleIndex >= 0, `missing role declaration ${name}`);
    const roleLine = security.slice(roleIndex, security.indexOf('\n', roleIndex));
    const role = /_ANY_ROLE/.test(roleLine) ? 'authenticated admin or expert' : 'authenticated expert';
    const routeChunk = source.slice(match.index, source.indexOf('\n    @router.', match.index + 1) < 0 ? undefined : source.indexOf('\n    @router.', match.index + 1));
    const delegated = [...routeChunk.matchAll(/\b[a-z_]+\.([a-z_]+)\(/g)].map((m) => m[1])
      .find((candidate) => new RegExp(`^    def ${candidate}\\(`, 'm').test(adapterSource));
    const localMethod = delegated && new RegExp(`^    def ${delegated}\\(`, 'm').exec(adapterSource);
    const method = localMethod && { index: localMethod.index + adapterOffset };
    assert.ok(method, `missing integrated adapter ${name}`);
    const next = adapters.indexOf('\n    def ', method.index + 1);
    const methodSource = adapters.slice(method.index, next < 0 ? undefined : next);
    const stub = /_stub\(|raise NotImplementedError/.test(methodSource);
    const request = operation.requestBody?.content ?? {};
    const content = Object.entries(request)[0];
    const schema = content?.[1]?.schema;
    const shape = schema?.$ref?.split('/').at(-1) ?? (content?.[0] === 'application/octet-stream' ? 'bounded binary' : 'none');
    const keyed = (operation.parameters ?? []).some((p) => p.name?.toLowerCase() === 'idempotency-key' && p.required);
    const scope = [...operation.path.matchAll(/\{([^}]+)\}/g)].map((m) => m[1]).join(' → ') || 'none';
    const responseTypes = [...new Set(Object.values(operation.responses).flatMap((r) => Object.keys(r.content ?? {})))].filter((v) => v !== 'application/json');
    const streaming = /streamStage/.test(name);
    const cost = /estimate/.test(name) ? 'source-bound estimate; no provider dispatch'
      : /startStageChain|resumeStageChain/.test(name) ? 'durable scheduling; with_ai consent + shared pre-call spend fence; execution UNVERIFIED'
      : /uploadStageUploadPart/.test(name) ? 'bounded source-byte intake; no model call'
      : /createStageReviewCard|Verdicts/.test(name) ? 'keyed expert act + audit; no model call'
      : 'no direct model dispatch';
    const evidence = `[router:${line(source, match.index)}](../../../${file}:${line(source, match.index)}); `
      + `[adapter:${line(adapters, method.index)}](../../../src/auditmanager/bootstrap/adapters.py:${line(adapters, method.index)}); `
      + `[role:${line(security, roleIndex)}](../../../src/auditmanager/api/security.py:${line(security, roleIndex)})`;
    rows.push({ wave: router === 'comparison_stage_c4' ? 'C4' : 'C3', name,
      text: `| ${router === 'comparison_stage_c4' ? 'C4' : 'C3'} \`${name}\`<br>\`${operation.method} ${operation.path}\` | ${role} | ${shape}; key ${keyed ? 'required' : 'none'} | typed ${scope}; service delegation only; cross-ID/runtime execution UNVERIFIED | ${cost} | ${streaming ? responseTypes.join(', ') : 'JSON'} | ${stub ? 'STUB' : 'WIRED in source'}; execution UNVERIFIED; ${evidence} |` });
  }
}
assert.equal(rows.filter((r) => r.wave === 'C3').length, 32);
assert.equal(rows.filter((r) => r.wave === 'C4').length, 24);
assert.equal(new Set(rows.map((r) => r.name)).size, 56);
const sha = process.argv.find((value) => value.startsWith('--source-sha='))?.split('=')[1];
if (process.argv.includes('--write')) assert.match(sha ?? '', /^[0-9a-f]{40}$/, '--write requires the exact reviewed --source-sha');
const moduleIndex = adapters.indexOf('class _StagesModuleGate');
const wiringIndex = composition.indexOf('comparison_stage_c4=');
assert.ok(moduleIndex >= 0 && wiringIndex >= 0, 'stage module gate/composition missing');
const output = `# Static comparison API exposure review — C3/C4\n\n`
  + `Current source snapshot: \`${sha}\`, 2026-10-30, CMP-JOURNEY-C4-01, API ${api.info.version}. **56 declarations: 32 C3 +24 C4. Execution UNVERIFIED.** No browser, auth/scope request matrix, worker journey or download was executed by this audit. The earlier 55-row snapshot is preserved verbatim in [prior snapshot](../../../tests/e2e/pc01/journey/fixtures/exposure-cmp-prior.md).\n\n`
  + `Every listed operation has a source role declaration and adapter entry. The common [stages gate](../../../src/auditmanager/bootstrap/adapters.py:${line(adapters, moduleIndex)}) and [current composition](../../../src/auditmanager/bootstrap/composition.py:${line(composition, wiringIndex)}) exist. Global account/token/profile checks precede roles. This is a source census, not proof that anonymous, inactive, default-password, incomplete-profile or cross-project requests were rejected. No table row is a runtime PASS.\n\n`
  + `| Wave / operation / method + path | Auth / role | Body / key | Scope evidence and limit | Cost / effect | Response / stream | Static state / exact pointers |\n`
  + `| --- | --- | --- | --- | --- | --- | --- |\n`
  + rows.map((r) => r.text).join('\n')
  + `\n\n## Deferred execution obligations\n\n`
  + `- Execute anonymous/account/role, malformed body/key, foreign parent/project, stale revision and retry matrices against the exact integrated candidate. The table does not certify those checks.\n`
  + `- Recorded C4 needs the explicit local synthetic worker fixture. Production composition refuses recorded routes; a displayed image estimate is insufficient. The journey requires source-digest/image-hash receipts for the actual run. Missing recordings/routes/crops fail, never skip.\n`
  + `- Prove run/effective revision/job scope, immutable raw evidence, lease fences, pre-call reservation and explicit graphic consent-window pauses. Source pointers alone do not prove these boundaries.\n`
  + `- Execute XLSX/PDF/HTML downloads: credential/scope, content type/disposition, actual bytes, accepted grouping and no provider call. No download ran today.\n`
  + `- ZIP intake retains raw-byte/disk/path/member bounds; __MACOSX remains rejected. No intake policy was changed by this task.\n\n`
  + `Reproduce the static census with \`node tests/e2e/pc01/journey/comparison-exposure.mjs\`. It launches no application or external scan.\n`;
if (process.argv.includes('--write')) writeFileSync(resolve(root, 'docs/program/compare/EXPOSURE-REVIEW-CMP.md'), output);
else console.log(`STATIC exposure census: 32 C3 +24 C4 =56; source wired ${rows.filter((r) => !r.text.includes('| STUB')).length}; runtime execution UNVERIFIED.`);
