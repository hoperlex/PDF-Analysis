/**
 * Lane N2 — what lane N1 left on «Исполнители» and «Настройки анализа»: one opt-in two-column form in the global layer,
 * the page header and tabs of «Исполнители», the scroll regions of «Настройки анализа», the connection wizard and the
 * runner-token panel, the focus ring of the cut-over proposal, and the menu's ✓ cell in the global layer (`D-396`).
 * Rendered in one static pass, and the CSS read as text where the assertion is about a rule.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import { memberCandidates } from '@/entities/executor-group';
import { CreateConnectionForm, ReviseConnectionForm, RunnerTokenPanel } from '@/features/manage-executor-connection';
import {
  AgentSetup, ConnectWizard, EnrollmentCommandView, OpenRouterSetup, SshInstallForm,
} from '@/features/connect-remote-agent';
import { CutOverPreviewTable, GroupForm } from '@/features/manage-executor-group';
import { PresetForm } from '@/features/manage-analysis-preset';
import { AnalysisSettingsPage } from '@/_pages/analysis-settings';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';

import { WEB_ROOT } from '../../guards/lib/repo';
import { queryKeys } from '@/shared/api';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';

import { newClient, renderScreen } from '../screens/harness';
import { CONNECTION_CASES, PREVIEW, ROUTED_GROUP } from '../executor-groups/executor-groups-fixtures';
import { PINNED, PULL_BARE, PULL_ONLINE, READY } from './executor-fixtures';
import { issued } from './connect-remote-agent-fixtures';

const css = (path: string): string => readFileSync(join(WEB_ROOT, 'src', path), 'utf8');
const GLOBALS = css('app/globals.css');

/** The body of the first rule whose selector list is exactly `selector`, or `null`. */
function ruleBody(source: string, selector: string): string | null {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\>]/g, '\\$&');
  const match = new RegExp(`^${escaped}\\s*\\{([^}]*)\\}`, 'm').exec(source);
  return match === null ? null : (match[1] ?? '');
}

describe('item 1: one opt-in two-column form in the global layer', () => {
  it('declares the grid once, with the long fields and everything that is not a field on the whole row', () => {
    const grid = ruleBody(GLOBALS, '.am-form--two');
    expect(grid).toContain('grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr))');
    expect(grid).toContain('column-gap: var(--am-gap)');
    expect(grid).toContain('max-width: 52rem');
    expect(ruleBody(GLOBALS, '.am-form--two > *')).toContain('grid-column: 1 / -1');
    expect(ruleBody(GLOBALS, '.am-form--two > .am-form__field')).toContain('grid-column: auto');
    expect(ruleBody(GLOBALS, '.am-form--two > .am-form__field--wide')).toContain('grid-column: 1 / -1');
  });

  it('can fail: the plain form is not a grid of tracks, and a rule that is not there reads as null', () => {
    expect(ruleBody(GLOBALS, '.am-form')).not.toContain('auto-fit');
    expect(ruleBody(GLOBALS, '.am-form--three')).toBeNull();
  });

  it('puts the two connection forms on it, with the long fields marked wide and no module class left', () => {
    const create = renderScreen(newClient(), createElement(CreateConnectionForm, { pinnedModels: PINNED }));
    const revise = renderScreen(newClient(), createElement(ReviseConnectionForm, {
      connection: READY.connection, revision: READY.detail.revisions[0], pinnedModels: PINNED, holdsKey: true, onClose: () => {},
    }));
    expect(create).toMatch(/<form class="am-form am-form--two"[^>]*data-executor-create-form/);
    expect(revise).toMatch(/<form class="am-form am-form--two"[^>]*data-executor-revise-form/);
    expect(revise).toMatch(/class="am-form__field am-form__field--wide"/);
    expect(revise).not.toMatch(/class="[^"]*_wide_/);
    expect(revise).not.toMatch(/<form class="[^"]*_form_/);
  });

  it('puts the group form on it, both when it makes a group and when it revises one', () => {
    const candidates = memberCandidates(
      CONNECTION_CASES.map((one) => one.connection),
      new Map(CONNECTION_CASES.map((one) => [one.connection.connection_id, one.detail] as const)),
    );
    const made = renderScreen(newClient(), createElement(GroupForm, { candidates, pinnedModels: PINNED }));
    const revised = renderScreen(newClient(), createElement(GroupForm, { group: ROUTED_GROUP, candidates, pinnedModels: PINNED }));
    expect(made).toMatch(/<form class="am-form am-form--two"[^>]*data-group-form="create"/);
    expect(revised).toMatch(/<form class="am-form am-form--two"[^>]*data-group-form="revise"/);
    // The members are not a field: they take the whole row without a marker.
    expect(made).toMatch(/<div class="[^"]*members[^"]*"[^>]*data-group-members/);
    expect(made).not.toMatch(/data-group-members[^>]*am-form__field/);
  });

  it('leaves the preset form on its own grid: its tracks are 16 rem, and the global ones would widen its two fields', () => {
    const preset = renderScreen(newClient(), createElement(PresetForm, { choices: [] }));
    expect(preset).toMatch(/<form class="am-form [^"]*form[^"]*" data-preset-form="create"/);
    expect(preset).not.toContain('am-form--two');
    expect(css('features/manage-analysis-preset/ui/preset-form.module.css')).toContain('minmax(min(100%, 16rem), 1fr)');
  });
});

