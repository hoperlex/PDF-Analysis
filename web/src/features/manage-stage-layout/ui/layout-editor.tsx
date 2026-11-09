'use client';

/**
 * «Изменить» in «Модели по этапам» (`HOSTS-WEB-01`, plan 2026-11-09 §7.4; **administrator only**). The segments
 * «Только Claude · Только Codex · Свой набор», and for each of the six rows a model and an effort. «Дополнительно» holds the
 * answer limit and the timeout of every cell.
 *
 * **What the form offers.** A set only when every model it names can be served now; a model only when some server can serve
 * it (and the model already in the cell, so the draft never drops what is in force); an effort only from the catalogue's
 * list for the model. A row that is an ensemble scheme (several cells) is read-only here: the plan chooses it whole, with the
 * set. The server checks every pair again, and a refusal is said in words.
 *
 * One idempotency key per intent, kept for an explicit repeat after an unknown outcome and released when the command settles.
 */

import { useState } from 'react';

import type { ModelCatalogue, ModelEffort, StageLayoutCell, StageModelKit, StageModelLayout } from '@/shared/api';
import { MODEL_EFFORT_VALUES, STAGE_ROW_KEY_VALUES } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { modelLabel } from '@/entities/executor-host';
import {
  ADVANCED_SUMMARY,
  CANCEL_LABEL,
  ENSEMBLE_NOTE,
  KIT_LEGEND,
  NO_AVAILABLE_MODELS,
  ROW_EFFORT_LABEL,
  ROW_MODEL_LABEL,
  SAVE_LABEL,
  STAGE_EFFORT_LABELS,
  STAGE_KIT_LABELS,
  STAGE_ROLE_LABELS,
  STAGE_ROW_LABELS,
  TIMEOUT_LABEL,
  TOKENS_LABEL,
  cellText,
  effortsOf,
  layoutFailure,
  rowCells,
} from '@/entities/stage-layout';
import { useCommandKey } from '@/features/manage-executor-connection';
import { HostFailure } from '@/features/manage-executor-host';
import { Table } from '@/shared/ui';

import {
  chooseKit,
  draftChanged,
  draftProblem,
  draftRequest,
  initialDraft,
  modelOptions,
  offeredKits,
  setCellEffort,
  setCellLimit,
  setCellModel,
} from '../model/draft';
import type { LayoutDraft } from '../model/draft';
import { useReviseStageModelLayout } from '../model/use-manage-stage-layout';
import styles from './manage-stage-layout.module.css';

export interface LayoutEditorViewProps {
  readonly draft: LayoutDraft;
  readonly catalogue: ModelCatalogue | undefined;
  readonly availableModelIds: readonly string[];
  readonly currentKit: StageModelKit | undefined;
  readonly pending: boolean;
  readonly problem: string | null;
  readonly failure: ExecutionFailure | null;
  readonly onKit: (kit: StageModelKit) => void;
  readonly onModel: (cellKey: string, modelId: string) => void;
  readonly onEffort: (cellKey: string, effort: ModelEffort) => void;
  readonly onLimit: (cellKey: string, field: 'max_output_tokens' | 'timeout_seconds', value: number) => void;
  readonly onSave: () => void;
  readonly onCancel: () => void;
}

function RowEditor({ row, cells, ...props }: {
  readonly row: (typeof STAGE_ROW_KEY_VALUES)[number];
  readonly cells: readonly StageLayoutCell[];
} & Pick<LayoutEditorViewProps, 'catalogue' | 'availableModelIds' | 'onModel' | 'onEffort'>) {
  if (cells.length === 0) return <span className="am-note">нет данных</span>;
  if (cells.length > 1) {
    return (
      <span data-layout-ensemble={row}>
        {cells.map((cell) => `${STAGE_ROLE_LABELS[cell.role]}: ${cellText(cell)}`).join('; ')}
        <span className="am-form__hint"> {ENSEMBLE_NOTE}</span>
      </span>
    );
  }
  const cell = cells[0] as StageLayoutCell;
  const options = modelOptions(cell, props.catalogue, props.availableModelIds);
  const efforts = MODEL_EFFORT_VALUES.filter((effort) => effortsOf(props.catalogue, cell.model_id).includes(effort));
  return (
    <span className="am-form__row">
      <select
        aria-label={`${ROW_MODEL_LABEL}: ${STAGE_ROW_LABELS[row]}`}
        value={cell.model_id}
        data-layout-model={row}
        onChange={(event) => props.onModel(cell.cell_key, event.currentTarget.value)}
      >
        {options.map((id) => <option key={id} value={id}>{modelLabel(id)}</option>)}
      </select>
      <select
        aria-label={`${ROW_EFFORT_LABEL}: ${STAGE_ROW_LABELS[row]}`}
        value={cell.effort}
        data-layout-effort={row}
        onChange={(event) => props.onEffort(cell.cell_key, event.currentTarget.value as ModelEffort)}
      >
        {(efforts.includes(cell.effort) ? efforts : [cell.effort, ...efforts]).map((effort) => (
          <option key={effort} value={effort}>{STAGE_EFFORT_LABELS[effort]}</option>
        ))}
      </select>
    </span>
  );
}

