/**
 * Public API of the `comparison-viewer` widget (`CMP-VIEWER-01`): the overlay viewer of one sheet pair.
 *
 * Mounted by `CMP-VC-UI-01`; this lane does not mount it on a route.
 */

export { ComparisonViewer } from './ui/comparison-viewer';
export type { ComparisonViewerProps } from './ui/comparison-viewer';
export { ComparisonViewerView } from './ui/comparison-viewer-view';
export type { ComparisonViewerViewProps, TileStatus, ViewerNavigation } from './ui/comparison-viewer-view';
export { ChannelStrip, HowCompared, ServiceNotes, TextChanges } from './ui/evidence-panels';
export { DifferenceList } from './ui/difference-list';

export { canShowOverlay, viewerGeometry } from './model/geometry';
export type { ViewerGeometry } from './model/geometry';
export { DEFAULT_LAYERS, LAYER_LABELS, LAYER_ORDER, STATUS_LABELS, regionClassLabel } from './model/labels';
export { initialState, reduce } from './model/viewer-state';
export type { ViewerAction, ViewerContext, ViewerState } from './model/viewer-state';

// `CMP-VC-UI-02`: the side panel «Изменения в листе» and the banner of the evidence it cites.
export type { ChangesPanelProps, ChangesPanelViewProps } from './ui/changes-panel';
export {
  ChangesPanel,
  ChangesPanelView,
  ENGINE_SAME_TEXT,
  NOT_PROCESSED_TEXT,
  NO_CHANGES_TEXT,
  PANEL_TITLE,
  STALE_TEXT,
  WHOLE_SPEC_NOTE,
  sheetTitleOf,
} from './ui/changes-panel';
export type { EvidenceAction, EvidenceState } from './ui/evidence-banner';
export { EvidenceBanner } from './ui/evidence-banner';