describe('item 2: «Исполнители» says its page in one sentence and keeps the rest one line away', () => {
  const page = (): string => renderScreen(newClient(), createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'connections' }));

  it('puts one sentence under the title and the long text in a closed disclosure', () => {
    const markup = page();
    const subtitle = /<p class="am-page__subtitle">([^<]*)<\/p>/.exec(markup)?.[1] ?? '';
    expect(subtitle).toBe('Обзор и очередь, подключения к моделям, процессы, группы, правила и назначения.');
    expect(subtitle.split(/[.!?]/).filter((part) => part.trim() !== '')).toHaveLength(1);
    const detail = /<details[^>]*data-workers-about[^>]*>[\s\S]*?<\/details>/.exec(markup)?.[0] ?? '';
    expect(detail).not.toMatch(/^<details[^>]*\sopen/);
    expect(detail).toContain('<summary>Что на экране и как обновляются данные</summary>');
    expect(detail).toContain('Обзор и список процессов обновляются автоматически, пока вкладка открыта');
    expect(detail).toContain('остальные данные — при возврате на вкладку, после команды и по запросу');
    expect(markup.indexOf('data-workers-about')).toBeLessThan(markup.indexOf('role="tablist"'));
  });

  it('can fail: the subtitle that was there held four sentences-worth of clauses, and a long one is not accepted', () => {
    const longer = 'Обзор исполнителей и очереди, подключения к моделям, процессы, которые выполняют прогоны, группы исполнителей, правила и назначения. Обзор и список процессов обновляются автоматически.';
    expect(longer.split(/[.!?]/).filter((part) => part.trim() !== '').length).toBeGreaterThan(1);
  });

  it('draws the tabs at the height of the strip’s controls, from tokens and not from pixels', () => {
    const tabs = css('_pages/workers/ui/workers-page.module.css');
    expect(ruleBody(tabs, '.tab')).toContain('padding: var(--am-gap-xs) var(--am-gap-md)');
    expect(ruleBody(tabs, '.tablist')).toContain('padding: var(--am-gap-xs)');
    expect(ruleBody(tabs, '.panel')).toContain('margin-top: var(--am-gap-sm)');
    expect(tabs).not.toMatch(/padding[^;]*\d+px/);
  });
});

