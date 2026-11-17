/** Public API of the `section-detail` page slice: one section of one project (`R-151l`). */

export type { SectionDetailPageProps } from './ui/section-detail-page';
export { SectionDetailPage, sectionPageTitle } from './ui/section-detail-page';
// `UI-A-35`: «Выбрать все» over the whole listing — the row and the walk behind it, for the static harnesses.
export type { SectionHeaderProps } from './ui/section-header';
export { SectionHeader, objectHomeHref } from './ui/section-header';
export type { SectionBatchBarProps } from './ui/section-batch-bar';
export { SectionBatchBar } from './ui/section-batch-bar';
export type { SectionSelectionBarProps } from './ui/section-selection-bar';
export { SectionSelectionBar } from './ui/section-selection-bar';
export type { ListingScope, ListingWalk } from './model/use-listing-walk';
export { useListingWalk } from './model/use-listing-walk';
export type { SectionChoices } from './model/section-choices';
export { sectionChoices, wholeListing } from './model/section-choices';
// `UIP-S02-06`: the section's cards by group, made of the whole listing.
export type { DocumentGroup } from './model/group-documents';
export { GROUP_NAME_MAX_LENGTH, NO_GROUP_LABEL, groupDocuments, groupOf, orderGroupNames } from './model/group-documents';
export type { GroupDrop, GroupsWalkNoteProps, SectionGroupGrid, SectionGroupsProps } from './ui/section-groups';
export { GroupsWalkNote, SectionGroup, SectionGroups } from './ui/section-groups';
// `UIP-S02-07`: moving a document into a group, by dragging its card or by «Группа…» in the card's menu.
export type {
  DragSource, EditingAction, EditingState, GroupAnswer, GroupChoice, GroupRequest, MoveNotice, PendingMove,
} from './model/group-move';
export {
  EDITING_IDLE, dragSourceOf, dropRequest, editingReducer, movedSentence, movingSentence, newGroupProblem, refusedSentence,
  resolveGroupChoice,
} from './model/group-move';
export type { GroupDialogProps, KnownGroup } from './ui/group-dialog';
export {
  GROUP_DIALOG_CANCEL_LABEL, GROUP_DIALOG_SAVE_LABEL, GROUP_DIALOG_TITLE, GroupDialog, NEW_GROUP_LABEL,
} from './ui/group-dialog';
export type { GroupEditing, GroupEditingInput, GroupEditingLayerProps } from './ui/group-editing';
export { GROUP_MENU_ITEM_LABEL, GroupEditingLayer, useGroupEditing } from './ui/group-editing';
