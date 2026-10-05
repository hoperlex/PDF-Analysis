/**
 * The small label-bearing primitives are public components, so their TypeScript props are
 * not a runtime boundary. A malformed transport object can reach them through a cast or a
 * stale client. Each primitive must render one typed fault rather than indexing a label map
 * with an unknown key and producing an empty badge.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunState, StageStatus, Verdict } from '@/shared/api';
import type { StageRow } from '@/entities/audit-run';
import { StageTable } from '@/entities/audit-run';
import { VerdictBadge } from '@/entities/expert-decision';
import { RunStateBadge, StageStatusBadge } from '@/shared/ui';

import { render } from '../review/fixtures';

describe('closed-vocabulary badges fail visibly', () => {
  it('renders a typed fault for an unknown verdict', () => {
    const markup = render(
      createElement(VerdictBadge, { verdict: 'future_verdict' as Verdict }),
    );
    expect(markup).toContain('data-closed-vocabulary-fault="verdict"');
    expect(markup).toContain('Неизвестный вердикт');
    expect(markup).not.toContain('future_verdict');
  });

  it('renders a typed fault for an unknown run state', () => {
    const markup = render(
      createElement(RunStateBadge, { state: 'future_state' as RunState }),
    );
    expect(markup).toContain('data-closed-vocabulary-fault="run-state"');
    expect(markup).not.toContain('future_state');
  });

  it('renders a typed fault for an unknown provider mode', () => {
    const markup = render(
      createElement(RunStateBadge, {
        state: 'published',
        providerMode: 'future_mode' as 'live',
      }),
    );
    expect(markup).toContain('data-closed-vocabulary-fault="provider-mode"');
    expect(markup).not.toContain('future_mode');
  });

  it('renders a typed fault for an unknown stage status', () => {
    const markup = render(
      createElement(StageStatusBadge, { status: 'future_status' as StageStatus }),
    );
    expect(markup).toContain('data-closed-vocabulary-fault="stage-status"');
    expect(markup).not.toContain('future_status');
  });
});

describe('the stage table validates every label-table key before rendering rows', () => {
  const row: StageRow = {
    stageId: 'source_preparation',
    status: 'succeeded',
    errorCode: null,
    startedAt: null,
    finishedAt: null,
    expected: true,
    ordinal: 1,
    dependsOn: [],
  };

  it.each([
    ['stage id', { ...row, stageId: 'future_stage' }],
    ['stage status', { ...row, status: 'future_status' }],
    ['dependency', { ...row, dependsOn: ['future_stage'] }],
  ])('renders a typed fault for an unknown %s', (_name, malformed) => {
    const markup = render(
      createElement(StageTable, { rows: [malformed as unknown as StageRow] }),
    );
    expect(markup).toContain('data-stage-table-fault="closed-vocabulary"');
    expect(markup).toContain('Этап содержит неизвестное значение.');
    expect(markup).not.toContain('future_');
  });
});
