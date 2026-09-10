#!/usr/bin/env node
/**
 * Generate the typed API client under `web/src/shared/api/generated/**` from the frozen
 * OpenAPI document at `contracts/api/v1/openapi.json`.
 *
 * The contract is read-only to this script and to the session that owns it. If the
 * document cannot generate, the answer is to report the defect to the contract's owner
 * (session `A1`), never to edit the document so the generator is happy: a client and a
 * contract reconciled by the same hand prove nothing.
 *
 * Determinism is the whole point. The output is a pure function of the input bytes:
 *   - no timestamp, no hostname, no absolute path and no environment value is emitted;
 *   - every iteration order is an explicit, locale-independent sort;
 *   - line endings are LF and every file ends with exactly one newline.
 * Running the generator twice on the same document must produce byte-identical files,
 * and `--check` asserts exactly that against the committed tree.
 *
 * Usage:
 *   node scripts/generate-api-client.mjs            # write the client and the snapshot
 *   node scripts/generate-api-client.mjs --check    # verify, write nothing, exit 1 on drift
 *   node scripts/generate-api-client.mjs --input <openapi.json> --out <dir> --snapshot <file>
 */

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const GENERATOR_VERSION = '1.0.0';

const WEB_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO_ROOT = resolve(WEB_ROOT, '..');

const DEFAULT_INPUT = join(REPO_ROOT, 'contracts', 'api', 'v1', 'openapi.json');
const DEFAULT_OUT = join(WEB_ROOT, 'src', 'shared', 'api', 'generated');
const DEFAULT_SNAPSHOT = join(WEB_ROOT, 'openapi', 'openapi.json');

/** The complete set of files this generator owns. Anything else in `out` is drift. */
const OWNED_FILES = ['types.gen.ts', 'operations.gen.ts', 'client.gen.ts', 'index.ts'];

const HTTP_METHODS = ['get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'];

// --------------------------------------------------------------------------------------
// small deterministic helpers
// --------------------------------------------------------------------------------------

/** Locale-independent ascending string comparison. `localeCompare` is not deterministic. */
const byCodeUnit = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

const sortedKeys = (obj) => Object.keys(obj ?? {}).sort(byCodeUnit);

const pascal = (s) => s.charAt(0).toUpperCase() + s.slice(1);

const screamingSnake = (s) =>
  s
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2')
    .toUpperCase();

const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

/** A JS string literal, single-quoted, for emission into TypeScript. */
const lit = (s) => `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;

/** Render a description as a JSDoc block at the given indent, or nothing. */
function jsdoc(text, indent = '') {
  if (!text) return '';
  const safe = String(text).replace(/\*\//g, '*\\/');
  const lines = safe.split('\n');
  if (lines.length === 1) return `${indent}/** ${lines[0]} */\n`;
  return (
    `${indent}/**\n` +
    lines.map((l) => (l.length > 0 ? `${indent} * ${l}` : `${indent} *`)).join('\n') +
    `\n${indent} */\n`
  );
}

/** Deduplicate a list of rendered type strings, preserving first-seen order. */
function dedupe(list) {
  const seen = new Set();
  const out = [];
  for (const item of list) {
    if (!seen.has(item)) {
      seen.add(item);
      out.push(item);
    }
  }
  return out;
}

// --------------------------------------------------------------------------------------
// defects: the generator refuses rather than guessing
// --------------------------------------------------------------------------------------

class ContractDefect extends Error {
  constructor(where, detail) {
    super(
      `contract defect at ${where}: ${detail}\n` +
        'The OpenAPI document is read-only to this generator. Report the defect to the ' +
        'owner of contracts/api/v1/** and do not repair it here.',
    );
    this.name = 'ContractDefect';
  }
}

// --------------------------------------------------------------------------------------
// schema -> TypeScript
// --------------------------------------------------------------------------------------

const PRIMITIVES = {
  string: 'string',
  number: 'number',
  integer: 'number',
  boolean: 'boolean',
  null: 'null',
  object: 'Record<string, unknown>',
};

/** Name of a `#/components/schemas/X` reference, or null when the ref points elsewhere. */
function schemaRefName(ref) {
  const prefix = '#/components/schemas/';
  return typeof ref === 'string' && ref.startsWith(prefix) ? ref.slice(prefix.length) : null;
}

