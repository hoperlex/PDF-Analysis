/**
 * The sheet viewer as markup (`CMP-VIEWER-01`, plan §1.1): the controls, the pane or panes, and the evidence beside them.
 *
 * It takes the pair, the state the island keeps, the tiles that have arrived and the handlers, and draws them; it owns no
 * state, starts no request and reads no environment, so the contrast census and the language guards render the same
 * markup the reader gets (the shape of `PortalBlockListView`).
 */

import type { HTMLAttributes, ReactNode, Ref } from 'react';

import type { ComparisonLayer, ComparisonPageRef, ComparisonSheetPair } from '@/shared/api';
import { pairReasonWords } from '@/entities/version-series';

import { shownIndices } from '../model/differences';
import type { ViewerGeometry } from '../model/geometry';
import { LAYER_LABELS, LAYER_ORDER, SCAN_NOTE, SIDE_WORDS, SPLIT_PART_NOTE, SPLIT_WHOLE_NOTE, STATUS_LABELS } from '../model/labels';
import type { Side } from '../model/labels';
import { type SheetKind, type SheetTiles, shownKinds, sheetTiles } from '../model/requests';
import type { TileRequest } from '../model/tile-loader';
import { type ViewerAction, type ViewerContext, type ViewerState, filterOf, paneOf } from '../model/viewer-state';

import { DifferenceList } from './difference-list';
import { EvidenceBanner } from './evidence-banner';
import type { EvidenceAction, EvidenceState } from './evidence-banner';
import { ChannelStrip, HowCompared, ServiceNotes, TextChanges } from './evidence-panels';
import { type BoxView, type EvidenceBoxView, type PaneLayer, SheetPane } from './sheet-pane';
import styles from './comparison-viewer.module.css';

export interface ViewerNavigation {
  readonly onPrevious?: () => void;
  readonly onNext?: () => void;
  readonly onClose?: () => void;
}

export interface TileStatus {
  readonly urlOf: (request: TileRequest) => string | null;
  readonly failed: number;
  readonly pending: number;
  readonly retry: () => void;
}

export interface ComparisonViewerViewProps {
  readonly pair: ComparisonSheetPair;
  /** `null`: the pair has no sheet the viewer can draw (no canvas, no resolution, no size passed). */
  readonly geometry: ViewerGeometry | null;
  readonly context: ViewerContext;
  readonly state: ViewerState;
  readonly tiles: TileStatus;
  readonly dispatch: (action: ViewerAction) => void;
  readonly navigation?: ViewerNavigation;
  readonly stageRef?: Ref<HTMLDivElement>;
  readonly paneHandlers?: HTMLAttributes<HTMLDivElement>;
  readonly dragging?: boolean;
  /** `CMP-VC-UI-02`: the side panel «Изменения в листе» (a node handed in by the island) and the evidence it focused. */
  readonly sidePanel?: ReactNode;
  readonly evidence?: EvidenceState | null;
  readonly onEvidence?: (action: EvidenceAction) => void;
}

const BADGE_TONE: Readonly<Record<string, string>> = {
  same: 'ok',
  same_zones_changed: 'degraded',
  different: 'active',
  needs_review: 'degraded',
  added: 'inert',
  removed: 'inert',
  unmatched: 'inert',
};

/** «Было: л. 5 · План освещения» and «Стало: нет в этой версии»: the sheet of one side, by its place in the pair. */
function sheetName(side: Side, page: ComparisonPairPageLike | undefined): string {
  if (page === undefined) return `${SIDE_WORDS[side]}: нет в этой версии`;
  const number = page.sheet_number === undefined ? `стр. ${(page.page as ComparisonPageRef).page_number}` : `л. ${page.sheet_number}`;
  return `${SIDE_WORDS[side]}: ${number}${page.title === undefined ? '' : ` · ${page.title}`}`;
}

type ComparisonPairPageLike = NonNullable<ComparisonSheetPair['page_a']>;

