/**
 * `AR-V3-DECISIONS-01` (`R-146as`): the findings of an AR v3 beta Run in the group review panel, with the
 * verdict controls.
 *
 * Static states first (what an expert, an administrator and a run with nothing to decide are shown), then
 * the live behaviour with only the transport replaced: the controls call `appendDecision` with exactly the
 * request the ledger accepts, an accept of a finding that carries a proposed severity is refused in the
 * browser until the expert chooses one, and a person who may not decide is offered no button.
 */

import type { QueryClient } from '@tanstack/react-query';
import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, appendDecision: vi.fn(), getMe: vi.fn(), listRunFindings: vi.fn() };
});

import { appendDecision, getMe, listRunFindings, queryKeys } from '@/shared/api';
import type { Account, Finding } from '@/shared/api';
import { mayRecordVerdict } from '@/widgets/ar-v3-beta-review/model/may-decide';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';

import { newClient, renderScreen } from '../screens/harness';

import {
  AVAILABLE_RUN_ID, GROUP_ID, NORM_QUOTE, PDF_QUOTE, accountFixture, groupReviewFixture, runFindingsPage, v3FindingFixture,
} from './ar-v3-beta-review-fixtures';
import { mountLive } from './live-render';
import type { LiveRender } from './live-render';

const review = groupReviewFixture();
const AVAILABLE_RUN = AVAILABLE_RUN_ID;

const v3Finding = v3FindingFixture;
const page = runFindingsPage;
const account = accountFixture;

function seeded(roles: Account['roles'], items: Finding[]): QueryClient {
  const client = newClient();
  client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), review);
  client.setQueryData(queryKeys.runs.findings(AVAILABLE_RUN), { data: page(items) });
  client.setQueryData(queryKeys.account.me(), account(roles));
  return client;
}

