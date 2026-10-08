/** Read the web image currently served by this origin. This is not an API operation. */

import { getWebBuildId } from '@/shared/config';

export class VersionCheckError extends Error {
  constructor(readonly status: number | null) {
    super('Не удалось проверить обновление приложения.');
    this.name = 'VersionCheckError';
  }
}

export function shouldShowUpdate(current: string | null, available: string | null, later: string | null): boolean {
  return current !== null && available !== null && current !== available && later !== available;
}

export async function checkWebVersion(
  request: typeof fetch = globalThis.fetch,
): Promise<{ current: string; available: string; changed: boolean }> {
  const current = getWebBuildId();
  let answer: Response;
  try {
    answer = await request('/bff/version', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
  } catch {
    throw new VersionCheckError(null);
  }
  if (!answer.ok) throw new VersionCheckError(answer.status);
  let body: unknown;
  try {
    body = await answer.json();
  } catch {
    throw new VersionCheckError(answer.status);
  }
  if (
    typeof body !== 'object' || body === null ||
    !('web_build_id' in body) || typeof body.web_build_id !== 'string' ||
    body.web_build_id.length === 0
  ) throw new VersionCheckError(answer.status);
  return { current, available: body.web_build_id, changed: current !== body.web_build_id };
}
