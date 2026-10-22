/**
 * The destination a key is bound to, as far as the screen can say it before the server does
 * (`EXEC-HTTP-01`, plan §4.1).
 *
 * A key opens only for the route it was entered for: `transport|ssh_endpoint|origin`. A new
 * revision that changes any part leaves the current key unreadable, and the screen must say
 * so *before* the administrator saves, because the key is write-only and cannot be carried
 * over. This is a hint: the server recomputes the destination from the stored revision and
 * is the only judge.
 */

import type { ExecutorRevision } from '@/shared/api';

/** `scheme://host:port` in lower case with the default port made explicit, or `null`. */
export function normalisedOrigin(baseUrl: string | undefined): string | null {
  if (baseUrl === undefined) return null;
  const text = baseUrl.trim();
  if (!/^https?:\/\//i.test(text)) return null;
  try {
    const parsed = new URL(text);
    const port = parsed.port !== '' ? parsed.port : parsed.protocol === 'https:' ? '443' : '80';
    return `${parsed.protocol}//${parsed.hostname.toLowerCase()}:${port}`;
  } catch {
    return null;
  }
}

type DestinationSettings = Pick<ExecutorRevision, 'base_url' | 'transport' | 'ssh_host' | 'ssh_port'>;

/** The route of a revision as the key is bound to it. */
export function destinationOf(settings: DestinationSettings): string {
  const transport = settings.transport ?? '';
  const endpoint =
    settings.ssh_host !== undefined && settings.ssh_port !== undefined
      ? `${settings.ssh_host.trim().toLowerCase()}:${settings.ssh_port}`
      : '';
  return `${transport}|${transport === 'ssh_tunnel' ? endpoint : ''}|${normalisedOrigin(settings.base_url) ?? ''}`;
}

/** The SSH endpoint alone, for a command connection, whose key is bound to host and port. */
export function sshEndpointOf(settings: Pick<ExecutorRevision, 'ssh_host' | 'ssh_port'>): string {
  if (settings.ssh_host === undefined || settings.ssh_port === undefined) return '';
  return `${settings.ssh_host.trim().toLowerCase()}:${settings.ssh_port}`;
}

/**
 * True when saving `next` over `current` changes the route a key is bound to, so that the
 * key entered for `current` will not open for `next`.
 */
export function destinationChanged(
  kind: 'http_api' | 'ssh_command' | 'pull',
  current: DestinationSettings,
  next: DestinationSettings,
): boolean {
  if (kind === 'http_api') return destinationOf(current) !== destinationOf(next);
  if (kind === 'ssh_command') return sshEndpointOf(current) !== sshEndpointOf(next);
  return false;
}