/**
 * Render one JSON Schema node as a TypeScript type.
 *
 * `where` is a JSON-pointer-ish breadcrumb used only in defect messages.
 */
function renderType(schema, where, indent = '') {
  if (schema === true) return 'unknown';
  if (schema === false) return 'never';
  if (schema === undefined || schema === null) return 'unknown';
  if (typeof schema !== 'object') throw new ContractDefect(where, 'schema is not an object');

  if (schema.$ref !== undefined) {
    const name = schemaRefName(schema.$ref);
    if (name === null) throw new ContractDefect(where, `unsupported $ref ${schema.$ref}`);
    return name;
  }

  if (schema.const !== undefined) return JSON.stringify(schema.const);

  if (Array.isArray(schema.enum)) {
    if (schema.enum.length === 0) throw new ContractDefect(where, 'empty enum');
    return dedupe(schema.enum.map((v) => JSON.stringify(v))).join(' | ');
  }

  if (Array.isArray(schema.allOf)) {
    const parts = schema.allOf.map((s, i) => renderType(s, `${where}/allOf/${i}`, indent));
    return dedupe(parts).join(' & ');
  }

  for (const key of ['oneOf', 'anyOf']) {
    if (Array.isArray(schema[key])) {
      const parts = schema[key].map((s, i) => renderType(s, `${where}/${key}/${i}`, indent));
      return dedupe(parts).join(' | ');
    }
  }

  if (Array.isArray(schema.type)) {
    const parts = schema.type.map((t) =>
      renderType({ ...schema, type: t }, `${where}/type/${t}`, indent),
    );
    return dedupe(parts).join(' | ');
  }

  const type = schema.type;

  if (type === 'array') {
    const items = renderType(schema.items ?? true, `${where}/items`, indent);
    return `Array<${items.includes(' ') ? `(${items})` : items}>`;
  }

  if (type === 'object' || (type === undefined && schema.properties !== undefined)) {
    return renderObject(schema, where, indent);
  }

  if (type === 'string' && schema.format === 'binary') return 'Blob';

  if (type !== undefined) {
    const rendered = PRIMITIVES[type];
    if (rendered === undefined) throw new ContractDefect(where, `unknown type ${type}`);
    return rendered;
  }

  // A schema with no type, no ref, no enum and no combinator constrains nothing.
  return 'unknown';
}

function renderObject(schema, where, indent) {
  const inner = `${indent}  `;
  const required = new Set(schema.required ?? []);
  const props = schema.properties ?? {};
  const names = sortedKeys(props);

  const lines = [];
  for (const name of names) {
    const prop = props[name];
    const doc = jsdoc(prop.description, inner);
    const optional = required.has(name) ? '' : '?';
    const key = /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(name) ? name : lit(name);
    lines.push(`${doc}${inner}${key}${optional}: ${renderType(prop, `${where}/${name}`, inner)};`);
  }

  const extra = schema.additionalProperties;
  if (extra !== undefined && extra !== false) {
    const valueType = extra === true ? 'unknown' : renderType(extra, `${where}/additionalProperties`, inner);
    lines.push(`${inner}[key: string]: ${valueType};`);
  }

  if (lines.length === 0) return 'Record<string, never>';
  return `{\n${lines.join('\n')}\n${indent}}`;
}

// --------------------------------------------------------------------------------------
// file headers
// --------------------------------------------------------------------------------------

function header(meta, purpose) {
  return (
    '/**\n' +
    ' * GENERATED FILE - DO NOT EDIT.\n' +
    ' *\n' +
    ` * ${purpose}\n` +
    ' *\n' +
    ' * Produced by `npm --prefix web run api:generate`\n' +
    ` * (web/scripts/generate-api-client.mjs, generator ${GENERATOR_VERSION})\n` +
    ' * from contracts/api/v1/openapi.json\n' +
    ` *   ${meta.title} ${meta.version} (OpenAPI ${meta.openapi})\n` +
    ` *   sha256 ${meta.digest}\n` +
    ' *\n' +
    ' * Hand-editing this file makes the contract drift guard in web/tests/contract go\n' +
    ' * red. The contract belongs to session A1: change it there, then regenerate.\n' +
    ' */'
  );
}

