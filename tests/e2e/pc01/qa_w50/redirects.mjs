/**
 * `W50-QA-01`, item 5 (stand half) — the guest redirect as the built server answers it: a real
 * `307` with `Location: /login?next=<concrete path and query>` for every registered `session`
 * screen, not a `200` with a redirect streamed inside it.
 *
 *     node tests/e2e/pc01/qa_w50/redirects.mjs --origin http://127.0.0.1:PORT
 *
 * The rows come from the registry's own source (`web/src/shared/config/screen-registry.ts`),
 * read here because this is a node script outside the Next build. Dynamic segments get
 * well-formed identifiers of the contract's shapes. No cookie is sent: this is a guest.
 *
 * Written by QA from the plan, without the lane reports.
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { parseArgs, recorder } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const HERE = dirname(fileURLToPath(import.meta.url));
const REGISTRY = join(HERE, '..', '..', '..', '..', 'web', 'src', 'shared', 'config', 'screen-registry.ts');

const source = readFileSync(REGISTRY, 'utf8');
const body = source.slice(source.indexOf('export const SCREEN_REGISTRY'), source.indexOf('] as const satisfies'));
const rows = [...body.matchAll(/\{\s*address:\s*'([^']+)'[\s\S]*?access:\s*'([^']+)'/g)].map((m) => ({
  address: m[1],
  access: m[2],
}));

const IDENTIFIERS = {
  project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
  document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
  run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8E',
};

const r = recorder('guest redirect');
const session = rows.filter((row) => row.access === 'session');
r.check('the registry source yields at least the eighteen W50 session rows', true, session.length >= 18);
r.note('rows read', { total: rows.length, session: session.length });

for (const row of rows.filter((x) => x.access !== 'public')) {
  const path = row.address.replace(/\[([^\]]+)\]/g, (_, name) => IDENTIFIERS[name] ?? `missing-${name}`);
  const asked = `${path}?view=table&page=2`;
  const response = await fetch(`${args.origin}${asked}`, { redirect: 'manual' });
  const raw = response.headers.get('location');
  // Relative or absolute, the same origin is required and the path and query are compared.
  const resolved = raw === null ? null : new URL(raw, args.origin);
  const location = resolved === null ? null : resolved.origin === args.origin ? resolved.pathname + resolved.search : raw;
  r.check(
    `GET ${asked} (${row.access})`,
    { status: 307, location: `/login?next=${encodeURIComponent(asked)}` },
    { status: response.status, location },
  );
  await response.body?.cancel();
}

const failed = r.failed();
console.log(`\n${failed.length === 0 ? 'REDIRECTS OK' : `REDIRECTS FAILED: ${failed.length}`}`);
process.exit(failed.length === 0 ? 0 : 1);
