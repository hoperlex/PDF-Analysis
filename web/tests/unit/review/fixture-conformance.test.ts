/**
 * The fixtures are contract-shaped, and something checks that they are.
 *
 * `tests/unit/review/fixtures.ts` opens by promising that "identifiers follow the
 * contract's patterns" and that "every builder returns a value that type-checks as the
 * generated model, so a contract change that removes or renames a field takes these red at
 * `tsc` time". Three of those claims were false when `W12-WEB` checked them, and nothing
 * in the suite could have said so:
 *
 *   - `PROJECT_UID` was `proj_…`; the contract pattern is `^prj_[0-9A-HJKMNP-TV-Z]{26}$`,
 *     and the file's own docstring named `proj_` as if it were the contract prefix;
 *   - `provenance()` declared `stage_id: 'analysis'`, which is not one of the nine values
 *     of the contract's `StageId` — hidden from `tsc` by the builder's `as
 *     ObservationProvenance` cast, which is exactly the escape the docstring promised was
 *     not there;
 *   - `evidence()` declared `block_id: 'blk_0042'`; the contract pattern is `^b_[0-9]{6}$`.
 *     `key-leakage.test.ts` asserted the rendered markup does not contain `blk_` — a
 *     prefix the contract can never produce, so that assertion could not fail.
 *
 * A fixture that does not match the contract is a test passing against a payload the server
 * cannot send. This file pins every identifier the builders mint against the generated
 * pattern **and** against the literal prefix, so neither the fixture nor the generated
 * constant can drift alone.
 */

import { describe, expect, it } from 'vitest';

import {
  ANALYSIS_PROFILE_ID_PATTERN,
  DECISION_ID_PATTERN,
  DOCUMENT_UID_PATTERN,
  FINDING_OBSERVATION_ID_PATTERN,
  FINDING_UID_PATTERN,
  MODEL_CALL_ID_PATTERN,
  PROJECT_UID_PATTERN,
  PROMPT_BUNDLE_ID_PATTERN,
  RUN_ID_PATTERN,
  STAGE_ID_VALUES,
  VERSION_UID_PATTERN,
  VERDICT_VALUES,
  DECISION_EVENT_TYPE_VALUES,
  FINDING_CATEGORY_VALUES,
  PROVIDER_MODE_VALUES,
  RUN_STATE_VALUES,
} from '@/shared/api';

import {
  DOCUMENT_UID,
  FINDING_UID,
  OBSERVATION_ID,
  PROJECT_UID,
  RUN_ID,
  VERSION_UID,
  decisionEvent,
  decisionId,
  evidence,
  finding,
  findingDetail,
  observation,
  provenance,
  runStatus,
} from './fixtures';

/** The literal prefixes, pinned here so a mutated generated pattern still reddens. */
const PREFIXES: Readonly<Record<string, string>> = {
  project: 'prj_',
  document: 'doc_',
  version: 'ver_',
  run: 'run_',
  finding: 'fnd_',
  observation: 'fobs_',
  decision: 'dec_',
  analysisProfile: 'ap_',
  promptBundle: 'pb_',
  modelCall: 'mc_',
};

describe('the generated patterns are the prefixes the contract declares', () => {
  it('anchors each one and names the prefix this suite expects', () => {
    expect(PROJECT_UID_PATTERN).toBe('^prj_[0-9A-HJKMNP-TV-Z]{26}$');
    expect(DOCUMENT_UID_PATTERN).toContain(PREFIXES['document'] as string);
    expect(VERSION_UID_PATTERN).toContain(PREFIXES['version'] as string);
    expect(RUN_ID_PATTERN).toContain(PREFIXES['run'] as string);
    expect(FINDING_UID_PATTERN).toContain(PREFIXES['finding'] as string);
    expect(FINDING_OBSERVATION_ID_PATTERN).toContain(PREFIXES['observation'] as string);
    expect(DECISION_ID_PATTERN).toContain(PREFIXES['decision'] as string);
    expect(ANALYSIS_PROFILE_ID_PATTERN).toContain(PREFIXES['analysisProfile'] as string);
    expect(PROMPT_BUNDLE_ID_PATTERN).toContain(PREFIXES['promptBundle'] as string);
    expect(MODEL_CALL_ID_PATTERN).toContain(PREFIXES['modelCall'] as string);
  });
});

