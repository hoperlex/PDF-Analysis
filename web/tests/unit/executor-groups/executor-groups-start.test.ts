/**
 * `EXEC2-WEB-GROUPS-01` — what a start request may carry: **exactly one selector** at most (ADR-0026
 * decisions 12 to 14; `startRun` and `estimateRunCost` of API 1.16.0 refuse a group beside a connection
 * or a preset). Written under `R-149d` and not run in EXEC-2; none of it needs PostgreSQL.
 *
 * `RUN-START-ONE-01a` removed the three-way start choice from the control (the radio «Как выбрать
 * исполнителя», the group, preset and executor selects): the one-button control sends none of the three.
 * What stays here is the request itself, which the contract still lets a caller fill: `startRunBody`
 * and `startRunIntent` hold at most one selector and give each choice its own intent. The tests of the
 * radio (`startSelectors`, `chooseMode`, the control rendered with three ways to start, the control live
 * with a group select) were removed with it; `one-click-start.test.ts` proves the control sends none.
 */

import { describe, expect, it } from 'vitest';

import { startRunBody, startRunIntent } from '@/features/start-run';
import type { StartRunCommand } from '@/features/start-run';

import { VERSION_UID } from '../review/fixtures';
import { COST_CONSENT } from '../analysis-settings/cost-estimate-fixtures';
import { READY, groupId } from './executor-groups-fixtures';

const GROUP = groupId(1);
const CONNECTION = READY.connection.connection_id;
const PRESET = 'pre_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

describe('the request carries one selector, even if the command holds more', () => {
  function body(over: Partial<StartRunCommand>): Record<string, unknown> {
    return startRunBody({ versionUid: VERSION_UID, idempotencyKey: 'ik', ...over }) as Record<string, unknown>;
  }

  it('prefers the group, then the preset, then the connection', () => {
    expect(body({ executorGroupId: GROUP, presetId: PRESET, executorConnectionId: CONNECTION }))
      .toEqual({ version_uid: VERSION_UID, executor_group_id: GROUP });
    expect(body({ presetId: PRESET, executorConnectionId: CONNECTION }))
      .toEqual({ version_uid: VERSION_UID, preset_id: PRESET });
    expect(body({ executorConnectionId: CONNECTION }))
      .toEqual({ version_uid: VERSION_UID, executor_connection_id: CONNECTION });
    expect(body({})).toEqual({ version_uid: VERSION_UID });
  });

  it('never holds two of the three keys, for every subset of the three', () => {
    for (const mask of Array.from({ length: 8 }, (_, index) => index)) {
      const request = body({
        ...((mask & 1) === 0 ? {} : { executorGroupId: GROUP }),
        ...((mask & 2) === 0 ? {} : { presetId: PRESET }),
        ...((mask & 4) === 0 ? {} : { executorConnectionId: CONNECTION }),
      });
      const keys = ['executor_group_id', 'preset_id', 'executor_connection_id'].filter((key) => key in request);
      expect(keys.length, `mask ${mask}`).toBeLessThanOrEqual(1);
    }
  });

  it('keeps the cost consent and the raised limit beside the selector', () => {
    expect(body({ executorGroupId: GROUP, relaxedLimits: true, costConsent: COST_CONSENT })).toEqual({
      version_uid: VERSION_UID, executor_group_id: GROUP, relaxed_limits: true, cost_consent: COST_CONSENT,
    });
  });
});

describe('the intent of a group start', () => {
  it('is a different intent from the same version without a group, and from another group', () => {
    const plain = startRunIntent(VERSION_UID, null);
    const grouped = startRunIntent(VERSION_UID, null, null, false, undefined, GROUP);
    const other = startRunIntent(VERSION_UID, null, null, false, undefined, groupId(2));
    expect(plain.signature).toBe(`start-run:${VERSION_UID}`);
    expect(grouped.signature).toBe(`start-run:${VERSION_UID}:group:${GROUP}`);
    expect(new Set([plain.signature, grouped.signature, other.signature]).size).toBe(3);
  });

  it('builds the command with the group alone, and keeps the old signatures word for word', () => {
    const grouped = startRunIntent(VERSION_UID, CONNECTION, PRESET, false, undefined, GROUP);
    expect(grouped.command('ik')).toEqual({ versionUid: VERSION_UID, idempotencyKey: 'ik', executorGroupId: GROUP });
    expect(startRunIntent(VERSION_UID, CONNECTION).signature).toBe(`start-run:${VERSION_UID}:executor:${CONNECTION}`);
    expect(startRunIntent(VERSION_UID, null, PRESET).signature).toBe(`start-run:${VERSION_UID}:preset:${PRESET}`);
  });
});
