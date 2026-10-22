/**
 * What a connection's current revision is ready for (`EXEC-HTTP-01`, plan §2 and §4.1).
 *
 * A connection can serve model work only when its **current revision** has a finished probe
 * whose outcome is `ok` **on the current secret**: a revision that changes the address
 * leaves the key unreadable for it (the key opens only for the destination it was entered
 * for), and a key entered after the probe is a key nobody has tried. The screen offers a
 * connection as a route only under that rule and says which part fails; the server checks
 * the same rule again on every write.
 */

import type {
  ExecutorConnection,
  ExecutorProbe,
  ExecutorRevision,
  ExecutorSecretMetadata,
  ExecutorSecretPurpose,
} from '@/shared/api';

/** Which secrets a revision of this kind needs before a probe can be `ok`. */
export function requiredPurposes(
  connection: Pick<ExecutorConnection, 'kind'>,
  revision: Pick<ExecutorRevision, 'transport'> | undefined,
): readonly ExecutorSecretPurpose[] {
  if (connection.kind === 'http_api') {
    return revision?.transport === 'ssh_tunnel' ? ['api_key', 'ssh_private_key'] : ['api_key'];
  }
  if (connection.kind === 'ssh_command') return ['ssh_private_key'];
  return [];
}

/** The newest secret of a purpose, or `null`. The list is metadata only; no value is in it. */
export function secretOfPurpose(
  connection: Pick<ExecutorConnection, 'secrets'>,
  purpose: ExecutorSecretPurpose,
): ExecutorSecretMetadata | null {
  let newest: ExecutorSecretMetadata | null = null;
  for (const secret of connection.secrets) {
    if (secret.purpose !== purpose) continue;
    if (newest === null || secret.set_at > newest.set_at) newest = secret;
  }
  return newest;
}

/** A secret that exists but was entered for another destination than the current revision's. */
export function secretIsUnreadable(secret: ExecutorSecretMetadata | null): boolean {
  return secret !== null && !secret.bound_to_current_revision;
}

export type RouteBlocker =
  | 'archived'
  | 'no_revision'
  | 'kind_not_served'
  | 'secret_missing'
  | 'secret_unreadable'
  | 'not_probed'
  | 'probe_pending'
  | 'probe_failed';

export const ROUTE_BLOCKER_SENTENCES: Readonly<Record<RouteBlocker, string>> = {
  archived: 'подключение в архиве',
  no_revision: 'настройки ещё не заданы',
  kind_not_served: 'этот вид подключения пока не обслуживается',
  secret_missing: 'ключ ещё не введён',
  secret_unreadable: 'ключ введён для прежнего адреса, введите его заново',
  not_probed: 'текущие настройки ещё не проверены',
  probe_pending: 'проверка ещё не завершена',
  probe_failed: 'последняя проверка не прошла',
};

/**
 * Kinds whose probe and route the stand serves in this release: the HTTP API (`EXEC-HTTP-01`)
 * and the client that pulls tasks (`EXEC-PULL-01`, wired by `EXEC-CANDIDATE-2`).
 */
export function kindIsServed(kind: ExecutorConnection['kind']): boolean {
  return kind === 'http_api' || kind === 'pull';
}

/**
 * Why the connection cannot be routed, or `null` when it can: the current revision has a
 * finished `ok` probe taken on the connection's current secret, and no required secret is
 * bound to another destination.
 */
export function routeBlocker(
  connection: ExecutorConnection,
  revision: ExecutorRevision | undefined,
): RouteBlocker | null {
  if (connection.archived_at !== undefined) return 'archived';
  if (revision === undefined) return 'no_revision';
  if (!kindIsServed(connection.kind)) return 'kind_not_served';
  for (const purpose of requiredPurposes(connection, revision)) {
    const secret = secretOfPurpose(connection, purpose);
    if (secret === null) return 'secret_missing';
    if (secretIsUnreadable(secret)) return 'secret_unreadable';
  }
  const probe = revision.latest_probe;
  if (probe === undefined) return 'not_probed';
  if (probe.state !== 'finished') return 'probe_pending';
  if (probe.outcome !== 'ok') return 'probe_failed';
  if (!probeIsOnCurrentSecret(probe, connection, revision)) return 'not_probed';
  return null;
}

/** An `ok` probe counts only for the secret that is current now. */
export function probeIsOnCurrentSecret(
  probe: ExecutorProbe,
  connection: ExecutorConnection,
  revision: ExecutorRevision,
): boolean {
  const purposes = requiredPurposes(connection, revision);
  if (purposes.length === 0) return true;
  if (probe.secret_id === undefined) return false;
  const probed = probe.secret_id;
  return purposes.some((purpose) => secretOfPurpose(connection, purpose)?.secret_id === probed);
}

/** The current revision of a connection, read from its detail. */
export function currentRevision(
  connection: Pick<ExecutorConnection, 'current_revision_id'>,
  revisions: readonly ExecutorRevision[],
): ExecutorRevision | undefined {
  if (connection.current_revision_id === undefined) return undefined;
  return revisions.find((revision) => revision.revision_id === connection.current_revision_id);
}