// --------------------------------------------------------------------------------------
// types.gen.ts
// --------------------------------------------------------------------------------------

function emitTypes(doc, meta) {
  const schemas = doc.components?.schemas ?? {};
  const names = sortedKeys(schemas);
  if (names.length === 0) throw new ContractDefect('#/components/schemas', 'no schemas');

  const out = [header(meta, 'Every component schema of the PC-01 API as a TypeScript type.')];
  out.push('');
  out.push('/** The `info.version` of the contract these types were generated from. */');
  out.push(`export const CONTRACT_VERSION = ${lit(meta.version)};`);
  out.push('');
  out.push('/** sha256 of the OpenAPI document these types were generated from. */');
  out.push(`export const CONTRACT_DIGEST = ${lit(meta.digest)};`);
  out.push('');
  out.push('/** Every component schema name in the contract, sorted. */');
  out.push('export const SCHEMA_NAMES = [');
  for (const name of names) out.push(`  ${lit(name)},`);
  out.push('] as const;');

  for (const name of names) {
    const schema = schemas[name];
    out.push('');

    const isStringEnum =
      schema.type === 'string' && Array.isArray(schema.enum) && schema.enum.length > 0;

    if (isStringEnum) {
      const constName = `${screamingSnake(name)}_VALUES`;
      out.push(jsdoc(schema.description, '').trimEnd() || `/** ${name}. */`);
      out.push(`export const ${constName} = [`);
      for (const value of schema.enum) out.push(`  ${lit(value)},`);
      out.push('] as const;');
      out.push('');
      out.push(`/** ${name} - the closed value set above. */`);
      out.push(`export type ${name} = (typeof ${constName})[number];`);
      continue;
    }

    const doc0 = jsdoc(schema.description, '');
    if (doc0) out.push(doc0.trimEnd());
    out.push(`export type ${name} = ${renderType(schema, `#/components/schemas/${name}`, '')};`);

    if (schema.type === 'string' && typeof schema.pattern === 'string') {
      out.push('');
      out.push(`/** The contract pattern for \`${name}\`. Anchored; use with \`new RegExp()\`. */`);
      out.push(`export const ${screamingSnake(name)}_PATTERN = ${JSON.stringify(schema.pattern)};`);
    }
  }

  return `${out.join('\n')}\n`;
}

// --------------------------------------------------------------------------------------
// operations.gen.ts
// --------------------------------------------------------------------------------------

const IDEMPOTENCY_HEADER = 'Idempotency-Key';
const CORRELATION_HEADER = 'X-Correlation-Id';

function derefParameter(doc, node, where) {
  if (node.$ref === undefined) return node;
  const prefix = '#/components/parameters/';
  if (!node.$ref.startsWith(prefix)) throw new ContractDefect(where, `unsupported $ref ${node.$ref}`);
  const name = node.$ref.slice(prefix.length);
  const resolved = doc.components?.parameters?.[name];
  if (resolved === undefined) throw new ContractDefect(where, `dangling $ref ${node.$ref}`);
  return resolved;
}

/** Collect every operation, resolved and sorted by operationId. */
function collectOperations(doc) {
  const operations = [];
  const seenIds = new Set();

  for (const path of sortedKeys(doc.paths)) {
    const item = doc.paths[path];
    const shared = (item.parameters ?? []).map((p, i) =>
      derefParameter(doc, p, `#/paths/${path}/parameters/${i}`),
    );

    for (const method of HTTP_METHODS) {
      const op = item[method];
      if (op === undefined) continue;
      const where = `#/paths/${path}/${method}`;

      const operationId = op.operationId;
      if (typeof operationId !== 'string' || operationId.length === 0) {
        throw new ContractDefect(where, 'missing operationId; a client cannot name this call');
      }
      if (seenIds.has(operationId)) {
        throw new ContractDefect(where, `duplicate operationId ${operationId}`);
      }
      seenIds.add(operationId);

      const params = [
        ...shared,
        ...(op.parameters ?? []).map((p, i) => derefParameter(doc, p, `${where}/parameters/${i}`)),
      ];

      const pathParams = params.filter((p) => p.in === 'path');
      const queryParams = params.filter((p) => p.in === 'query');
      const headerParams = params.filter((p) => p.in === 'header');

      // Every `{token}` in the path template must have a declared path parameter.
      const declared = new Set(pathParams.map((p) => p.name));
      for (const token of path.matchAll(/\{([^}]+)\}/g)) {
        if (!declared.has(token[1])) {
          throw new ContractDefect(where, `path template names {${token[1]}} with no parameter`);
        }
      }

      const requiresIdempotencyKey = headerParams.some(
        (p) => p.name === IDEMPOTENCY_HEADER && p.required === true,
      );
      const extraHeaders = headerParams.filter(
        (p) => p.name !== IDEMPOTENCY_HEADER && p.name !== CORRELATION_HEADER,
      );

      let requestMediaType = null;
      let requestSchema = null;
      if (op.requestBody !== undefined) {
        const content = op.requestBody.content ?? {};
        const mediaTypes = sortedKeys(content);
        if (mediaTypes.length !== 1) {
          throw new ContractDefect(`${where}/requestBody`, `expected one media type, found ${mediaTypes.length}`);
        }
        requestMediaType = mediaTypes[0];
        requestSchema = content[requestMediaType].schema;
      }

      const successCodes = sortedKeys(op.responses).filter((c) => /^2\d\d$/.test(c));
      if (successCodes.length === 0) throw new ContractDefect(where, 'no 2xx response declared');
      const primary = successCodes[0];
      const primaryResponse = op.responses[primary];
      const responseContent = primaryResponse.content ?? {};
      const responseMediaTypes = sortedKeys(responseContent);
      if (responseMediaTypes.length > 1) {
        throw new ContractDefect(`${where}/responses/${primary}`, 'more than one response media type');
      }
      const responseMediaType = responseMediaTypes[0] ?? null;
      const responseSchema = responseMediaType ? responseContent[responseMediaType].schema : null;

      const errorCodes = sortedKeys(op.responses).filter((c) => !/^2\d\d$/.test(c));

      operations.push({
        operationId,
        method: method.toUpperCase(),
        path,
        summary: op.summary ?? null,
        description: op.description ?? null,
        tags: [...(op.tags ?? [])].sort(byCodeUnit),
        pathParams: pathParams.slice().sort((a, b) => byCodeUnit(a.name, b.name)),
        queryParams: queryParams.slice().sort((a, b) => byCodeUnit(a.name, b.name)),
        extraHeaders: extraHeaders.slice().sort((a, b) => byCodeUnit(a.name, b.name)),
        requiresIdempotencyKey,
        requestMediaType,
        requestSchema,
        successStatuses: successCodes.map(Number),
        responseMediaType,
        responseSchema,
        errorStatuses: errorCodes.map(Number),
        where,
      });
    }
  }

  operations.sort((a, b) => byCodeUnit(a.operationId, b.operationId));
  return operations;
}

