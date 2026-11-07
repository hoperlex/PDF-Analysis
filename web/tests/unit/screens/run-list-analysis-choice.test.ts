/**
 * `AR-V3-OPT-IN` (design 4.3, 4.6 and 4.8), rendered: the run list offers the choice of AR v3 on ONE answer of the server
 * and on no other, and where it does not offer it the page is today's page.
 *
 * Replaces the pin of 2026-10-30 («the run list mounts no six-check control, whatever the pack and the list do»), which
 * was true while v3 was reachable by API only. The new pin is its precise successor:
 *
 *   - the choice is drawn on the start form of an АР version when `getArV3BetaPackStatus` reads `installed` AND
 *     `start_allowed: true` -- that answer and no other (loading, a failed read, no pack, a pack that does not allow a
 *     start, a pack of an older server that does not say, a contract fault);
 *   - the standard analysis is selected whenever the form opens;
 *   - where the choice is not drawn the markup is exactly the ordinary start's (no radio, no sentence, no link, no word
 *     about v3), and a version that is not АР, or a comparison PDF, never even asks the server;
 *   - each row says which analysis produced the run: a v3 run always, a standard run only where both are on offer.
 *
 * Each pin has its planted control: the predicate that finds the choice in markup is shown to find it where it is, so a
 * grid of «absent» is a grid that could have been «present».
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { ArV3BetaPackStatus, RunStatus } from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';

import { NOT_INSTALLED_PACK, installedPackFixture, withoutMember } from '../analysis-settings/ar-v3-beta-pack-fixtures';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen, seedError } from './harness';

type Client = ReturnType<typeof newClient>;

const PACK = queryKeys.runs.arV3PackStatus();
const GROUP = 'arg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const STANDARD_RUN = runStatus({ run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as NonNullable<RunStatus['run_id']>, analysis_kind: 'standard' });
const V3_RUN = runStatus({
  run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8C' as NonNullable<RunStatus['run_id']>,
  analysis_kind: 'ar_v3_beta',
  analysis_profile_id: 'ap_01M5M28ZCDD8VPSP1BTAEW92YE' as NonNullable<RunStatus['analysis_profile_id']>,
  ar_v3_group_id: GROUP as NonNullable<RunStatus['ar_v3_group_id']>,
  ar_v3_scope_id: 'F1',
});

/** The answer on which the choice is offered, and the answers on which it is not. */
const ALLOWED: ArV3BetaPackStatus = installedPackFixture({ start_allowed: true });
const NOT_ALLOWED: ReadonlyArray<readonly [string, (client: Client) => void]> = [
  ['loading', () => {}],
  [
    'a failed read',
    (client) => seedError(client, PACK, new ApiError(503, {
      contract_version: '1.39.0', error_code: 'dependency_unavailable', message: 'm',
      correlation_id: 'c', retryable: true,
    }, 'c')),
  ],
  ['not installed', (client) => client.setQueryData(PACK, NOT_INSTALLED_PACK)],
  ['installed, starts not allowed', (client) => client.setQueryData(PACK, installedPackFixture({ start_allowed: false }))],
  ['installed by a server that does not say', (client) => client.setQueryData(PACK, installedPackFixture())],
  ['an allowance that is not a boolean', (client) => client.setQueryData(PACK, { ...installedPackFixture(), start_allowed: 'true' })],
  ['an allowance that is null', (client) => client.setQueryData(PACK, { ...installedPackFixture(), start_allowed: null })],
  ['installed without a review', (client) => client.setQueryData(PACK, withoutMember({ ...ALLOWED }, 'review'))],
  ['an undeclared state', (client) => client.setQueryData(PACK, { state: 'withdrawn', start_allowed: true })],
  ['not installed, with an allowance', (client) => client.setQueryData(PACK, { state: 'not_installed', start_allowed: true })],
];

function listClient(runs: readonly RunStatus[]): Client {
  const client = newClient();
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
    items: runs, page: { next_cursor: null },
  });
  return client;
}

interface Where {
  readonly sectionCode?: 'AR' | 'KJ' | undefined;
  readonly uploadKind?: 'comparison_pdf' | undefined;
}

function list(client: Client, where: Where = { sectionCode: 'AR' }): string {
  return renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, ...where }));
}

/** The ids React mints for labels differ per render; the structure does not. */
const structure = (markup: string): string => markup.replace(/_[rR]_[A-Za-z0-9]+_/g, '_ID_');

/** The one predicate behind every «absent»: whether the markup offers the choice of an analysis, or says anything of v3. */
const offersChoice = (markup: string): boolean => markup.includes('data-analysis-choice');
const mentionsV3 = (markup: string): boolean => /АР v3|шесть проверок|шесть платных|data-ar-v3|data-analysis/i.test(markup);

const CHOICE_STANDARD = 'data-analysis-choice="standard"';
const STANDARD_CHECKED = /<input[^>]*data-analysis-choice-option="standard"[^>]*checked=""/;
const V3_CHECKED = /<input[^>]*data-analysis-choice-option="ar_v3_beta"[^>]*checked=""/;

