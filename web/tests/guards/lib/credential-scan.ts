/**
 * Pure scanner for the one property that cannot be repaired after the fact: **the
 * deployment credential is not in the browser bundle.**
 *
 * Pure for the same reason as `source-scan.ts`: the guard runs it over the real `web/src`
 * tree and over in-memory fixtures that break every rule, so it is shown to fire rather
 * than assumed to. A guard that only ever ran against a clean tree would be green whether
 * or not it worked.
 *
 * The rules encode Next's actual substitution rule, not a habit. Next replaces
 * `process.env.X` in client code only when `X` begins `NEXT_PUBLIC_`. So the credential is
 * out of the bundle if, and only if:
 *
 *   1. it is never read through a `NEXT_PUBLIC_` name;
 *   2. the module that does read it is not reachable from client code.
 *
 * Rule 2 is enforced structurally rather than by tracing the whole graph: exactly one
 * module reads the names, nothing re-exports it from a barrel a client imports, and the
 * only importers are route handlers under `src/app/bff/`.
 */

export interface ScannedFile {
  /** A repo-relative POSIX path. */
  readonly path: string;
  readonly text: string;
}

export interface CredentialViolation {
  readonly path: string;
  readonly rule: string;
  readonly detail: string;
}

/** The server-only names, restated here so the guard does not share the subject's copy. */
export const EXPECTED_SERVER_ONLY_NAMES = [
  'AUDITMANAGER_API_UPSTREAM',
  'AUDITMANAGER_API_TOKEN',
] as const;

/** The only module allowed to name them. */
export const CREDENTIAL_READER = 'web/src/shared/config/server-env.ts';

/** The only prefix allowed to import that module. */
export const CREDENTIAL_IMPORTER_PREFIX = 'web/src/app/bff/';

/** A `NEXT_PUBLIC_*` name carrying any of these reads as a secret, and none may exist. */
const SECRET_WORDS = ['TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL', 'KEY', 'AUTH'];

const NEXT_PUBLIC_NAME = /NEXT_PUBLIC_[A-Z0-9_]+/g;
const SERVER_ENV_IMPORT = /from\s+['"](?:@\/shared\/config\/server-env|\.\/server-env|\.\.\/config\/server-env)['"]/;

export const CREDENTIAL_RULE_IDS = [
  'public-secret-name',
  'credential-read-outside-reader',
  'credential-reader-reexported',
  'credential-reader-imported-outside-bff',
] as const;

/** Every violation in the supplied files, in file then rule order. */
export function scanCredentialExposure(files: readonly ScannedFile[]): CredentialViolation[] {
  const violations: CredentialViolation[] = [];
  const sorted = [...files].sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));

  for (const file of sorted) {
    // 1. No `NEXT_PUBLIC_` name may read as a secret, wherever it is written.
    for (const match of file.text.match(NEXT_PUBLIC_NAME) ?? []) {
      const tail = match.slice('NEXT_PUBLIC_'.length);
      const word = SECRET_WORDS.find((candidate) => tail.includes(candidate));
      if (word !== undefined) {
        violations.push({
          path: file.path,
          rule: 'public-secret-name',
          detail: `${match} is compiled into the browser bundle and its name says '${word}'.`,
        });
      }
    }

    // 2. The server-only names appear in exactly one module.
    if (file.path !== CREDENTIAL_READER) {
      for (const name of EXPECTED_SERVER_ONLY_NAMES) {
        // A bare mention in prose is not a read; `process.env.NAME` is.
        if (file.text.includes(`process.env.${name}`)) {
          violations.push({
            path: file.path,
            rule: 'credential-read-outside-reader',
            detail: `${name} is read here; only ${CREDENTIAL_READER} may read it.`,
          });
        }
      }
    }

    // 3. No barrel re-exports the reader. A barrel a client component imports would pull
    //    the module into the client graph even where the binding is never called.
    if (file.path.endsWith('/index.ts') && SERVER_ENV_IMPORT.test(file.text)) {
      violations.push({
        path: file.path,
        rule: 'credential-reader-reexported',
        detail: 'A barrel re-exports server-env, which puts it in the client import graph.',
      });
    }

    // 4. Only the BFF route handlers import it.
    if (
      file.path !== CREDENTIAL_READER &&
      !file.path.endsWith('/index.ts') &&
      SERVER_ENV_IMPORT.test(file.text) &&
      !file.path.startsWith(CREDENTIAL_IMPORTER_PREFIX)
    ) {
      violations.push({
        path: file.path,
        rule: 'credential-reader-imported-outside-bff',
        detail: `server-env is imported outside ${CREDENTIAL_IMPORTER_PREFIX}.`,
      });
    }
  }

  return violations;
}
