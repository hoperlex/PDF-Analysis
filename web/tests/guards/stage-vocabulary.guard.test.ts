/**
 * The stage vocabulary and the pipeline's shape, held to the contracts that decide them.
 *
 * Two maps in `web/src` restate something a contract in this repository already declares,
 * and both would drift in silence:
 *
 *   `STAGE_LABELS`      one Russian name per `StageId`, the enum in
 *                       `contracts/api/v1/openapi.json`;
 *   `STAGE_DEPENDS_ON`  one dependency list per stage, the `depends_on` declared in
 *                       `contracts/analysis/v1/stage-registry.json`.
 *
 * The type checker holds the first map's KEYS — `Record<StageId, string>` over a type
 * generated from the enum — and that is worth exactly what the generated type is worth. It
 * cannot see a label that is still an English word, a label that is a copy of the machine
 * value, or a dependency list that has quietly stopped matching the registry. This file
 * reads both contracts and judges the maps against them.
 *
 * **And the third assertion here is the one `D-62` actually asked for.** The run screen now
 * numbers the stages PC-01 schedules. A number is a claim that the things numbered stand in
 * a line, and the nine stages of `stage-registry.json` DO NOT: the registry forks after
 * `document_context_build`, joins at `finding_merge` and forks again. The ordinal is honest
 * only because the four stages PC-01 schedules happen to be a chain — so that is asserted
 * against the registry, in both directions: the four are a chain, and the nine are not. A
 * later wave that schedules a forked stage reddens this file before a reader can be misled
 * by a column that quietly became an invention.
 */

import { describe, expect, it } from 'vitest';

import type { StageId } from '@/shared/api';
import { STAGE_ID_VALUES } from '@/shared/api';
import { PC01_STAGE_IDS, STAGE_DEPENDS_ON } from '@/entities/audit-run';
import { STAGE_LABELS } from '@/shared/ui';

import { join } from 'node:path';
import { CONTRACT_PATH, REPO_ROOT, readJson } from './lib/repo';

const REGISTRY_PATH = join(REPO_ROOT, 'contracts', 'analysis', 'v1', 'stage-registry.json');

interface OpenApi {
  readonly components: { readonly schemas: Record<string, { readonly enum?: readonly string[] }> };
}

interface Registry {
  readonly stages: readonly {
    readonly stage_id: StageId;
    readonly depends_on?: readonly StageId[];
    readonly status_policy?: { readonly skip_allowed?: boolean };
    readonly execution?: { readonly mandatory?: boolean };
  }[];
}

function contractStageIds(): readonly string[] {
  const openapi = readJson<OpenApi>(CONTRACT_PATH);
  const schema = openapi.components.schemas['StageId'];
  if (schema?.enum === undefined) {
    throw new Error('openapi.json declares no StageId enum; this guard has no subject.');
  }
  return schema.enum;
}

const registry = readJson<Registry>(REGISTRY_PATH);

// ============================================================ the names a reviewer reads

describe('every stage the contract publishes has a Russian name', () => {
  it('is keyed on the whole enum, in both directions', () => {
    // The generated `STAGE_ID_VALUES` is what the type is built from, so it is checked
    // against the contract itself rather than trusted as a second copy of it.
    expect([...STAGE_ID_VALUES].sort()).toEqual([...contractStageIds()].sort());
    expect(Object.keys(STAGE_LABELS).sort()).toEqual([...contractStageIds()].sort());
    // Non-vacuous: nine, not zero, and the registry declares the same nine.
    expect(contractStageIds().length).toBe(9);
    expect(registry.stages.map((stage) => stage.stage_id).sort()).toEqual(
      [...contractStageIds()].sort(),
    );
  });

  it('names each stage in the reader’s language and never in the machine’s', () => {
    for (const stageId of STAGE_ID_VALUES) {
      const label = STAGE_LABELS[stageId];
      // `D-62`: the defect was the identifier reaching the screen as the label. A label
      // that IS the identifier is that defect wearing a map.
      expect({ stageId, isIdentifier: label === stageId }).toEqual({ stageId, isIdentifier: false });
      // Cyrillic, and no Latin word at all. `rendered-language.guard.test.ts` judges what a
      // screen renders; this judges the source of the words before a screen composes them,
      // so a label that is never rendered on a seeded screen cannot slip through in English.
      expect({ stageId, cyrillic: /[а-яА-Я]/.test(label) }).toEqual({
        stageId,
        cyrillic: true,
      });
      expect({ stageId, latin: /[A-Za-z]/.test(label) }).toEqual({ stageId, latin: false });
    }
  });
});