function Choice({ checked, disabled, title, layer, onChange, children }: { checked: boolean; disabled?: boolean | undefined; title?: string | undefined; layer?: ComparisonLayer | undefined; onChange: (on: boolean) => void; children: ReactNode }) {
  return (
    <label
      className={disabled === true ? `${styles.choice} ${styles.choiceOff}` : styles.choice}
      title={title}
      {...(layer === undefined ? {} : { 'data-layer': layer })}
    >
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      {children}
    </label>
  );
}

export function ComparisonViewerView({
  pair, geometry, context, state, tiles, dispatch, navigation, stageRef, paneHandlers, dragging, sidePanel, evidence, onEvidence,
}: ComparisonViewerViewProps) {
  const differences = pair.differences ?? [];
  const alignedBlocks = pair.how_compared?.aligned_blocks ?? 0;
  const status = pair.status;
  const notes: string[] = [];
  if (pair.page_a?.scan === true || pair.page_b?.scan === true) notes.push(SCAN_NOTE);
  if (pair.parts !== undefined && pair.parts.role === 'part') notes.push(`${SPLIT_PART_NOTE}; листы-части покрывают ${Math.round(pair.parts.covered_percent)} % прежнего листа`);
  if (pair.parts !== undefined && pair.parts.role === 'whole' && pair.parts.parts.length > 0) notes.push(SPLIT_WHOLE_NOTE);

  let stage: ReactNode;
  if (geometry === null) {
    // Plain markup, not a shared state block: a state block is a "branch" that `rendered-language.guard` requires one
    // of ITS OWN screens to render, and this widget's states are its own.
    stage = (
      <section className={styles.panel} aria-label="Лист нельзя показать" data-viewer-unavailable="">
        <h3 className={styles.panelTitle}>Лист нельзя показать</h3>
        <p className={styles.empty}>
          {pair.failure_reason !== undefined
            ? `Сравнение листа не удалось: ${pairReasonWords(pair.failure_reason)}.`
            : 'У листа нет результата сравнения, по которому известен его размер.'}
        </p>
      </section>
    );
  } else {
    const pane = paneOf(state, context);
    const kinds = shownKinds(state, context);
    const sheets = new Map<SheetKind, SheetTiles>(kinds.map((kind) => [kind, sheetTiles(kind, state, geometry.levels, pane)]));
    const indices = shownIndices(differences, filterOf(state));
    const boxes: BoxView[] = differences.flatMap((difference, index) =>
      state.selected === index || (state.showBoxes && indices.includes(index)) ? [{ index, difference, selected: state.selected === index }] : [],
    );
    const evidenceBoxes: EvidenceBoxView[] =
      evidence === null || evidence === undefined
        ? []
        : evidence.items.flatMap((item, index) =>
            evidence.all || index === evidence.index ? [{ id: item.id, box: item.box, current: index === evidence.index }] : [],
          );
    const paneFor = (label: string, layers: PaneLayer[], divider?: number) => (
      <SheetPane
        key={label}
        label={label}
        layers={layers}
        view={state.view}
        dpi={geometry.dpi}
        urlOf={tiles.urlOf}
        boxes={boxes}
        evidence={evidenceBoxes}
        {...(divider === undefined ? {} : { divider })}
        {...(dragging === undefined ? {} : { dragging })}
        {...(paneHandlers === undefined ? {} : { handlers: paneHandlers })}
      />
    );
    const panes =
      state.mode === 'side'
        ? kinds.map((kind) => paneFor(kind === 'a' ? SIDE_WORDS.a : SIDE_WORDS.b, [{ sheet: sheets.get(kind) as SheetTiles }]))
        : [
            paneFor(
              state.swipe ? `Шторка: слева — ${SIDE_WORDS[state.under].toLowerCase()}, справа — наложение` : 'Наложение',
              kinds.map((kind) => ({
                sheet: sheets.get(kind) as SheetTiles,
                ...(state.swipe && kind === 'overlay' ? { clipLeft: state.swipePosition } : {}),
              })),
              state.swipe ? state.swipePosition : undefined,
            ),
          ];
    stage = (
      <>
        <div className={styles.toolbar} role="toolbar" aria-label="Управление просмотром">
          <fieldset className={styles.group}>
            <legend className={styles.groupTitle}>Вид</legend>
            <button type="button" aria-pressed={state.mode === 'overlay'} disabled={!context.canOverlay}
              title={context.canOverlay ? undefined : 'Наложения нет: листы не были совмещены'}
              className={`am-button am-button--quiet am-button--small ${styles.modeButton} ${state.mode === 'overlay' ? styles.modeButtonOn : ''}`.trim()}
              onClick={() => dispatch({ type: 'mode', mode: 'overlay' })}>Наложение</button>
            <button type="button" aria-pressed={state.mode === 'side'}
              className={`am-button am-button--quiet am-button--small ${styles.modeButton} ${state.mode === 'side' ? styles.modeButtonOn : ''}`.trim()}
              onClick={() => dispatch({ type: 'mode', mode: 'side' })}>Рядом</button>
            <Choice checked={state.swipe} disabled={state.mode === 'side'} title={state.mode === 'side' ? 'Шторка работает только в наложении' : 'Ползунок под листом: тяните вправо — верхний лист скрывается, открывается нижний'}
              onChange={(on) => dispatch({ type: 'swipe', on })}>шторка</Choice>
            {state.swipe ? (
              <>
                <label className={styles.choice}><input type="radio" name="under" checked={state.under === 'a'} onChange={() => dispatch({ type: 'under', under: 'a' })} />под ней — {SIDE_WORDS.a.toLowerCase()}</label>
                <label className={styles.choice}><input type="radio" name="under" checked={state.under === 'b'} onChange={() => dispatch({ type: 'under', under: 'b' })} />под ней — {SIDE_WORDS.b.toLowerCase()}</label>
              </>
            ) : null}
          </fieldset>
          <fieldset className={styles.group}>
            <legend className={styles.groupTitle}>Масштаб</legend>
            <button type="button" className="am-button am-button--quiet am-button--small" aria-label="Уменьшить" onClick={() => dispatch({ type: 'zoom', factor: 1 / 1.25 })}>−</button>
            <span className={styles.zoom}>{Math.round(state.view.zoom * 100)} %</span>
            <button type="button" className="am-button am-button--quiet am-button--small" aria-label="Увеличить" onClick={() => dispatch({ type: 'zoom', factor: 1.25 })}>＋</button>
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => dispatch({ type: 'fit' })}>Вписать</button>
          </fieldset>
          {state.mode === 'overlay' ? (
            <fieldset className={styles.group}>
              <legend className={styles.groupTitle}>Слои</legend>
              {LAYER_ORDER.map((layer: ComparisonLayer) => (
                <Choice key={layer} layer={layer} checked={state.layers.includes(layer)} onChange={(on) => dispatch({ type: 'layer', layer, on })}>
                  {LAYER_LABELS[layer]}
                </Choice>
              ))}
            </fieldset>
          ) : null}
          <fieldset className={styles.group}>
            <legend className={styles.groupTitle}>Отличия на листе</legend>
            <Choice checked={state.showBoxes} onChange={(on) => dispatch({ type: 'boxes', on })}>рамки отличий</Choice>
            <Choice checked={state.alignBlocks} disabled={alignedBlocks === 0}
              title={alignedBlocks === 0 ? 'Движения блоков не найдено: совмещать нечего' : 'Показать перемещённые блоки нового листа на их местах, не меняя PDF'}
              onChange={(on) => dispatch({ type: 'align', on })}>
              Совмещать блоки{alignedBlocks > 0 ? ` (${alignedBlocks})` : ''}
            </Choice>
          </fieldset>
          {navigation === undefined ? null : (
            <fieldset className={styles.group}>
              <legend className={styles.groupTitle}>Листы</legend>
              <button type="button" className="am-button am-button--quiet am-button--small" disabled={navigation.onPrevious === undefined} onClick={navigation.onPrevious}>‹ лист</button>
              <button type="button" className="am-button am-button--quiet am-button--small" disabled={navigation.onNext === undefined} onClick={navigation.onNext}>лист ›</button>
              {navigation.onClose === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={navigation.onClose}>✕ Закрыть</button>}
            </fieldset>
          )}
        </div>
        <div className={styles.stage} ref={stageRef} tabIndex={0} aria-label="Лист: стрелки влево и вправо переходят между отличиями">
          {panes}
        </div>
        {tiles.failed > 0 ? (
          <p className={`${styles.progress} ${styles.progressFailed}`} role="alert">
            Не загружено плиток: {tiles.failed}.{' '}
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={tiles.retry}>Повторить</button>
          </p>
        ) : tiles.pending > 0 ? (
          <p className={styles.progress} role="status">Загружается плиток: {tiles.pending}</p>
        ) : null}
        {state.swipe && state.mode === 'overlay' ? (
          <div className={styles.swipe}>
            <label htmlFor="comparison-viewer-swipe">Положение шторки: тяните вправо — верхний лист скрывается, открывается нижний</label>
            <input id="comparison-viewer-swipe" className={styles.slider} type="range" min={0} max={100} value={state.swipePosition}
              onChange={(event) => dispatch({ type: 'swipe-position', position: Number(event.target.value) })} />
          </div>
        ) : null}
      </>
    );
  }

  return (
    <div className={styles.viewer} data-comparison-viewer="" data-mode={state.mode}>
      <header className={styles.header}>
        <h2 className={styles.sheetName}><span className={styles.sheetSide}>{sheetName('a', pair.page_a)}</span></h2>
        <h2 className={styles.sheetName}><span className={styles.sheetSide}>{sheetName('b', pair.page_b)}</span></h2>
        <div className={styles.facts}>
          {status === undefined ? null : <span className={`am-badge am-badge--${BADGE_TONE[status] ?? 'inert'}`}>{STATUS_LABELS[status]}</span>}
          {pair.ai_dependent === true ? <span className="am-badge am-badge--inert">пара связана с участием ИИ</span> : null}
        </div>
      </header>
      {notes.length === 0 ? null : (
        <ul className={styles.notes}>{notes.map((note) => <li key={note} className={styles.note}>{note}</li>)}</ul>
      )}
      {evidence === null || evidence === undefined || onEvidence === undefined ? null : <EvidenceBanner evidence={evidence} onAction={onEvidence} />}
      <div className={sidePanel === undefined ? undefined : `${styles.layout} ${styles.layoutWide}`} {...(sidePanel === undefined ? {} : { 'data-viewer-layout': 'with-panel' })}>
      <div className={sidePanel === undefined ? undefined : styles.main}>
      {stage}
      <div className={styles.panels}>
        <ChannelStrip channels={pair.channels} reasons={pair.reasons ?? []} />
        <DifferenceList
          differences={differences}
          filter={filterOf(state)}
          selected={state.selected}
          onSelect={(index) => dispatch({ type: 'select', index })}
          onStep={(direction) => dispatch({ type: 'step', direction })}
          onShifts={(on) => dispatch({ type: 'shifts', on })}
          onStyleOnly={(on) => dispatch({ type: 'style-only', on })}
        />
        <TextChanges
          changes={pair.text_changes ?? []}
          onFocus={(change) => (change.box === undefined ? undefined : dispatch({ type: 'focus-box', box: change.box }))}
        />
        <ServiceNotes notes={pair.service_notes ?? []} />
        <HowCompared how={pair.how_compared} />
      </div>
      </div>
      {sidePanel}
      </div>
    </div>
  );
}