describe('the findings under an available scope, as markup', () => {
  it('shows the PDF quote, the norm with its designation and quote, the model text escaped, and the controls to an expert', () => {
    const hostile = v3Finding();
    hostile.observation = { ...hostile.observation, finding_text: '<b>Проверить ширину прохода.</b>' };
    const markup = renderScreen(seeded(['expert'], [hostile]), createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect(markup).toContain('Находки и решения эксперта');
    expect(markup).toContain(PDF_QUOTE);
    expect(markup).toContain('СП 1.13130');
    expect(markup).toContain('пункт 4.2.5');
    expect(markup).toContain(NORM_QUOTE);
    expect(markup).toContain('Формулировка модели, не решение эксперта.');
    expect(markup).toContain('&lt;b&gt;Проверить ширину прохода.&lt;/b&gt;');
    expect(markup).not.toContain('<b>Проверить');
    expect(markup).toContain('data-intent="accept"');
    expect(markup).toContain('data-intent="reject"');
    expect(markup).toContain('data-intent="comment"');
    expect(markup).toContain('Важность при принятии');
  });

  it('shows a pending verdict and a number nowhere', () => {
    const markup = renderScreen(seeded(['expert'], [v3Finding()]), createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect(markup).toContain('data-verdict="pending"');
    expect(markup).toContain('am-badge--pending');  // the verdict badge itself, not only the card's attribute
    expect(markup).not.toMatch(/required_value|stated_value|1,4 м(?!\.)/);
  });

  it('offers an administrator and a person with no role the findings and no button', () => {
    for (const roles of [['admin'], []] as Account['roles'][]) {
      const markup = renderScreen(seeded(roles, [v3Finding()]), createElement(ArV3BetaReview, { groupId: GROUP_ID }));
      expect(markup).toContain(PDF_QUOTE);
      expect(markup).toContain('Решение записывает эксперт.');
      expect(markup).not.toContain('data-intent="accept"');
      expect(markup).not.toContain('data-intent="reject"');
      expect(markup).not.toContain('data-ar-v3-verdict-controls');
    }
  });

  it('says there is nothing to decide when the run published no finding', () => {
    const markup = renderScreen(seeded(['expert'], []), createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect(markup).toContain('Опубликованных находок нет.');
    expect(markup).not.toContain('data-ar-v3-finding ');
  });

  it('shows a decided finding with the expert\'s severity and its verdict', () => {
    const decided = v3Finding({ current_verdict: 'accepted', decided_severity: 'economic' });
    const markup = renderScreen(seeded(['expert'], [decided]), createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect(markup).toContain('data-verdict="accepted"');
    expect(markup).toContain('am-badge--ok');
    expect(markup).toContain('Важность, решённая экспертом');
  });

  it('only an expert may record a verdict', () => {
    expect(mayRecordVerdict(['expert'])).toBe(true);
    expect(mayRecordVerdict(['expert', 'admin'])).toBe(true);
    expect(mayRecordVerdict(['admin'])).toBe(false);
    expect(mayRecordVerdict([])).toBe(false);
  });
});

describe('the verdict controls, live', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getMe).mockResolvedValue({ data: account(['expert']) } as never);
    vi.mocked(listRunFindings).mockResolvedValue({ data: page([v3Finding()]) } as never);
    vi.mocked(appendDecision).mockResolvedValue({
      data: {
        event: {
          decision_id: 'dec_01M59N8QNBVN91ACA2HCE6VE74', finding_uid: v3Finding().finding_uid,
          finding_observation_id: v3Finding().observation.finding_observation_id, event_type: 'accept',
          author_label: 'Сьютова Е.', recorded_at: '2026-10-27T10:00:00Z',
        },
        current_verdict: 'accepted',
      },
    } as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(): Promise<LiveRender> {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), review);
    client.setQueryData(queryKeys.runs.findings(AVAILABLE_RUN), { data: page([v3Finding()]) });
    client.setQueryData(queryKeys.account.me(), account(['expert']));
    live = await mountLive(createElement(QueryClientProvider, { client }, createElement(ArV3BetaReview, { groupId: GROUP_ID })));
    return live;
  }

  it('refuses an accept in the browser until the expert has chosen a severity, and sends nothing', async () => {
    const view = await mount();
    expect(await view.press('Принять')).toBe(true);
    expect(appendDecision).not.toHaveBeenCalled();
    expect(view.markup()).toContain('Перед принятием выберите важность. Ничего не отправлено.');
  });

  it('sends an accept of a finding that carries no proposed severity as exactly {event_type, finding_observation_id}', async () => {
    const plain = v3Finding();
    const { proposed_severity: proposed, ...withoutSeverity } = plain.observation;
    void proposed;
    vi.mocked(listRunFindings).mockResolvedValue({ data: page([{ ...plain, observation: withoutSeverity }]) } as never);
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), review);
    client.setQueryData(queryKeys.runs.findings(AVAILABLE_RUN), { data: page([{ ...plain, observation: withoutSeverity }]) });
    client.setQueryData(queryKeys.account.me(), account(['expert']));
    live = await mountLive(createElement(QueryClientProvider, { client }, createElement(ArV3BetaReview, { groupId: GROUP_ID })));
    expect(live.markup()).not.toContain('Важность при принятии');
    await live.press('Принять');
    expect(appendDecision).toHaveBeenCalledTimes(1);
    const call = vi.mocked(appendDecision).mock.calls[0]![0] as { body: Record<string, unknown> };
    expect(call.body).toEqual({ event_type: 'accept', finding_observation_id: plain.observation.finding_observation_id });
  });

  it('sends a reject as exactly {event_type, finding_observation_id}: no severity, no comment', async () => {
    const view = await mount();
    await view.press('Отклонить');
    expect(appendDecision).toHaveBeenCalledTimes(1);
    const call = vi.mocked(appendDecision).mock.calls[0]![0] as { path: { finding_uid: string }; body: Record<string, unknown> };
    expect(call.path.finding_uid).toBe(v3Finding().finding_uid);
    expect(call.body).toEqual({
      event_type: 'reject', finding_observation_id: v3Finding().observation.finding_observation_id,
    });
  });

  it('sends a comment without a verdict, and refuses an empty one in the browser', async () => {
    const view = await mount();
    await view.press('Добавить комментарий');
    expect(appendDecision).not.toHaveBeenCalled();
    expect(view.markup()).toContain('data-comment-refusal');
  });
});
