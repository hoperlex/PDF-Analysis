/**
 * The floating-version detector, as a pure function.
 *
 * It is a pure function on purpose: the guard test runs it against the real
 * `web/package.json` **and** against mutated manifests it builds in memory. That second
 * call is what makes the guard evidence rather than decoration — a pinning check that has
 * never seen a caret has not been shown to detect one.
 */

/** An exact semantic version: `1.2.3`, or `1.2.3-rc.1`. Nothing else. */
export const EXACT_VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+(?:\.[0-9A-Za-z.]+)*)?$/;

/** `npm@10.9.8` — a package manager pinned to one exact version. */
export const EXACT_PACKAGE_MANAGER = /^[a-z]+@\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$/;

export interface PinViolation {
  /** Dotted location inside the manifest, e.g. `dependencies.next`. */
  readonly where: string;
  readonly value: string;
  readonly reason: string;
}

const DEPENDENCY_SECTIONS = [
  'dependencies',
  'devDependencies',
  'optionalDependencies',
  'peerDependencies',
] as const;

function classify(value: string): string | null {
  if (EXACT_VERSION.test(value)) return null;
  if (value.startsWith('^')) return 'caret range accepts any compatible minor or patch';
  if (value.startsWith('~')) return 'tilde range accepts any compatible patch';
  if (value === '*' || value === '' || value === 'x' || value === 'X') return 'wildcard accepts anything';
  if (/^(>=?|<=?)/.test(value)) return 'comparator range accepts more than one version';
  if (value.includes('||')) return 'alternation accepts more than one version';
  if (value.includes(' - ')) return 'hyphen range accepts more than one version';
  if (/^(latest|next|beta|alpha|canary)$/.test(value)) return `dist-tag '${value}' moves under you`;
  if (value.startsWith('npm:')) return 'alias may itself carry a range';
  if (/^(git|github|file|link|https?):/.test(value)) return 'non-registry source is not a pinned version';
  if (/\d+\.\d+\.x/i.test(value)) return 'x-range accepts any patch';
  return 'not an exact version';
}

/**
 * Every floating version in one `package.json`-shaped object.
 *
 * The foundation freeze forbids a floating version anywhere: the backend pins container
 * images by digest, so the frontend pinning by range would be the one soft edge in an
 * otherwise reproducible tree.
 */
export function findFloatingVersions(manifest: unknown): PinViolation[] {
  const violations: PinViolation[] = [];
  if (typeof manifest !== 'object' || manifest === null) {
    return [{ where: '<root>', value: String(manifest), reason: 'manifest is not an object' }];
  }
  const root = manifest as Record<string, unknown>;

  for (const section of DEPENDENCY_SECTIONS) {
    const entries = root[section];
    if (entries === undefined) continue;
    if (typeof entries !== 'object' || entries === null) {
      violations.push({ where: section, value: String(entries), reason: 'section is not an object' });
      continue;
    }
    for (const name of Object.keys(entries as Record<string, unknown>).sort()) {
      const value = (entries as Record<string, unknown>)[name];
      if (typeof value !== 'string') {
        violations.push({ where: `${section}.${name}`, value: String(value), reason: 'not a string' });
        continue;
      }
      const reason = classify(value);
      if (reason !== null) violations.push({ where: `${section}.${name}`, value, reason });
    }
  }

  const engines = root['engines'];
  if (typeof engines === 'object' && engines !== null) {
    for (const name of Object.keys(engines as Record<string, unknown>).sort()) {
      const value = (engines as Record<string, unknown>)[name];
      if (typeof value !== 'string' || !EXACT_VERSION.test(value)) {
        violations.push({
          where: `engines.${name}`,
          value: String(value),
          reason: 'engines must name one exact version, not a range',
        });
      }
    }
  }

  const packageManager = root['packageManager'];
  if (packageManager !== undefined) {
    if (typeof packageManager !== 'string' || !EXACT_PACKAGE_MANAGER.test(packageManager)) {
      violations.push({
        where: 'packageManager',
        value: String(packageManager),
        reason: 'packageManager must be <name>@<exact version>',
      });
    }
  }

  // `overrides` and `resolutions` can reintroduce a range behind the dependency list.
  for (const section of ['overrides', 'resolutions'] as const) {
    const entries = root[section];
    if (entries === undefined) continue;
    const walk = (node: unknown, path: string): void => {
      if (typeof node === 'string') {
        const reason = classify(node);
        if (reason !== null) violations.push({ where: path, value: node, reason });
        return;
      }
      if (typeof node === 'object' && node !== null) {
        for (const key of Object.keys(node as Record<string, unknown>).sort()) {
          walk((node as Record<string, unknown>)[key], `${path}.${key}`);
        }
      }
    };
    walk(entries, section);
  }

  return violations;
}

/** Every lockfile entry that does not pin a resolved artifact by integrity hash. */
export function findUnpinnedLockEntries(lock: unknown): PinViolation[] {
  const violations: PinViolation[] = [];
  if (typeof lock !== 'object' || lock === null) {
    return [{ where: '<root>', value: String(lock), reason: 'lockfile is not an object' }];
  }
  const packages = (lock as Record<string, unknown>)['packages'];
  if (typeof packages !== 'object' || packages === null) {
    return [{ where: 'packages', value: String(packages), reason: 'lockfile has no packages map' }];
  }

  for (const name of Object.keys(packages as Record<string, unknown>).sort()) {
    // The root entry ("") describes this project, not a downloaded artifact.
    if (name === '') continue;
    const entry = (packages as Record<string, unknown>)[name] as Record<string, unknown>;
    if (entry['link'] === true) continue;
    const version = entry['version'];
    if (typeof version !== 'string' || !EXACT_VERSION.test(version)) {
      violations.push({
        where: `packages.${name}.version`,
        value: String(version),
        reason: 'lockfile entry does not name one exact version',
      });
    }
    if (typeof entry['resolved'] !== 'string' || typeof entry['integrity'] !== 'string') {
      violations.push({
        where: `packages.${name}`,
        value: String(entry['resolved']),
        reason: 'lockfile entry has no resolved URL and integrity hash',
      });
    }
  }

  return violations;
}
