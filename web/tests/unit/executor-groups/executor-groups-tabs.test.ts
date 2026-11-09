/**
 * `EXEC2-WEB-GROUPS-01` — what «Группы» and «Правила» draw, and how «Назначения» behaves in each routing mode. Written under
 * `R-149d` and not run in EXEC-2; none of it needs PostgreSQL. `HOSTS-WEB-01` moved the six tabs to the advanced page,
 * `/workers/advanced`, where each is a section that mounts only when opened; the tab tests are in
 * `tests/unit/workers/workers-tabs.test.ts`.
 *
 * «Назначения» is the legacy Primary/Standby editor while the routing mode is `legacy` and the history of the routes once rules
 * are in force (ADR-0026 decision 17), so the page tests below hold that it is an editor in the one mode and history in the other.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import type { Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ADVANCED_SECTIONS, WorkersAdvancedPage } from '@/_pages/workers';
import type { AdvancedSection, WorkersAdvancedPageProps } from '@/_pages/workers';

import { newClient, renderScreen } from '../screens/harness';
import { MAIN_GROUP, ROUTED_GROUP, ruleOf, seedGroups, seedRules } from './executor-groups-fixtures';

describe('the advanced page', () => {
  function page(props: WorkersAdvancedPageProps, roles: Role[] = ['admin'], mode: 'legacy' | 'rules' | null = null): string {
    const client = newClient();
    seedGroups(client);
    client.setQueryData(queryKeys.account.me(), { roles });
    if (mode !== null) seedRules(client, mode, mode === 'rules' ? [ruleOf('text_analysis', ROUTED_GROUP, 1)] : []);
    return renderScreen(client, createElement(WorkersAdvancedPage as ComponentType<WorkersAdvancedPageProps>, props));
  }

  const tab = (name: AdvancedSection): WorkersAdvancedPageProps => ({ initialTab: name });

  it('draws «Группы» and nothing of the other tabs', () => {
    const markup = page(tab('groups'));
    expect(markup).toContain('data-advanced-section="groups"');
    expect(markup).toContain('data-executor-groups');
    expect(markup).not.toContain('data-executor-rules');
    expect(markup).not.toContain('data-executor-routes');
    expect(markup).not.toContain('data-executor-connections');
  });

  it('draws «Правила» with the legacy routes inside it while the mode is the legacy one', () => {
    const markup = page(tab('rules'), ['admin'], 'legacy');
    expect(markup).toContain('data-advanced-section="rules"');
    expect(markup).toContain('data-executor-rules');
    expect(markup).toContain('data-rules-legacy-routes');
    // The routes there are history: their summaries, never their editors.
    expect(markup).toContain('data-executor-routes');
    expect(markup).not.toContain('data-executor-route-form');
    expect(markup).not.toContain('data-executor-routes-history');
  });

  it('draws «Назначения» as the editor under the legacy mode and as history under rules', () => {
    const legacy = page(tab('routes'), ['admin'], 'legacy');
    expect(legacy).toContain('data-executor-route-form');
    expect(legacy).not.toContain('data-executor-routes-history');

    const ruled = page(tab('routes'), ['admin'], 'rules');
    expect(ruled).toContain('data-executor-routes-history');
    expect(ruled).toContain('data-executor-route="text_analysis"');
    expect(ruled).not.toContain('data-executor-route-form');
    expect(ruled).not.toContain('Сохранить назначение');
  });

  it('keeps «Назначения» an editor while the mode has not been read: the server enforces the mode', () => {
    const markup = page(tab('routes'), ['admin'], null);
    expect(markup).toContain('data-executor-route-form');
    expect(markup).not.toContain('data-executor-routes-history');
  });

  it('opens exactly the section the address named, and mounts nothing of the closed ones', () => {
    for (const name of ADVANCED_SECTIONS) {
      const markup = page(tab(name), ['admin'], 'legacy');
      expect(markup.match(/<details[^>]*open=""/g), name).toHaveLength(1);
      expect(markup).toMatch(new RegExp(`<details[^>]*open=""[^>]*data-advanced-section="${name}"|<details[^>]*data-advanced-section="${name}"[^>]*open=""`));
    }
  });

  it('shows the groups to every role and the controls to an administrator only', () => {
    const group = MAIN_GROUP.display_name;
    const admin = page(tab('groups'), ['admin']);
    const reader = page(tab('groups'), ['expert']);
    expect(admin).toContain(group);
    expect(reader).toContain(group);
    expect(admin).toContain('data-executor-group-create');
    expect(reader).not.toContain('data-executor-group-create');
    expect(reader).not.toContain('data-group-revise');
  });
});
