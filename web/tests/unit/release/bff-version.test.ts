import { afterEach, describe, expect, it, vi } from 'vitest';

import { subjectOf } from '@/app/bff/session/store';
import { GET } from '@/app/bff/version/route';

vi.mock('@/app/bff/session/store', () => ({
  readSessionId: () => 'session-id',
  subjectOf: vi.fn(),
}));

const oldBuild = process.env.NEXT_PUBLIC_WEB_BUILD_ID;
afterEach(() => {
  vi.mocked(subjectOf).mockReset();
  if (oldBuild === undefined) delete process.env.NEXT_PUBLIC_WEB_BUILD_ID;
  else process.env.NEXT_PUBLIC_WEB_BUILD_ID = oldBuild;
});

describe('/bff/version', () => {
  it('refuses a missing or incomplete session without disclosing a build', () => {
    const request = new Request('http://web.test/bff/version');
    vi.mocked(subjectOf).mockReturnValue(null);
    expect(GET(request).status).toBe(401);
    vi.mocked(subjectOf).mockReturnValue({ profileComplete: false, isDefaultCredential: false } as ReturnType<typeof subjectOf>);
    expect(GET(request).status).toBe(401);
  });

  it('returns the compiled build only to a complete session, without caching', async () => {
    process.env.NEXT_PUBLIC_WEB_BUILD_ID = 'w1234567890abcdef';
    vi.mocked(subjectOf).mockReturnValue({ profileComplete: true, isDefaultCredential: false } as ReturnType<typeof subjectOf>);
    const answer = GET(new Request('http://web.test/bff/version'));
    expect(answer.status).toBe(200);
    expect(answer.headers.get('Cache-Control')).toBe('no-store');
    expect(await answer.json()).toEqual({ web_build_id: 'w1234567890abcdef' });
  });
});
