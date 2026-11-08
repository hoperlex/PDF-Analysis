/**
 * Lane N2 — what lane N1 left on «Исполнители» and «Настройки анализа»: one opt-in two-column form in the global layer,
 * the page header and tabs of «Исполнители», the scroll regions of «Настройки анализа», the connection wizard and the
 * runner-token panel, the focus ring of the cut-over proposal, and the menu's ✓ cell in the global layer (`D-396`).
 * Rendered in one static pass, and the CSS read as text where the assertion is about a rule.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { memberCandidates } from '@/entities/executor-group';
import { CreateConnectionForm, ReviseConnectionForm } from '@/features/manage-executor-connection';
import { GroupForm } from '@/features/manage-executor-group';
import { PresetForm } from '@/features/manage-analysis-preset';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderScreen } from '../screens/harness';
import { CONNECTION_CASES, ROUTED_GROUP } from '../executor-groups/executor-groups-fixtures';
import { PINNED, READY } from './executor-fixtures';

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