function inputTypeName(op) {
  return `${pascal(op.operationId)}Input`;
}

function resultTypeName(op) {
  return `${pascal(op.operationId)}Result`;
}

function referencedSchemaNames(operations) {
  const names = new Set();
  const walk = (node) => {
    if (node === null || typeof node !== 'object') return;
    if (typeof node.$ref === 'string') {
      const name = schemaRefName(node.$ref);
      if (name !== null) names.add(name);
    }
    for (const key of Object.keys(node)) walk(node[key]);
  };
  for (const op of operations) {
    for (const p of [...op.pathParams, ...op.queryParams, ...op.extraHeaders]) walk(p.schema);
    walk(op.requestSchema);
    walk(op.responseSchema);
  }
  names.add('IdempotencyKey');
  names.add('CorrelationId');
  return [...names].sort(byCodeUnit);
}

function emitOperations(doc, meta, operations) {
  const imported = referencedSchemaNames(operations);

  const out = [
    header(
      meta,
      'One typed input and result per operation, plus the runtime descriptor table the\n * transport executes.',
    ),
  ];
  out.push('');
  out.push('import type {');
  for (const name of imported) out.push(`  ${name},`);
  out.push("} from './types.gen';");
  out.push('');
  out.push('/** Every operationId in the contract, sorted. */');
  out.push('export const OPERATION_IDS = [');
  for (const op of operations) out.push(`  ${lit(op.operationId)},`);
  out.push('] as const;');
  out.push('');
  out.push('/** The closed set of operations this client can perform. */');
  out.push('export type OperationId = (typeof OPERATION_IDS)[number];');

  for (const op of operations) {
    const where = `#/paths/${op.path}/${op.method.toLowerCase()}`;
    out.push('');
    out.push('// ' + '-'.repeat(84));
    out.push(`// ${op.operationId} - ${op.method} ${op.path}`);
    out.push('// ' + '-'.repeat(84));
    out.push('');

    const docLines = [];
    if (op.summary) docLines.push(op.summary);
    if (op.description) {
      if (docLines.length > 0) docLines.push('');
      docLines.push(op.description);
    }
    if (docLines.length > 0) out.push(jsdoc(docLines.join('\n'), '').trimEnd());

    const fields = [];

    if (op.pathParams.length > 0) {
      const inner = op.pathParams
        .map((p) => `    ${p.name}: ${renderType(p.schema, `${where}/path/${p.name}`, '    ')};`)
        .join('\n');
      fields.push(`  /** Path parameters, substituted into \`${op.path}\`. */\n  path: {\n${inner}\n  };`);
    }

    if (op.queryParams.length > 0) {
      const inner = op.queryParams
        .map((p) => {
          const doc0 = jsdoc(p.description, '    ');
          const optional = p.required === true ? '' : '?';
          return `${doc0}    ${p.name}${optional}: ${renderType(p.schema, `${where}/query/${p.name}`, '    ')};`;
        })
        .join('\n');
      const anyRequired = op.queryParams.some((p) => p.required === true);
      fields.push(`  /** Query string parameters. */\n  query${anyRequired ? '' : '?'}: {\n${inner}\n  };`);
    }

    if (op.requestSchema !== null) {
      fields.push(
        `  /** Request body, sent as \`${op.requestMediaType}\`. */\n` +
          `  body: ${renderType(op.requestSchema, `${where}/requestBody`, '  ')};`,
      );
    }

    if (op.requiresIdempotencyKey) {
      fields.push(
        '  /**\n' +
          `   * Required \`${IDEMPOTENCY_HEADER}\`. Mint it once per intent and reuse the same\n` +
          '   * value on every retry: a new key is a new command, not a retry.\n' +
          '   */\n' +
          '  idempotencyKey: IdempotencyKey;',
      );
    }

    fields.push(
      '  /**\n' +
        `   * Optional \`${CORRELATION_HEADER}\`. The edge assigns one when the caller does not.\n` +
        '   */\n' +
        '  correlationId?: CorrelationId;',
    );

    if (op.extraHeaders.length > 0) {
      const inner = op.extraHeaders
        .map((p) => {
          const doc0 = jsdoc(p.description, '    ');
          const optional = p.required === true ? '' : '?';
          return `${doc0}    ${lit(p.name)}${optional}: ${renderType(p.schema, `${where}/header/${p.name}`, '    ')};`;
        })
        .join('\n');
      const anyRequired = op.extraHeaders.some((p) => p.required === true);
      fields.push(`  /** Additional declared request headers. */\n  headers${anyRequired ? '' : '?'}: {\n${inner}\n  };`);
    }

    out.push(`export type ${inputTypeName(op)} = {`);
    out.push(fields.join('\n'));
    out.push('};');
    out.push('');

    const resultType =
      op.responseSchema === null
        ? 'void'
        : renderType(op.responseSchema, `${where}/responses/${op.successStatuses[0]}`, '');
    out.push(
      `/** Success body of \`${op.operationId}\`` +
        (op.responseMediaType ? ` (\`${op.responseMediaType}\`, HTTP ${op.successStatuses.join('/')}).` : '.') +
        ' */',
    );
    out.push(`export type ${resultTypeName(op)} = ${resultType};`);
  }

  // Runtime descriptor table.
  out.push('');
  out.push('// ' + '-'.repeat(84));
  out.push('// Runtime descriptors');
  out.push('// ' + '-'.repeat(84));
  out.push('');
  out.push('/**');
  out.push(' * What the transport needs at runtime to execute an operation. Consumers read this');
  out.push(' * table; they never build a URL, a method or a header name by hand.');
  out.push(' */');
  out.push('export const OPERATIONS = {');
  for (const op of operations) {
    out.push(`  ${op.operationId}: {`);
    out.push(`    operationId: ${lit(op.operationId)},`);
    out.push(`    method: ${lit(op.method)},`);
    out.push(`    path: ${lit(op.path)},`);
    out.push(`    pathParams: [${op.pathParams.map((p) => lit(p.name)).join(', ')}],`);
    out.push(`    queryParams: [${op.queryParams.map((p) => lit(p.name)).join(', ')}],`);
    out.push(`    headerParams: [${op.extraHeaders.map((p) => lit(p.name)).join(', ')}],`);
    out.push(`    requiresIdempotencyKey: ${op.requiresIdempotencyKey ? 'true' : 'false'},`);
    out.push(`    requestMediaType: ${op.requestMediaType === null ? 'null' : lit(op.requestMediaType)},`);
    out.push(`    responseMediaType: ${op.responseMediaType === null ? 'null' : lit(op.responseMediaType)},`);
    out.push(`    successStatuses: [${op.successStatuses.join(', ')}],`);
    out.push(`    errorStatuses: [${op.errorStatuses.join(', ')}],`);
    out.push(`    tags: [${op.tags.map((t) => lit(t)).join(', ')}],`);
    out.push('  },');
  }
  out.push('} as const;');

  return `${out.join('\n')}\n`;
}