describe('the choice of an analysis is drawn on one answer of the server and on no other', () => {
  for (const withRuns of [false, true]) {
    const runs = withRuns ? [STANDARD_RUN] : [];

    it(`${withRuns ? 'a list with runs' : 'an empty list'}, installed and allowed: the choice, standard selected, the ordinary form below`, () => {
      const client = listClient(runs);
      client.setQueryData(PACK, ALLOWED);
      const markup = list(client);
      expect(offersChoice(markup)).toBe(true);
      expect(markup).toContain(CHOICE_STANDARD);
      expect(markup).toMatch(STANDARD_CHECKED);
      expect(markup).not.toMatch(V3_CHECKED);
      expect(markup).toContain('>Анализ</p>');
      expect(markup).toContain('Стандартный (профиль АР из исходного приложения)');
      expect(markup).toContain('АР v3: шесть проверок по нормам (бета)');
      // The standard form is the one below: today's form, once, and no v3 control or sentence beside it.
      expect(markup).toContain('data-start-run-control="true"');
      expect(markup.match(/>Запустить прогон<\/button>/g)).toHaveLength(1);
      expect(markup).not.toContain('data-ar-v3-group-start');
      expect(markup).not.toContain('Запустить шесть проверок АР v3');
      expect(markup).not.toContain('data-ar-v3-choice-note');
    });

    for (const [name, seed] of NOT_ALLOWED) {
      it(`${withRuns ? 'a list with runs' : 'an empty list'}, ${name}: no choice, no word about v3, today's form`, () => {
        const client = listClient(runs);
        seed(client);
        const markup = list(client);
        expect(offersChoice(markup), name).toBe(false);
        expect(mentionsV3(markup), name).toBe(false);
        expect(markup).toContain('data-start-run-control="true"');
        expect(markup.match(/>Запустить прогон<\/button>/g)).toHaveLength(1);
      });
    }
  }

  it('the grid can see what it is looking for: the predicate finds the choice where it is, and the words where they are', () => {
    const client = listClient([]);
    client.setQueryData(PACK, ALLOWED);
    const drawn = list(client);
    expect(offersChoice(drawn)).toBe(true);
    expect(mentionsV3(drawn)).toBe(true);
    expect(offersChoice(drawn.replace(/data-analysis-choice/g, 'x'))).toBe(false);
  });

  it('where the choice is not offered the markup is the ordinary start’s, whatever the reason', () => {
    const baseline = structure(list(listClient([]), {}));
    for (const [name, seed] of NOT_ALLOWED) {
      const client = listClient([]);
      seed(client);
      expect(structure(list(client)), name).toBe(baseline);
    }
  });

  it('draws the same page for an АР version whatever the answer that does not allow a start', () => {
    const drawn = NOT_ALLOWED.map(([, seed]) => {
      const client = listClient([STANDARD_RUN]);
      seed(client);
      return structure(list(client));
    });
    for (const markup of drawn) expect(markup).toBe(drawn[0]);
  });
});

describe('a version that cannot take the choice never asks the server', () => {
  /** Whether anything used the status hook: the query exists in the cache once it was (a static render attaches no observer). */
  const asked = (client: Client): boolean => client.getQueryCache().find({ queryKey: PACK }) !== undefined;

  for (const [name, where] of [
    ['a version of another section', { sectionCode: 'KJ' }],
    ['a version with no confirmed section yet', {}],
    ['a comparison PDF of an АР version', { sectionCode: 'AR', uploadKind: 'comparison_pdf' }],
  ] as const) {
    it(`${name}: nothing asks the server, and the allowed answer changes nothing when it is there`, () => {
      for (const withRuns of [false, true]) {
        const client = listClient(withRuns ? [STANDARD_RUN] : []);
        list(client, where);
        expect(asked(client), `${name}: the list asks for the pack status`).toBe(false);
      }
      const allowed = listClient([]);
      allowed.setQueryData(PACK, ALLOWED);
      const markup = list(allowed, where);
      expect(offersChoice(markup)).toBe(false);
      expect(mentionsV3(markup)).toBe(false);
      expect(structure(markup)).toBe(structure(list(listClient([]), where)));
    });
  }

  it('the control: an АР version does ask, in the state with a list and in the empty one', () => {
    for (const withRuns of [false, true]) {
      const client = listClient(withRuns ? [STANDARD_RUN] : []);
      list(client);
      expect(asked(client), 'an АР version did not ask').toBe(true);
    }
  });
});

describe('every row says which analysis produced the run', () => {
  const rows = [STANDARD_RUN, V3_RUN];

  it('names the v3 run, with its scope, and links its group, whether or not a start is allowed', () => {
    for (const [name, seed] of [['allowed', (c: Client) => c.setQueryData(PACK, ALLOWED)], ...NOT_ALLOWED] as const) {
      const client = listClient(rows);
      seed(client);
      const markup = list(client);
      expect(markup, name).toContain('data-run-analysis="ar_v3_beta"');
      expect(markup, name).toContain('АР v3 (бета) · F1');
      expect(markup, name).toContain(`href="/analysis-settings?group_id=${GROUP}"`);
      // A v3 run has no canonical findings to review: only the standard run is offered «Разобрать».
      expect(markup.match(/>Разобрать</g), name).toHaveLength(1);
    }
  });

  it('names the standard run only where both analyses are on offer', () => {
    const allowed = listClient(rows);
    allowed.setQueryData(PACK, ALLOWED);
    expect(list(allowed)).toContain('data-run-analysis="standard"');
    expect(list(allowed)).toContain('>Стандартный<');
    for (const [name, seed] of NOT_ALLOWED) {
      const client = listClient(rows);
      seed(client);
      const markup = list(client);
      expect(markup, name).not.toContain('data-run-analysis="standard"');
      expect(markup, name).not.toContain('Стандартный');
    }
  });

  it('a list of standard runs on a deployment that allows no v3 is drawn exactly as it was', () => {
    const plain = listClient([runStatus()]);
    const same = listClient([STANDARD_RUN]);
    plain.setQueryData(PACK, NOT_INSTALLED_PACK);
    same.setQueryData(PACK, NOT_INSTALLED_PACK);
    const strip = (markup: string) => structure(markup).replace(/run_[0-9A-Z]{26}/g, 'run_X');
    expect(strip(list(same))).toBe(strip(list(plain)));
  });
});