describe('every identifier the fixtures mint matches its contract pattern', () => {
  it.each([
    ['PROJECT_UID', PROJECT_UID, PROJECT_UID_PATTERN, PREFIXES['project'] as string],
    ['DOCUMENT_UID', DOCUMENT_UID, DOCUMENT_UID_PATTERN, PREFIXES['document'] as string],
    ['VERSION_UID', VERSION_UID, VERSION_UID_PATTERN, PREFIXES['version'] as string],
    ['RUN_ID', RUN_ID, RUN_ID_PATTERN, PREFIXES['run'] as string],
    ['FINDING_UID', FINDING_UID, FINDING_UID_PATTERN, PREFIXES['finding'] as string],
    ['OBSERVATION_ID', OBSERVATION_ID, FINDING_OBSERVATION_ID_PATTERN, PREFIXES['observation'] as string],
  ])('%s', (_name, value, pattern, prefix) => {
    expect(value.startsWith(prefix)).toBe(true);
    expect(new RegExp(pattern).test(value)).toBe(true);
  });

  it('mints decision identifiers that match too, for every suffix used', () => {
    for (const suffix of ['A', 'B', 'C', 'Z']) {
      const id = decisionId(suffix);
      expect(id.startsWith('dec_')).toBe(true);
      expect(new RegExp(DECISION_ID_PATTERN).test(id)).toBe(true);
    }
  });

  it('mints provenance identifiers that match', () => {
    const p = provenance();
    expect(new RegExp(ANALYSIS_PROFILE_ID_PATTERN).test(p.analysis_profile_id)).toBe(true);
    expect(new RegExp(PROMPT_BUNDLE_ID_PATTERN).test(p.prompt_bundle_id)).toBe(true);
    expect(p.model_call_id === null || new RegExp(MODEL_CALL_ID_PATTERN).test(p.model_call_id ?? '')).toBe(
      true,
    );
  });
});

describe('every enum-valued field the fixtures set is a value the contract declares', () => {
  it('uses a real StageId for the observation provenance', () => {
    // `'analysis'` is not one. The builder's cast kept `tsc` from saying so.
    expect([...STAGE_ID_VALUES]).toContain(provenance().stage_id);
  });

  it('uses a real ProviderMode, FindingCategory, Verdict and DecisionEventType', () => {
    expect([...PROVIDER_MODE_VALUES]).toContain(provenance().provider_mode);
    expect([...FINDING_CATEGORY_VALUES]).toContain(observation().category);
    expect([...FINDING_CATEGORY_VALUES]).toContain(finding().category);
    expect([...VERDICT_VALUES]).toContain(finding().current_verdict);
    expect([...DECISION_EVENT_TYPE_VALUES]).toContain(decisionEvent().event_type);
    expect([...VERDICT_VALUES]).toContain(decisionEvent().verdict ?? 'pending');
    expect([...RUN_STATE_VALUES]).toContain(runStatus().state);
  });
});

describe('the evidence block_id is the contract shape, not an invented one', () => {
  it('matches the secondary-anchor pattern the contract declares', () => {
    // `^b_[0-9]{6}$`. Written out because the generator emits no constant for it: the
    // pattern is inline on `Evidence.block_id` rather than on a named schema.
    const blockId = evidence().block_id;
    expect(typeof blockId).toBe('string');
    expect(blockId ?? '').toMatch(/^b_[0-9]{6}$/);
  });

  it('is not the `blk_` prefix the leakage check used to look for', () => {
    // The leakage suite asserted the rendered markup contains no `blk_`. Nothing the
    // contract can produce ever contains `blk_`, so that assertion could not have failed.
    expect(evidence().block_id ?? '').not.toContain('blk_');
  });
});

describe('the composed fixtures stay consistent with their parts', () => {
  it('gives a finding the same identity everywhere it appears', () => {
    const detail = findingDetail();
    expect(detail.finding_uid).toBe(FINDING_UID);
    expect(detail.project_uid).toBe(PROJECT_UID);
    expect(detail.run_id).toBe(RUN_ID);
    expect(detail.observation.finding_observation_id).toBe(OBSERVATION_ID);
  });

  it('gives an evidence item an anchor that agrees with its own quotation', () => {
    const item = evidence({ quote: 'a\u{1F5CE}b' });
    expect(item.char_end - item.char_start).toBe(3);
  });
});
