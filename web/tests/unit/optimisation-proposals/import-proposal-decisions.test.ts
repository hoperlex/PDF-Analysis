/**
 * `UI-B-15`: «Загрузить решения» on a pass's proposals, and «Выгрузить таблицу решений» beside it.
 *
 * The control is rendered, not read from source (`D-53`): its states, the refusal of every row in words, the refusal of a
 * whole file. The hook is exercised through its configuration, as `commands.test.ts` does: one `Idempotency-Key` per
 * chosen file, reused on a retry of that file; what a success changes is re-read, and a file that recorded nothing
 * changes nothing.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: (configuration: unknown) => configuration,
    useQueryClient: () => ({
      invalidateQueries: (...args: unknown[]) => {
        calls.invalidations.push(args);
        return Promise.resolve();
      },
    }),
  };
});

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  const refs: { current: unknown }[] = [];
  let cursor = 0;
  return {
    ...actual,
    useRef: (initial: unknown) => {
      const slot = (refs[cursor] ??= { current: initial });
      cursor += 1;
      return slot;
    },
    __rewind: () => {
      cursor = 0;
    },
    __forget: () => {
      refs.length = 0;
      cursor = 0;
    },
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, importOptimisationProposalDecisions: vi.fn() };
});

import * as react from 'react';

import type { ProposalDecisionImportReport } from '@/shared/api';
import { ApiError, PROPOSAL_DECISION_IMPORT_REFUSAL_VALUES, importOptimisationProposalDecisions, queryKeys } from '@/shared/api';
import { proposalsXlsxFileName } from '@/entities/optimisation-proposal';
import {
  PROPOSAL_IMPORT_REFUSAL_LABELS,
  ImportProposalDecisionsView,
  importProposalFailure,
  useImportProposalDecisions,
} from '@/features/import-proposal-decisions';
import { ExportProposalsView } from '@/widgets/optimisation-proposals';

import { DOOR_PROPOSAL, PASS_ID } from './fixtures';

const noop = (): void => undefined;
const rewind = (): void => (react as unknown as { __rewind: () => void }).__rewind();
const forget = (): void => (react as unknown as { __forget: () => void }).__forget();

function report(over: Partial<ProposalDecisionImportReport> = {}): ProposalDecisionImportReport {
  return {
    optimisation_pass_id: PASS_ID,
    recorded: 1,
    unchanged: 1,
    refused: 2,
    rows: [
      { row: 2, outcome: 'recorded', optimisation_proposal_id: DOOR_PROPOSAL },
      { row: 3, outcome: 'unchanged', optimisation_proposal_id: DOOR_PROPOSAL },
      { row: 4, outcome: 'refused', reason: 'unknown_proposal' },
      { row: 7, outcome: 'refused', reason: 'comment_required', optimisation_proposal_id: DOOR_PROPOSAL },
    ],
    ...over,
  };
}

function view(over: { pending?: boolean; report?: ProposalDecisionImportReport | null; failure?: string | null } = {}): string {
  return renderToStaticMarkup(
    createElement(ImportProposalDecisionsView, {
      pending: over.pending ?? false,
      report: over.report ?? null,
      failure: over.failure ?? null,
      onChoose: noop,
    }),
  );
}

describe('the control', () => {
  it('offers a workbook file and says what it is', () => {
    const markup = view();
    expect(markup).toContain('data-proposal-decision-import');
    expect(markup).toContain('Загрузить решения');
    expect(markup).toMatch(/<input[^>]*type="file"[^>]*accept="\.xlsx,/);
    expect(markup).not.toContain('disabled=""');
  });

  it('says it is loading, and cannot be pressed twice', () => {
    const markup = view({ pending: true });
    expect(markup).toContain('Загружаю решения');
    expect(markup).toContain('disabled=""');
  });

  it('counts what the import did and names each refused row with its reason in words', () => {
    const markup = view({ report: report() });
    expect(markup).toContain('data-import-recorded="1"');
    expect(markup).toContain('Записано 1 · без изменений 1 · отклонено 2');
    expect(markup).toContain('Строка 4: нет такого предложения в этом проходе');
    expect(markup).toContain('Строка 7: для «на доработку» нужен комментарий');
    expect(markup).not.toContain('Строка 2:');
  });

  it('says a refused file in a role=alert line', () => {
    const markup = view({ failure: 'Файл пуст.' });
    expect(markup).toMatch(/role="alert"[^>]*>Файл пуст\./);
  });
});

describe('the words', () => {
  it('give every refusal of the contract a Russian sentence, and only those', () => {
    expect(Object.keys(PROPOSAL_IMPORT_REFUSAL_LABELS).sort()).toEqual([...PROPOSAL_DECISION_IMPORT_REFUSAL_VALUES].sort());
    for (const label of Object.values(PROPOSAL_IMPORT_REFUSAL_LABELS)) expect(label).not.toMatch(/[A-Za-z_]/);
  });

  it('say a whole refused file by the constraint the server names, else by the catalogue', () => {
    const refuse = (constraint: string) =>
      new ApiError(422, {
        contract_version: '1.53.0', error_code: 'validation_failed', message: 'x',
        correlation_id: 'cid-1', retryable: false, details: { field: 'file', constraint },
      }, 'cid-1');
    expect(importProposalFailure(refuse('not_our_export'))).toContain('лист «Предложения» с колонкой идентификаторов предложений');
    expect(importProposalFailure(refuse('unreadable'))).toBe('Файл не читается как книга Excel (.xlsx).');
    expect(importProposalFailure(refuse('too_large'))).toBe('Файл больше 10 MiB.');
    expect(importProposalFailure(refuse('too_many_rows'))).toBe('В листе больше 20 000 строк.');
    expect(importProposalFailure(refuse('something_else'))).not.toBe('');
  });

  it('name the downloaded workbook after the pass and nothing else', () => {
    expect(proposalsXlsxFileName(PASS_ID)).toBe(`${PASS_ID}-proposals.xlsx`);
  });
});

describe('the export beside it', () => {
  it('offers the CSV and the workbook, each its own button, and the load control only when given', () => {
    const plain = renderToStaticMarkup(createElement(ExportProposalsView, { pending: false, failure: null, onDownload: noop }));
    expect(plain).toContain('Выгрузить CSV предложений');
    expect(plain).not.toContain('Выгрузить таблицу решений');
    const both = renderToStaticMarkup(
      createElement(ExportProposalsView, {
        pending: false, failure: null, onDownload: noop, onDownloadXlsx: noop,
        importControl: createElement(ImportProposalDecisionsView, { pending: false, report: null, failure: null, onChoose: noop }),
      }),
    );
    expect(both).toContain('Выгрузить CSV предложений');
    expect(both).toContain('Выгрузить таблицу решений (.xlsx)');
    expect(both).toContain('data-proposal-decision-import');
  });
});

describe('the command', () => {
  type Captured = {
    mutationFn: (input: { file: File }) => Promise<ProposalDecisionImportReport>;
    onSuccess?: (result: ProposalDecisionImportReport) => void;
    retry?: boolean;
  };
  const hook = (): Captured => {
    rewind();
    return useImportProposalDecisions({ passId: PASS_ID }) as unknown as Captured;
  };
  const file = (name: string) => new File([new Uint8Array([80, 75, 3, 4])], name);
  const keyOf = (call: number): string =>
    (vi.mocked(importOptimisationProposalDecisions).mock.calls[call]?.[0] as { idempotencyKey: string }).idempotencyKey;

  beforeEach(() => {
    calls.invalidations.length = 0;
    vi.clearAllMocks();
    forget();
  });

  it('sends the file to the pass under a key, reuses it for the same file and mints another for another file', async () => {
    vi.mocked(importOptimisationProposalDecisions).mockResolvedValue({ data: report() } as never);
    const chosen = file('Решения.xlsx');
    expect(hook().retry).toBe(false);
    await hook().mutationFn({ file: chosen });
    await hook().mutationFn({ file: chosen });
    await hook().mutationFn({ file: file('Другой.xlsx') });
    const sent = vi.mocked(importOptimisationProposalDecisions).mock.calls[0]?.[0];
    expect(sent).toMatchObject({ path: { optimisation_pass_id: PASS_ID }, body: { file: chosen } });
    expect(keyOf(1)).toBe(keyOf(0));
    expect(keyOf(2)).not.toBe(keyOf(0));
  });

  it('re-reads what a decision moves when something was recorded, and nothing when nothing was', () => {
    hook().onSuccess?.(report({ recorded: 0 }));
    expect(calls.invalidations).toEqual([]);
    hook().onSuccess?.(report());
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.optimisation.proposalsOf(PASS_ID) }],
      [{ queryKey: queryKeys.optimisation.allPasses() }],
      [{ queryKey: queryKeys.optimisation.allAccepted() }],
      [{ queryKey: queryKeys.optimisation.allProposalDecisions() }],
    ]);
    for (const entry of calls.invalidations) {
      const [options] = entry as [{ queryKey: readonly unknown[] }];
      expect(options.queryKey[0]).toBe('optimisation');
    }
  });
});
