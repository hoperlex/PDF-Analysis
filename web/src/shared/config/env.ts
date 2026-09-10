/**
 * Runtime configuration read from the environment.
 *
 * Two rules hold here and are the reason this module exists at all:
 *
 * 1. **No localhost default.** A missing API base URL fails loudly the first time
 *    something asks for it. A default would let a build quietly point at a developer's
 *    laptop and look healthy while talking to nothing.
 * 2. **Nothing secret.** The web tier holds an API base URL and a cosmetic instance
 *    label. It never holds an S3 endpoint, an access key, a bucket name or a database
 *    URL — `NEXT_PUBLIC_*` values are compiled into the browser bundle, so anything
 *    placed here is public by construction.
 *
 * The lookups are deliberately lazy. Reading them at module scope would make an
 * unconfigured environment a build failure rather than a startup failure, and the build
 * runs in places that legitimately have no API to point at.
 */

/** Raised when required configuration is absent. Never retried, never defaulted. */
export class MissingConfigurationError extends Error {
  readonly variable: string;

  constructor(variable: string, hint: string) {
    super(`Missing required configuration \`${variable}\`. ${hint}`);
    this.name = 'MissingConfigurationError';
    this.variable = variable;
  }
}

const API_BASE_URL_VARIABLE = 'NEXT_PUBLIC_API_BASE_URL';

/**
 * The versioned API base path or absolute origin, with any trailing slash removed.
 *
 * @throws {MissingConfigurationError} when the variable is unset or blank.
 */
export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (raw === undefined || raw.trim().length === 0) {
    throw new MissingConfigurationError(
      API_BASE_URL_VARIABLE,
      'Set it in web/.env.local (see web/.env.example). There is no localhost default: ' +
        'a silent one would let this app appear configured while talking to nothing.',
    );
  }
  return raw.trim().replace(/\/+$/, '');
}

/** True when the API base URL is configured. For a diagnostic screen, not for a fallback. */
export function hasApiBaseUrl(): boolean {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  return raw !== undefined && raw.trim().length > 0;
}

/**
 * A cosmetic label distinguishing two local instances in the shell header. Authorizes
 * nothing and is safe to omit.
 */
export function getInstanceLabel(): string | null {
  const raw = process.env.NEXT_PUBLIC_INSTANCE_LABEL;
  return raw === undefined || raw.trim().length === 0 ? null : raw.trim();
}
