/**
 * Types for the generator's one exported entry point, so the contract drift guard can
 * import it from TypeScript without the generator itself becoming a typed module.
 *
 * The generator is deliberately plain Node ESM with no dependencies: it has to run before
 * anything is installed and it must not be able to drag a transitive package into the
 * output. This declaration is the thin edge that keeps it importable from a test.
 */

export interface GeneratorMeta {
  readonly openapi: string;
  readonly title: string;
  readonly version: string;
  /** sha256 of the input document bytes. */
  readonly digest: string;
}

export interface GeneratedOperation {
  readonly operationId: string;
  readonly method: string;
  readonly path: string;
}

export interface GenerateResult {
  readonly meta: GeneratorMeta;
  readonly operations: readonly GeneratedOperation[];
  /** File name to file content, for every file the generator owns. */
  readonly files: Record<string, string>;
}

/**
 * Generate the whole client from the OpenAPI document bytes. Pure: the same bytes always
 * produce the same files.
 *
 * @throws when the document cannot generate — a missing `operationId`, a dangling `$ref`,
 * an unsupported media type. The generator reports the defect; it never repairs the
 * contract, which belongs to session A1.
 */
export function generate(documentBytes: Uint8Array): GenerateResult;
