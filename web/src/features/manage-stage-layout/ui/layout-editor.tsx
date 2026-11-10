'use client';

/**
 * «Изменить» in «Модели по этапам» (`HOSTS-WEB-01`, plan 2026-11-09 §7.4; **administrator only**). The segments
 * «Только Claude · Только Codex · Свой набор», and for each of the six rows a model and an effort. «Дополнительно» holds the
 * answer limit and the timeout of every cell.
 *
 * **What the form offers.** A set only when every model it names can be served now; a model only when some server can serve
 * it (and the model already in the cell, so the draft never drops what is in force); an effort only from the catalogue's
 * list for the model. The blocks row is not a model and an effort: it is **one scheme of a closed list of three** (an Opus leg and
 * a Sonnet judge, two Codex legs and a judge, or one Astra), chosen in one select, and its legs and judge are never edited one by
 * one (`HOSTS-ENSEMBLE-01`). The server checks every pair and the scheme again, and a refusal is said in words.
 *
 * **«Сравнение версий»** (`CMP-WEB-01`) is one small group of four rows, a model and an effort for each kind of work of the comparison
 * of versions that calls a model, and it is drawn under «Свой набор» **only**: with a named set the set's table applies and nothing is
 * drawn (fewer concepts on the screen). A custom revision stored without these cells shows the four rows empty and says the comparison will not
 * run; a kind is given a model only by the person. Their limit and timeout are in «Дополнительно» beside the others.
 *
 * One idempotency key per intent, kept for an explicit repeat after an unknown outcome and released when the command settles.
 */

import { useState } from 'react';

import type {
  ComparisonLayoutKind,
  ModelCatalogue,
  ModelEffort,
  StageComparisonCell,
  StageLayoutCell,
  StageModelKit,
  StageModelLayout,
} from '@/shared/api';
import { COMPARISON_LAYOUT_KIND_VALUES, MODEL_EFFORT_VALUES, STAGE_ROW_KEY_VALUES } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { modelLabel } from '@/entities/executor-host';
import {
  ADVANCED_SUMMARY,
  BLOCKS_SCHEME_LABEL,
  BLOCKS_SCHEME_UNLISTED,
  CANCEL_LABEL,
  COMPARISON_GROUP_TITLE,
  COMPARISON_KIND_HEADER,
  COMPARISON_KIND_LABELS,
  COMPARISON_NONE_NOTE,
  COMPARISON_NOT_CHOSEN,
  COMPARISON_NO_EFFORT,
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
  blockSchemeOf,
  effortsOf,
  layoutFailure,
  rowCells,
  sortedComparisonCells,
} from '@/entities/stage-layout';
import type { BlockScheme, BlockSchemeId } from '@/entities/stage-layout';
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
  offeredBlockSchemes,
  offeredKits,
  setBlockScheme,
  setCellEffort,
  setCellLimit,
  setCellModel,
  setComparisonEffort,
  setComparisonLimit,
  setComparisonModel,
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
  /**
   * The blocks row is chosen as one scheme of the closed list. Optional only for a view drawn to be read (the language and
   * contrast instruments render the view with the handlers they need); `LayoutEditor` always passes it.
   */
  readonly onScheme?: ((scheme: BlockSchemeId) => void) | undefined;
  readonly onEffort: (cellKey: string, effort: ModelEffort) => void;
  readonly onLimit: (cellKey: string, field: 'max_output_tokens' | 'timeout_seconds', value: number) => void;
  /**
   * A model, an effort and the limits of one kind of the comparison of versions. Optional only for a view drawn to be read, like `onScheme`;
   * `LayoutEditor` always passes them.
   */
  readonly onComparisonModel?: ((kind: ComparisonLayoutKind, modelId: string) => void) | undefined;
  readonly onComparisonEffort?: ((kind: ComparisonLayoutKind, effort: ModelEffort) => void) | undefined;
  readonly onComparisonLimit?: ((kind: ComparisonLayoutKind, field: 'max_output_tokens' | 'timeout_seconds', value: number) => void) | undefined;
  readonly onSave: () => void;
  readonly onCancel: () => void;
}