// --------------------------------------------------------------------------------------
// client.gen.ts
// --------------------------------------------------------------------------------------

function emitClient(meta, operations) {
  const out = [
    header(
      meta,
      'One typed function per contract operation. Each is a thin, generated binding onto\n' +
        ' * the hand-written transport in `../transport`, which is the only place in `web/`\n' +
        ' * where an HTTP request is actually made.',
    ),
  ];
  out.push('');
  out.push("import type { ApiResponse, RequestOptions } from '../transport';");
  out.push("import { request } from '../transport';");
  out.push('import type {');
  for (const op of operations) {
    out.push(`  ${inputTypeName(op)},`);
    out.push(`  ${resultTypeName(op)},`);
  }
  out.push("} from './operations.gen';");
  out.push("import { OPERATIONS } from './operations.gen';");

  for (const op of operations) {
    out.push('');
    const summary = op.summary ? `${op.summary}\n\n` : '';
    out.push(
      jsdoc(
        `${summary}\`${op.method} ${op.path}\`` +
          (op.requiresIdempotencyKey ? ' - a write; carries a required Idempotency-Key.' : '.'),
        '',
      ).trimEnd(),
    );
    out.push(`export function ${op.operationId}(`);
    out.push(`  input: ${inputTypeName(op)},`);
    out.push('  options?: RequestOptions,');
    out.push(`): Promise<ApiResponse<${resultTypeName(op)}>> {`);
    out.push(`  return request<${resultTypeName(op)}>(OPERATIONS.${op.operationId}, input, options);`);
    out.push('}');
  }

  out.push('');
  out.push('/**');
  out.push(' * The whole client as one object, for a consumer that would rather inject it than');
  out.push(' * import each function. The named exports above are the ordinary way in.');
  out.push(' */');
  out.push('export const apiClient = {');
  for (const op of operations) out.push(`  ${op.operationId},`);
  out.push('} as const;');

  return `${out.join('\n')}\n`;
}