// ================================================== the dependencies, and what they imply

describe('the dependency map is the contract’s, not a recollection of it', () => {
  it('matches every stage’s declared depends_on, in both directions', () => {
    const declared = Object.fromEntries(
      registry.stages.map((stage) => [stage.stage_id, [...(stage.depends_on ?? [])].sort()]),
    );
    const mirrored = Object.fromEntries(
      STAGE_ID_VALUES.map((stageId) => [stageId, [...STAGE_DEPENDS_ON[stageId]].sort()]),
    );
    expect(mirrored).toEqual(declared);
    // And a dependency names a stage that exists, so the registry cannot point at a stage
    // the API enum does not publish without this being red.
    for (const dependencies of Object.values(declared)) {
      for (const stageId of dependencies) expect(STAGE_ID_VALUES).toContain(stageId);
    }
  });

  it('says the nine stages are a GRAPH, which is why nothing numbers them', () => {
    // The finding `D-62` asked for, asserted rather than described. If this ever goes
    // green by the pipeline becoming a line, the run screen may number all nine — and
    // until then, numbering them would be an invention.
    const fanOut = STAGE_ID_VALUES.filter(
      (stageId) =>
        STAGE_ID_VALUES.filter((other) => STAGE_DEPENDS_ON[other].includes(stageId)).length > 1,
    );
    const joins = STAGE_ID_VALUES.filter((stageId) => STAGE_DEPENDS_ON[stageId].length > 1);
    expect(fanOut).toEqual(['document_context_build', 'finding_merge']);
    expect(joins).toEqual(['finding_merge']);
    // Four of the nine may not run at all, which is the second reason a position over the
    // nine would say more than the contract does.
    const optional = registry.stages
      .filter((stage) => stage.status_policy?.skip_allowed === true)
      .map((stage) => stage.stage_id);
    expect(optional).toEqual([
      'block_analysis',
      'finding_review',
      'finding_correction',
      'norm_verification',
    ]);
  });

  it('says the four stages PC-01 schedules ARE a chain, which is what licenses the ordinal', () => {
    // The stage table numbers these four. A number asserts a line, so the line is checked
    // against the registry: the first waits for nothing, and each later one waits for
    // exactly its predecessor in the schedule.
    expect(STAGE_DEPENDS_ON[PC01_STAGE_IDS[0]]).toEqual([]);
    PC01_STAGE_IDS.forEach((stageId, index) => {
      if (index === 0) return;
      expect({ stageId, waitsFor: [...STAGE_DEPENDS_ON[stageId]] }).toEqual({
        stageId,
        waitsFor: [PC01_STAGE_IDS[index - 1]],
      });
    });
    // And no scheduled stage is one the pipeline forks into, so the four cannot be a chain
    // by accident while the schedule silently picks up a branch.
    for (const stageId of PC01_STAGE_IDS) {
      const siblings = STAGE_ID_VALUES.filter(
        (other) =>
          other !== stageId &&
          STAGE_DEPENDS_ON[other].length === STAGE_DEPENDS_ON[stageId].length &&
          STAGE_DEPENDS_ON[other].every((d) => STAGE_DEPENDS_ON[stageId].includes(d)) &&
          STAGE_DEPENDS_ON[stageId].length > 0 &&
          PC01_STAGE_IDS.includes(other as (typeof PC01_STAGE_IDS)[number]),
      );
      expect({ stageId, scheduledSiblings: siblings }).toEqual({ stageId, scheduledSiblings: [] });
    }
  });
});
