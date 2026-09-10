/**
 * Textual boundary scanner, as a pure function over `{ path, text }` pairs.
 *
 * ESLint already carries these rules, but ESLint can be silenced with a comment and does
 * not run in the build. This scanner is the second, dumber check: it reads the source as
 * text and does not care what a disable comment says.
 *
 * Pure on purpose, for the same reason as the version detector: the guard runs it against
 * the real tree and against fixtures that violate every rule, so the scanner is shown to
 * fire rather than assumed to.
 */

export interface SourceFile {
  /** A repo-relative POSIX path — the scanner decides scope from it. */
  readonly path: string;
  readonly text: string;
}

export interface BoundaryViolation {
  readonly path: string;
  readonly line: number;
  readonly rule: string;
  readonly excerpt: string;
}

interface Rule {
  readonly id: string;
  readonly pattern: RegExp;
  /** Paths allowed to match. A file whose path contains one of these is exempt. */
  readonly allowedIn: readonly string[];
  readonly why: string;
}

const RULES: readonly Rule[] = [
  {
    id: 'raw-http',
    // `fetch(` as a call, `new XMLHttpRequest`, `EventSource`, `sendBeacon`.
    pattern: /(?:^|[^.\w])fetch\s*\(|XMLHttpRequest|new\s+EventSource|sendBeacon\s*\(/,
    allowedIn: ['web/src/shared/api/'],
    why: 'HTTP lives only in src/shared/api. Import the generated client.',
  },
  {
    id: 'http-library',
    pattern: /from\s+['"](?:axios|got|ky|node-fetch|superagent)['"]|require\(['"](?:axios|got|ky)['"]\)/,
    allowedIn: [],
    why: 'No HTTP library. The generated client and one fetch are the whole transport.',
  },
  {
    id: 'environment-read',
    pattern: /process\.env/,
    allowedIn: ['web/src/shared/config/'],
    why: 'Environment is read only in src/shared/config, so a localhost default has one place to not exist.',
  },
  {
    id: 'storage-address',
    // The contract forbids these in any response; they must not appear in the client either.
    pattern: /\b(?:object_key|s3_key|bucket_name|presigned|AWS_SECRET|AWS_ACCESS_KEY)\b/,
    allowedIn: [],
    why: 'An object key, bucket name or credential never enters the web tier.',
  },
];

function exempt(rule: Rule, path: string): boolean {
  return rule.allowedIn.some((prefix) => path.includes(prefix));
}

/** Every boundary violation in the supplied files, in file then line order. */
export function scanBoundaries(files: readonly SourceFile[]): BoundaryViolation[] {
  const violations: BoundaryViolation[] = [];
  for (const file of [...files].sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0))) {
    const lines = file.text.split('\n');
    for (const rule of RULES) {
      if (exempt(rule, file.path)) continue;
      lines.forEach((line, index) => {
        // A comment mentioning the rule is not a violation of it. This is why the
        // scanner strips line comments before matching rather than after.
        const code = line.replace(/\/\/.*$/, '').replace(/^\s*\*.*$/, '');
        if (rule.pattern.test(code)) {
          violations.push({
            path: file.path,
            line: index + 1,
            rule: rule.id,
            excerpt: line.trim().slice(0, 120),
          });
        }
      });
    }
  }
  return violations;
}

/** The rule ids this scanner knows, so a test can assert none was quietly dropped. */
export const BOUNDARY_RULE_IDS = RULES.map((rule) => rule.id);

export const BOUNDARY_RULE_REASONS: Readonly<Record<string, string>> = Object.fromEntries(
  RULES.map((rule) => [rule.id, rule.why]),
);
