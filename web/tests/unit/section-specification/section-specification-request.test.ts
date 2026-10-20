/**
 * What «Оптимизация разделов» asks the server for (`W63-SECTION-FORM7-01`): the section in the
 * path, the page in the query, and a project or a search only when the expert chose one — an
 * empty filter is not sent, because an absent filter and an empty one are different requests.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, getSectionSpecification: vi.fn() };
});

import { getSectionSpecification } from '@/shared/api';
import { SECTION_ROW_LIMIT, sectionSpecificationQueryOptions } from '@/entities/section-specification';

import { SECTION_PROJECT_A, sectionAnswer } from './fixtures';

const read = vi.mocked(getSectionSpecification);

beforeEach(() => {
  read.mockReset();
  read.mockResolvedValue({ data: sectionAnswer() } as never);
});

describe('getSectionSpecification as the screen sends it', () => {
  it('sends the section and the first page, and nothing else, for an unfiltered read', async () => {
    const answer = await sectionSpecificationQueryOptions({
      sectionCode: 'AR', projectUid: null, query: '', offset: 0,
    }).queryFn();
    expect(answer).toEqual(sectionAnswer());
    expect(read).toHaveBeenCalledTimes(1);
    expect(read.mock.calls[0]?.[0]).toEqual({
      path: { section_code: 'AR' },
      query: { offset: 0, limit: SECTION_ROW_LIMIT },
    });
  });

  it('sends a chosen project and a trimmed search, and the page asked for', async () => {
    await sectionSpecificationQueryOptions({
      sectionCode: 'KJ', projectUid: SECTION_PROJECT_A as never, query: '  щит  ', offset: 100,
    }).queryFn();
    expect(read.mock.calls[0]?.[0]).toEqual({
      path: { section_code: 'KJ' },
      query: { offset: 100, limit: SECTION_ROW_LIMIT, project_uid: SECTION_PROJECT_A, q: 'щит' },
    });
  });

  it('does not send a blank search', async () => {
    await sectionSpecificationQueryOptions({
      sectionCode: 'AR', projectUid: SECTION_PROJECT_A as never, query: '   ', offset: 0,
    }).queryFn();
    expect(read.mock.calls[0]?.[0]).toEqual({
      path: { section_code: 'AR' },
      query: { offset: 0, limit: SECTION_ROW_LIMIT, project_uid: SECTION_PROJECT_A },
    });
  });
});