// --------------------------------------------------------------------------------------
// index.ts
// --------------------------------------------------------------------------------------

function emitIndex(meta) {
  const out = [header(meta, 'Barrel for the generated client. Import from `@/shared/api` instead.')];
  out.push('');
  out.push("export * from './types.gen';");
  out.push("export * from './operations.gen';");
  out.push("export * from './client.gen';");
  return `${out.join('\n')}\n`;
}

// --------------------------------------------------------------------------------------
// driver
// --------------------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { check: false, input: DEFAULT_INPUT, out: DEFAULT_OUT, snapshot: DEFAULT_SNAPSHOT };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--check') args.check = true;
    else if (arg === '--input') args.input = resolve((argv[i += 1] ?? ''));
    else if (arg === '--out') args.out = resolve((argv[i += 1] ?? ''));
    else if (arg === '--snapshot') args.snapshot = resolve((argv[i += 1] ?? ''));
    else if (arg === '--no-snapshot') args.snapshot = null;
    else throw new Error(`unknown argument ${arg}`);
  }
  return args;
}

/** Generate every owned file from the document bytes. Pure: bytes in, files out. */
export function generate(documentBytes) {
  const text = documentBytes.toString('utf8');
  let doc;
  try {
    doc = JSON.parse(text);
  } catch (error) {
    throw new ContractDefect('#', `document is not valid JSON: ${error.message}`);
  }

  if (typeof doc.openapi !== 'string' || !doc.openapi.startsWith('3.1')) {
    throw new ContractDefect('#/openapi', `expected OpenAPI 3.1.x, found ${String(doc.openapi)}`);
  }

  const meta = {
    openapi: doc.openapi,
    title: doc.info?.title ?? 'untitled',
    version: doc.info?.version ?? '0.0.0',
    digest: sha256(documentBytes),
  };

  const operations = collectOperations(doc);

  return {
    meta,
    operations,
    files: {
      'types.gen.ts': emitTypes(doc, meta),
      'operations.gen.ts': emitOperations(doc, meta, operations),
      'client.gen.ts': emitClient(meta, operations),
      'index.ts': emitIndex(meta),
    },
  };
}