export function LayoutEditorView(props: LayoutEditorViewProps) {
  const { draft, catalogue, availableModelIds, currentKit, pending, problem, failure } = props;
  const kits = offeredKits(catalogue, availableModelIds, currentKit);
  const noChoice = availableModelIds.length === 0;
  const rows = STAGE_ROW_KEY_VALUES.map((row) => ({ row, cells: rowCells(draft.cells, row) }));
  return (
    <form
      className="am-form"
      data-layout-editor
      onSubmit={(event) => { event.preventDefault(); props.onSave(); }}
    >
      {noChoice ? <p className="am-note" role="status" data-layout-no-models>{NO_AVAILABLE_MODELS}</p> : null}
      <div role="radiogroup" aria-label={KIT_LEGEND} className={styles.segments}>
        {kits.map((kit) => (
          <button
            key={kit}
            type="button"
            role="radio"
            aria-checked={kit === draft.kit}
            className={styles.segment}
            data-layout-kit={kit}
            onClick={() => props.onKit(kit)}
          >
            {STAGE_KIT_LABELS[kit]}
          </button>
        ))}
      </div>
      <Table
        caption="Модели по этапам"
        rowKey={(entry) => entry.row}
        rows={rows}
        columns={[
          { key: 'row', header: 'Строка', cell: (entry) => STAGE_ROW_LABELS[entry.row] },
          {
            key: 'model',
            header: `${ROW_MODEL_LABEL} · ${ROW_EFFORT_LABEL.toLowerCase()}`,
            cell: (entry) => (
              <RowEditor row={entry.row} cells={entry.cells} catalogue={catalogue} availableModelIds={availableModelIds} onModel={props.onModel} onEffort={props.onEffort} />
            ),
          },
        ]}
      />
      <details className={styles.fold}>
        <summary>{ADVANCED_SUMMARY}</summary>
        <ul className={styles.limits}>
          {rows.flatMap((entry) => entry.cells).map((cell) => (
            <li key={cell.cell_key} className={styles.limit} data-layout-limits={cell.cell_key}>
              <strong>{STAGE_ROW_LABELS[cell.row]}{STAGE_ROLE_LABELS[cell.role] === '' ? '' : ` · ${STAGE_ROLE_LABELS[cell.role]}`}</strong>
              <label>
                {TOKENS_LABEL}{' '}
                <input
                  className={styles.number}
                  type="number"
                  min={1}
                  max={65536}
                  value={cell.max_output_tokens}
                  onChange={(event) => props.onLimit(cell.cell_key, 'max_output_tokens', Number(event.currentTarget.value))}
                />
              </label>
              <label>
                {TIMEOUT_LABEL}{' '}
                <input
                  className={styles.number}
                  type="number"
                  min={1}
                  max={7200}
                  value={cell.timeout_seconds}
                  onChange={(event) => props.onLimit(cell.cell_key, 'timeout_seconds', Number(event.currentTarget.value))}
                />
              </label>
            </li>
          ))}
        </ul>
      </details>
      {problem === null ? null : <p className="am-form__problem" role="alert" data-layout-problem>{problem}</p>}
      <div className="am-form__row">
        <button className="am-button" type="submit" disabled={pending || problem !== null} data-layout-save>{SAVE_LABEL}</button>
        <button className="am-button am-button--quiet" type="button" disabled={pending} onClick={props.onCancel}>{CANCEL_LABEL}</button>
      </div>
      {failure === null ? null : <HostFailure failure={failure} title="Набор моделей не сохранён" />}
    </form>
  );
}

export interface LayoutEditorProps {
  readonly layout: StageModelLayout;
  readonly catalogue: ModelCatalogue | undefined;
  readonly availableModelIds: readonly string[];
  readonly onClose: () => void;
}

export function LayoutEditor({ layout, catalogue, availableModelIds, onClose }: LayoutEditorProps) {
  const revise = useReviseStageModelLayout();
  const keys = useCommandKey();
  const [draft, setDraft] = useState<LayoutDraft | null>(() => initialDraft(layout, catalogue, availableModelIds));
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  if (draft === null) {
    return (
      <p className="am-note" role="status" data-layout-no-models>{NO_AVAILABLE_MODELS}</p>
    );
  }

  const problem = draftProblem(draft, catalogue);

  async function save(current: LayoutDraft) {
    if (!draftChanged(current, layout)) {
      onClose();
      return;
    }
    setFailure(null);
    const body = draftRequest(current);
    try {
      await revise.mutateAsync({ body, idempotencyKey: keys.keyFor(JSON.stringify(body)) });
      keys.release();
      onClose();
    } catch (error) {
      const failed = layoutFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <LayoutEditorView
      draft={draft}
      catalogue={catalogue}
      availableModelIds={availableModelIds}
      currentKit={layout.current?.kit}
      pending={revise.isPending}
      problem={problem}
      failure={failure}
      onKit={(kit) => setDraft((was) => (was === null ? was : chooseKit(was, kit)))}
      onModel={(key, id) => setDraft((was) => (was === null ? was : setCellModel(was, key, id, catalogue)))}
      onEffort={(key, effort) => setDraft((was) => (was === null ? was : setCellEffort(was, key, effort)))}
      onLimit={(key, field, value) => setDraft((was) => (was === null ? was : setCellLimit(was, key, field, value)))}
      onSave={() => void save(draft)}
      onCancel={onClose}
    />
  );
}