describe('item 3: «Настройки анализа» — boxes that scroll sideways are reached by Tab, and a badge keeps its line', () => {
  const page = (): string => {
    const client = newClient();
    client.setQueryData(queryKeys.analysis.profiles(), {
      items: [{
        section_code: 'PB', section_name: 'Пожарная безопасность',
        profile: {
          analysis_profile_id: 'ap_01M5G4NZVKNZJYH722M0SXXP3X', prompt_bundle_id: 'pb_01M5G4NZVKHM9GP4EH22JACW2X',
          profile_version: '1.0.0', status: 'draft', prompt_bundle_sha256: 'a'.repeat(64), content_sha256: 'b'.repeat(64), source: null,
        },
      }],
    });
    return renderScreen(client, createElement(AnalysisSettingsPage, {}));
  };

  it('makes each of the four sections a named region with a tab stop', () => {
    const markup = page();
    for (const label of ['Состояние анализа АР v3', 'Пакет анализа АР v3', 'Разбор анализа АР v3', 'Пресеты запуска']) {
      expect(markup, label).toMatch(new RegExp(`<section class="[^"]*panel[^"]*" role="region" aria-label="${label}" tabindex="0"`));
    }
  });

  it('keeps the profile table in the one region it already had, and does not scroll its frame a second time', () => {
    const markup = page();
    expect(markup.match(/role="region"[^>]*tabindex="0"/g)).toHaveLength(5);
    expect(markup).toMatch(/<div class="[^"]*panel[^"]*flush[^"]*"><section[^>]*aria-labelledby="analysis-profiles-heading"/);
    expect(markup).not.toMatch(/<div class="[^"]*flush[^"]*"[^>]*tabindex/);
  });

  it('shows where focus is on a box, and lets the framing box of the table stay put', () => {
    const rules = css('_pages/analysis-settings/ui/analysis-settings-page.module.css');
    expect(ruleBody(rules, '.panel:focus-visible')).toContain('outline: 2px solid var(--am-accent)');
    expect(ruleBody(rules, '.flush')).toContain('overflow-x: visible');
    expect(ruleBody(rules, '.panel')).toContain('overflow-x: auto');
  });

  it('puts the state in a cell of its own whose badge does not wrap, even where the global badge does', () => {
    const items = [{
      section_code: 'PB' as const, section_name: 'Пожарная безопасность',
      profile: {
        analysis_profile_id: 'ap_01M5G4NZVKNZJYH722M0SXXP3X', prompt_bundle_id: 'pb_01M5G4NZVKHM9GP4EH22JACW2X',
        profile_version: '1.0.0', status: 'draft' as const, prompt_bundle_sha256: 'a'.repeat(64), content_sha256: 'b'.repeat(64), source: null,
      },
    }];
    const markup = renderScreen(newClient(), createElement(AnalysisProfileTable, { items }));
    expect(markup).toMatch(/<td class="[^"]*state[^"]*" data-profile-status="draft"><span class="am-badge /);
    const rules = css('widgets/analysis-profile-table/ui/analysis-profile-table.module.css');
    expect(ruleBody(rules, '.state :global(.am-badge)')).toContain('white-space: nowrap');
    // The global rule that wraps it is the reason the module has one: at a phone width it lets the words break.
    expect(GLOBALS).toMatch(/@media \(max-width: 590px\) \{\s*\.am-badge \{\s*white-space: normal/);
  });
});

describe('item 5: the cut-over proposal’s scrolling box shows where focus is', () => {
  it('keeps the box a named region with a tab stop, and gives it the standard outline', () => {
    const markup = renderScreen(newClient(), createElement(CutOverPreviewTable, {
      preview: PREVIEW, connections: CONNECTION_CASES.map((one) => one.connection),
    }));
    expect(markup).toMatch(/<div class="[^"]*previewWrap[^"]*" role="region" aria-label="Предложение перехода, таблица" tabindex="0">/);
    const rules = css('features/manage-executor-group/ui/cut-over-panel.module.css');
    expect(ruleBody(rules, '.previewWrap:focus-visible')).toContain('outline: 2px solid var(--am-accent)');
    expect(ruleBody(rules, '.previewWrap:focus-visible')).toContain('outline-offset: -2px');
    expect(ruleBody(rules, '.previewWrap')).toContain('overflow-x: auto');
  });
});

describe('item 6 (D-396): the menu’s ✓ cell is a rule of the shared menu', () => {
  const SWITCHER = css('widgets/project-switcher/ui/project-switcher.module.css');

  it('declares the cell beside the item’s rules in the global layer, and the item as a flex line', () => {
    const check = ruleBody(GLOBALS, '.am-menu__check');
    expect(check).toContain('flex: 0 0 1.2ch');
    expect(check).toContain('margin-left: auto');
    expect(check).toContain('color: var(--am-accent-strong)');
    expect(check).toContain('text-align: right');
    const item = ruleBody(GLOBALS, '.am-menu__item');
    expect(item).toContain('display: flex');
    expect(item).toContain('align-items: baseline');
    expect(item).toContain('gap: var(--am-gap-sm)');
    expect(GLOBALS.indexOf('.am-menu__check {')).toBeGreaterThan(GLOBALS.indexOf('.am-menu__item:focus-visible'));
  });

  it('leaves the selector’s module with what is the selector’s own: no cell rule, no flex layout of the items', () => {
    expect(SWITCHER).not.toContain('am-menu__check');
    const item = ruleBody(SWITCHER, '.switcher :global(.am-menu__item)');
    expect(item).toContain('white-space: pre-line');
    expect(item).not.toContain('display');
    expect(item).not.toContain('gap');
  });

  it('can fail: the rule is read as nothing where it does not exist', () => {
    expect(ruleBody(SWITCHER, '.switcher :global(.am-menu__check)')).toBeNull();
  });
});

describe('item 4: the connection wizard and the runner-token panel', () => {
  const wizard = (element: ReturnType<typeof createElement>): string => renderScreen(newClient(), element);
  const none = (): void => {};

  it('draws the two kinds of connection as the same card side by side where there is room', () => {
    const markup = wizard(createElement(ConnectWizard, { pinnedModels: PINNED }));
    expect(markup.match(/data-wizard-kind="(agent|api)"/g)).toHaveLength(2);
    const rules = css('features/connect-remote-agent/ui/connect-remote-agent.module.css');
    expect(ruleBody(rules, '.choices')).toContain('grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr))');
    expect(ruleBody(rules, '.choices')).toContain('gap: var(--am-gap-sm)');
    expect(ruleBody(rules, '.wizard')).toContain('gap: var(--am-gap-sm)');
    // One track that may shrink, or a two-column form inside the step is as wide as its widest content (768 px at 390).
    expect(ruleBody(rules, '.group')).toContain('grid-template-columns: minmax(0, 1fr)');
    expect(ruleBody(rules, '.wizard')).toContain('grid-template-columns: minmax(0, 1fr)');
  });

  it('puts the three forms of the wizard on the two-column form, with the SSH host on a row of its own', () => {
    const agent = wizard(createElement(AgentSetup, { pinnedModels: PINNED, onBack: none }));
    const api = wizard(createElement(OpenRouterSetup, { pinnedModels: PINNED, onBack: none }));
    const ssh = wizard(createElement(SshInstallForm, { pending: false, problem: null, failure: null, onSubmit: none, onBack: none }));
    expect(agent).toMatch(/<form class="am-form am-form--two [^"]*form[^"]*"[^>]*data-agent-identity-form/);
    expect(api).toMatch(/<form class="am-form am-form--two [^"]*form[^"]*"[^>]*data-openrouter-form/);
    expect(ssh).toMatch(/<form class="am-form am-form--two [^"]*form[^"]*"[^>]*data-agent-ssh-form/);
    const field = (id: string) => ssh.slice(ssh.lastIndexOf('<div', ssh.indexOf(`for="${id}"`)), ssh.indexOf(`for="${id}"`));
    expect(field('agent-ssh-host')).toContain('am-form__field--wide');
    expect(field('agent-ssh-port')).not.toContain('wide');
    expect(field('agent-ssh-user')).not.toContain('wide');
  });

  it('prints the fixed facts of the preset two pairs to a row, and keeps all four', () => {
    const markup = wizard(createElement(OpenRouterSetup, { pinnedModels: PINNED, onBack: none }));
    const facts = /<dl class="[^"]*facts[^"]*"[^>]*data-openrouter-fixed[^>]*>([\s\S]*?)<\/dl>/.exec(markup)?.[1] ?? '';
    expect(facts.match(/<dt>/g)).toHaveLength(4);
    const rules = css('features/connect-remote-agent/ui/connect-remote-agent.module.css');
    expect(ruleBody(rules, '.facts')).toContain('column-gap: var(--am-gap)');
    expect(ruleBody(rules, '.facts > dt,\n.facts > dd')).toContain('grid-column: auto');
  });

  it('folds what matters to few, with its words kept: the private-network hint and the package facts', () => {
    const ssh = wizard(createElement(SshInstallForm, { pending: false, problem: null, failure: null, onSubmit: none, onBack: none }));
    expect(ssh).toMatch(/<details class="[^"]*fold[^"]*"><summary>Если сервер в частной сети<\/summary><p class="am-form__hint" data-agent-private-range-hint>/);
    const command = wizard(createElement(EnrollmentCommandView, {
      issued: issued(READY.connection.connection_id), replaced: false, pending: false, failure: null, onNewCommand: none, onClose: none,
    }));
    expect(command).toMatch(/<details class="[^"]*fold[^"]*"><summary>Версия пакета и проверка<\/summary>/);
    expect(command).toContain('1.2.3');
    expect(command).toContain('Действует до');
    // The two buttons stand in one row, the new command first.
    const row = /<div class="am-form__row">((?:(?!<\/div>)[\s\S])*data-agent-command-new(?:(?!<\/div>)[\s\S])*)<\/div>/.exec(command)?.[1] ?? '';
    expect(row.indexOf('data-agent-command-new')).toBeGreaterThan(-1);
    expect(row.indexOf('data-agent-command-close')).toBeGreaterThan(row.indexOf('data-agent-command-new'));
  });

  const panel = (canManage: boolean, one = PULL_ONLINE): string => wizard(createElement(RunnerTokenPanel, {
    connection: one.connection, detail: one.detail, canManage, nowMs: Date.now(),
  }));

  it('draws a token as two lines: the name with its states and its one command, then the facts, with no line break in it', () => {
    const markup = panel(true);
    expect(markup).toMatch(/<ul class="[^"]*tokens[^"]*" aria-label="Выпущенные токены"/);
    const rows = [...markup.matchAll(/<li class="[^"]*token[^"]*" data-executor-runner-token=[\s\S]*?<\/li>/g)].map((match) => match[0]);
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      expect(row).not.toContain('<br');
      expect(row).toMatch(/<span class="[^"]*head[^"]*"><code>/);
      expect(row).toMatch(/<\/span><span class="[^"]*facts[^"]*">выпущен /);
    }
    const live = rows.find((row) => row.includes('data-executor-runner-token-state="active"')) ?? '';
    expect(live).toMatch(/<span class="[^"]*head[^"]*">[\s\S]*data-executor-runner-token-revoke[\s\S]*<\/span><span class="[^"]*facts/);
    expect(rows.filter((row) => row.includes('data-executor-runner-token-revoke'))).toHaveLength(1);
  });

  it('folds how the state is read, and shows no command to an expert', () => {
    const admin = panel(true);
    expect(admin).toMatch(/<details class="[^"]*fold[^"]*"><summary>Как читается состояние и что будет, если клиента нет<\/summary><p class="am-form__hint">Состояние читается при открытии страницы/);
    const expert = panel(false);
    expect(expert).toContain('Состояние читается при открытии страницы');
    expect(expert).not.toContain('data-executor-runner-token-revoke');
    expect(expert).not.toContain('data-executor-runner-issue');
  });

  it('keeps the words a token with no call shows', () => {
    expect(panel(true, PULL_BARE)).toContain('data-executor-runner-tokens="none"');
  });
});