function main(argv) {
  const args = parseArgs(argv);

  if (!existsSync(args.input)) {
    console.error(`generate-api-client: input not found: ${args.input}`);
    return 2;
  }

  const bytes = readFileSync(args.input);
  const { meta, operations, files } = generate(bytes);

  if (args.check) {
    const problems = [];

    if (!existsSync(args.out)) {
      problems.push(`generated directory missing: ${args.out}`);
    } else {
      const present = readdirSync(args.out).sort(byCodeUnit);
      for (const extra of present) {
        if (!OWNED_FILES.includes(extra)) {
          problems.push(`unexpected file in generated directory: ${extra}`);
        }
      }
      for (const name of OWNED_FILES) {
        const target = join(args.out, name);
        if (!existsSync(target)) {
          problems.push(`missing generated file: ${name}`);
          continue;
        }
        const onDisk = readFileSync(target, 'utf8');
        if (onDisk !== files[name]) {
          problems.push(
            `drift in ${name}: committed sha256 ${sha256(Buffer.from(onDisk, 'utf8'))}, ` +
              `regenerated sha256 ${sha256(Buffer.from(files[name], 'utf8'))}`,
          );
        }
      }
    }

    if (args.snapshot !== null) {
      if (!existsSync(args.snapshot)) {
        problems.push(`missing OpenAPI snapshot: ${args.snapshot}`);
      } else if (!readFileSync(args.snapshot).equals(bytes)) {
        problems.push(
          `OpenAPI snapshot differs from the contract: snapshot sha256 ` +
            `${sha256(readFileSync(args.snapshot))}, contract sha256 ${meta.digest}`,
        );
      }
    }

    if (problems.length > 0) {
      console.error('generate-api-client --check: FAILED');
      for (const problem of problems) console.error(`  - ${problem}`);
      console.error('Run `npm --prefix web run api:generate` and commit the result.');
      return 1;
    }

    console.log(
      `generate-api-client --check: OK - ${operations.length} operations, ` +
        `contract sha256 ${meta.digest}`,
    );
    return 0;
  }

  mkdirSync(args.out, { recursive: true });
  for (const name of OWNED_FILES) writeFileSync(join(args.out, name), files[name], 'utf8');

  if (args.snapshot !== null) {
    mkdirSync(dirname(args.snapshot), { recursive: true });
    writeFileSync(args.snapshot, bytes);
  }

  console.log(
    `generate-api-client: wrote ${OWNED_FILES.length} files, ${operations.length} operations, ` +
      `contract sha256 ${meta.digest}`,
  );
  return 0;
}

const invokedDirectly =
  process.argv[1] !== undefined && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));

if (invokedDirectly) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (error) {
    console.error(`generate-api-client: ${error.message}`);
    process.exit(2);
  }
}
