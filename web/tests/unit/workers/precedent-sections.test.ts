/**
 * `PREC-WEB`: «Прецеденты и векторы» on the advanced page: the refusal labels by section, read-only apart from the way back (OFF).
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import type { PrecedentSettingList } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { WorkersAdvancedPage } from '@/_pages/workers';
import type { WorkersAdvancedPageProps } from '@/_pages/workers';
import { precedentKeys } from '@/entities/decision-memory';
import { PrecedentSectionsView } from '@/_pages/workers/ui/precedent-sections';
import { currentSectionEntries, sectionLabelStates, valueWithSectionOff } from '@/_pages/workers/model/precedent-sections';

import { newClient, renderScreen } from '../screens/harness';
import { render } from '../review/fixtures';

const DIGEST = 'ab'.repeat(32);
const list = (value: Record<string, unknown>): PrecedentSettingList => ({
  current: [{ setting_name: 'section_labels', revision: 2, value: value as Record<string, never>, actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', created_at: '2026-11-10T10:00:00Z' }],
  events: [],
});
const STATE = list({ AR: { enabled: true, report_sha256: DIGEST, analogous: 0.9 }, KR: { enabled: false }, PS: { enabled: true, report_sha256: 'cd'.repeat(32) } });

describe('reading section_labels', () => {
  it('reads each journalled section, the ones on first', () => {
    expect(sectionLabelStates(STATE).map((one) => [one.section, one.enabled, one.reportSha256 === null ? null : one.reportSha256.slice(0, 2), one.analogous])).toEqual([
      ['AR', true, 'ab', 0.9], ['PS', true, 'cd', null], ['KR', false, null, null],
    ]);
    expect(sectionLabelStates(undefined)).toEqual([]);
    expect(sectionLabelStates({ current: [], events: [] })).toEqual([]);
  });

  it('leaves out an entry the server would not accept, and reads a switch on with no report as off', () => {
    const odd = list({ AR: { enabled: true }, 'bad code': { enabled: true, report_sha256: DIGEST }, KR: { enabled: 'yes' }, PS: { enabled: true, report_sha256: 'short' }, OV: { enabled: true, report_sha256: DIGEST, analogous: 2 } });
    expect(currentSectionEntries(odd)).toEqual({});
  });

  it('writes the whole state with one section off and its report kept', () => {
    const next = valueWithSectionOff(STATE, 'AR');
    expect(next).toEqual({ AR: { enabled: false, report_sha256: DIGEST, analogous: 0.9 }, KR: { enabled: false }, PS: { enabled: true, report_sha256: 'cd'.repeat(32) } });
    // a section the journal has never named is written off, not left out and not on
    expect(valueWithSectionOff(STATE, 'GP').GP).toEqual({ enabled: false });
  });
});

describe('the view', () => {
  it('shows each section, its report digest and a way back for a section that is on, and says why there is no way to switch on', () => {
    const markup = render(createElement(PrecedentSectionsView, { sections: sectionLabelStates(STATE), pending: false, failure: null, onOff: () => {} }));
    expect(markup).toContain('data-precedent-sections="2"');
    expect(markup).toContain('data-precedent-section="AR"');
    expect(markup).toContain('отчёт abababab…ababab');
    expect(markup).toContain(`title="${DIGEST}"`);
    expect((markup.match(/data-precedent-section-off=/g) ?? []).length).toBe(2);
    expect(markup).not.toContain('data-precedent-section-off="KR"');
    expect(markup).toContain('data-precedent-enable-note');
    expect(markup).not.toContain('Включить</button>');
  });

  it('says that no section was ever switched on', () => {
    const markup = render(createElement(PrecedentSectionsView, { sections: [], pending: false, failure: null, onOff: () => {} }));
    expect(markup).toContain('data-precedent-sections-none');
    expect(markup).not.toContain('data-precedent-section-off');
  });
});

describe('on the advanced page', () => {
  function page(roles: readonly string[], seed: boolean): string {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', roles, login: 'админ' });
    if (seed) client.setQueryData(precedentKeys.settings(), STATE);
    return renderScreen(client, createElement(WorkersAdvancedPage as ComponentType<WorkersAdvancedPageProps>, { initialTab: 'precedents' }));
  }

  it('opens the section the address named and draws the sections for an administrator', () => {
    const markup = page(['admin'], true);
    const opened = [...markup.matchAll(/<details[^>]*data-advanced-section="([a-z]+)"[^>]*>/g)].filter((entry) => (entry[0] ?? '').includes(' open=""')).map((entry) => entry[1]);
    expect(opened).toEqual(['precedents']);
    expect(markup).toContain('Прецеденты и векторы');
    expect(markup).toContain('data-precedent-section="AR"');
  });

  it('draws nothing of it for an expert', () => {
    const markup = page(['expert'], true);
    expect(markup).not.toContain('data-advanced-section');
    expect(markup).not.toContain('data-precedent-section');
  });
});