/** The blocks row: one select with the schemes the row may be, never a model and an effort per cell. */
function SchemeEditor({ cells, schemes, onScheme }: {
  readonly cells: readonly StageLayoutCell[];
  readonly schemes: readonly BlockScheme[];
  readonly onScheme: ((scheme: BlockSchemeId) => void) | undefined;
}) {
  const chosen = blockSchemeOf(cells);
  return (
    <select
      aria-label={`${BLOCKS_SCHEME_LABEL}: ${STAGE_ROW_LABELS.blocks}`}
      value={chosen === null ? '' : chosen.id}
      data-layout-scheme="blocks"
      onChange={(event) => onScheme?.(event.currentTarget.value as BlockSchemeId)}
    >
      {chosen === null ? <option value="" disabled>{BLOCKS_SCHEME_UNLISTED}</option> : null}
      {schemes.map((scheme) => <option key={scheme.id} value={scheme.id} data-layout-scheme-id={scheme.id}>{scheme.label}</option>)}
    </select>
  );
}

function RowEditor({ row, cells, schemes, ...props }: {
  readonly row: (typeof STAGE_ROW_KEY_VALUES)[number];
  readonly cells: readonly StageLayoutCell[];
  readonly schemes: readonly BlockScheme[];
} & Pick<LayoutEditorViewProps, 'catalogue' | 'availableModelIds' | 'onModel' | 'onEffort' | 'onScheme'>) {
  if (cells.length === 0) return <span className="am-note">нет данных</span>;
  if (row === 'blocks') return <SchemeEditor cells={cells} schemes={schemes} onScheme={props.onScheme} />;
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
          <option key={effort} value={effort} data-model-effort={effort}>{STAGE_EFFORT_LABELS[effort]}</option>
        ))}
      </select>
    </span>
  );
}

/** One kind of the comparison of versions: a model and an effort. A kind with no model shows «не выбрана» and an effort that cannot be chosen yet. */
function ComparisonRowEditor({ kind, cell, catalogue, availableModelIds, onModel, onEffort }: {
  readonly kind: ComparisonLayoutKind;
  readonly cell: StageComparisonCell | undefined;
  readonly catalogue: ModelCatalogue | undefined;
  readonly availableModelIds: readonly string[];
  readonly onModel: ((kind: ComparisonLayoutKind, modelId: string) => void) | undefined;
  readonly onEffort: ((kind: ComparisonLayoutKind, effort: ModelEffort) => void) | undefined;
}) {
  const name = `${COMPARISON_GROUP_TITLE} — ${COMPARISON_KIND_LABELS[kind]}`;
  const options = modelOptions(cell, catalogue, availableModelIds);
  const efforts: readonly ModelEffort[] = cell === undefined ? [] : MODEL_EFFORT_VALUES.filter((effort) => effortsOf(catalogue, cell.model_id).includes(effort));
  return (
    <span className="am-form__row" data-comparison-kind={kind}>
      <select
        aria-label={`${ROW_MODEL_LABEL}: ${name}`}
        value={cell === undefined ? '' : cell.model_id}
        data-layout-comparison-model={kind}
        onChange={(event) => onModel?.(kind, event.currentTarget.value)}
      >
        {cell === undefined ? <option value="" disabled>{COMPARISON_NOT_CHOSEN}</option> : null}
        {options.map((id) => <option key={id} value={id}>{modelLabel(id)}</option>)}
      </select>
      <select
        aria-label={`${ROW_EFFORT_LABEL}: ${name}`}
        value={cell === undefined ? '' : cell.effort}
        disabled={cell === undefined}
        data-layout-comparison-effort={kind}
        onChange={(event) => onEffort?.(kind, event.currentTarget.value as ModelEffort)}
      >
        {cell === undefined ? <option value="" disabled>{COMPARISON_NO_EFFORT}</option> : null}
        {cell === undefined ? null : (efforts.includes(cell.effort) ? efforts : [cell.effort, ...efforts]).map((effort) => (
          <option key={effort} value={effort} data-model-effort={effort}>{STAGE_EFFORT_LABELS[effort]}</option>
        ))}
      </select>
    </span>
  );
}

/** «Сравнение версий»: four rows, drawn under «Свой набор» only. With no model chosen it says the comparison will not run. */
function ComparisonGroup({ cells, catalogue, availableModelIds, onModel, onEffort }: {
  readonly cells: readonly StageComparisonCell[];
  readonly catalogue: ModelCatalogue | undefined;
  readonly availableModelIds: readonly string[];
  readonly onModel: ((kind: ComparisonLayoutKind, modelId: string) => void) | undefined;
  readonly onEffort: ((kind: ComparisonLayoutKind, effort: ModelEffort) => void) | undefined;
}) {
  return (
    <section role="group" aria-label={COMPARISON_GROUP_TITLE} className={styles.comparison} data-layout-comparison-group>
      {cells.length === 0 ? <p className="am-note" data-layout-comparison-none>{COMPARISON_NONE_NOTE}</p> : null}
      <Table<ComparisonLayoutKind>
        caption={COMPARISON_GROUP_TITLE}
        rowKey={(kind) => kind}
        rows={COMPARISON_LAYOUT_KIND_VALUES}
        columns={[
          { key: 'kind', header: COMPARISON_KIND_HEADER, cell: (kind) => COMPARISON_KIND_LABELS[kind] },
          {
            key: 'model',
            header: `${ROW_MODEL_LABEL} · ${ROW_EFFORT_LABEL.toLowerCase()}`,
            cell: (kind) => (
              <ComparisonRowEditor
                kind={kind}
                cell={cells.find((cell) => cell.work_kind === kind)}
                catalogue={catalogue}
                availableModelIds={availableModelIds}
                onModel={onModel}
                onEffort={onEffort}
              />
            ),
          },
        ]}
      />
    </section>
  );
}

export function LayoutEditorView(props: LayoutEditorViewProps) {
  const { draft, catalogue, availableModelIds, currentKit, pending, problem, failure } = props;
  const kits = offeredKits(catalogue, availableModelIds, currentKit);
  const noChoice = availableModelIds.length === 0;
  const rows = STAGE_ROW_KEY_VALUES.map((row) => ({ row, cells: rowCells(draft.cells, row) }));
  const schemes = offeredBlockSchemes(draft, catalogue, availableModelIds);
  // A named set applies its own table, and nothing of the comparison is drawn; «Свой набор» is where it is seen and changed.
  const comparison = draft.kit === 'custom' ? sortedComparisonCells(draft.comparison ?? []) : null;
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
              <RowEditor
                row={entry.row}
                cells={entry.cells}
                schemes={schemes}
                catalogue={catalogue}
                availableModelIds={availableModelIds}
                onModel={props.onModel}
                onEffort={props.onEffort}
                onScheme={props.onScheme}
              />
            ),
          },
        ]}
      />
      {comparison === null ? null : (
        <ComparisonGroup
          cells={comparison}
          catalogue={catalogue}
          availableModelIds={availableModelIds}
          onModel={props.onComparisonModel}
          onEffort={props.onComparisonEffort}
        />
      )}
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
          {(comparison ?? []).map((cell) => (
            <li key={cell.work_kind} className={styles.limit} data-layout-comparison-limits={cell.work_kind}>
              <strong>{`${COMPARISON_GROUP_TITLE} · ${COMPARISON_KIND_LABELS[cell.work_kind]}`}</strong>
              <label>
                {TOKENS_LABEL}{' '}
                <input
                  className={styles.number}
                  type="number"
                  min={1}
                  max={65536}
                  value={cell.max_output_tokens}
                  onChange={(event) => props.onComparisonLimit?.(cell.work_kind, 'max_output_tokens', Number(event.currentTarget.value))}
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
                  onChange={(event) => props.onComparisonLimit?.(cell.work_kind, 'timeout_seconds', Number(event.currentTarget.value))}
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
      onScheme={(scheme) => setDraft((was) => (was === null ? was : setBlockScheme(was, scheme)))}
      onEffort={(key, effort) => setDraft((was) => (was === null ? was : setCellEffort(was, key, effort)))}
      onLimit={(key, field, value) => setDraft((was) => (was === null ? was : setCellLimit(was, key, field, value)))}
      onComparisonModel={(kind, id) => setDraft((was) => (was === null ? was : setComparisonModel(was, kind, id, catalogue)))}
      onComparisonEffort={(kind, effort) => setDraft((was) => (was === null ? was : setComparisonEffort(was, kind, effort)))}
      onComparisonLimit={(kind, field, value) => setDraft((was) => (was === null ? was : setComparisonLimit(was, kind, field, value)))}
      onSave={() => void save(draft)}
      onCancel={onClose}
    />
  );
}
