/** Public API of the `set-vendor-list` feature (`W60-PRICE-LIST-01`). */

export type {
  SetGlobalVendorListCommand,
  SetProjectVendorListCommand,
} from './model/use-set-vendor-list';
export { useSetGlobalVendorList, useSetProjectVendorList } from './model/use-set-vendor-list';

export type { VendorListEditorProps } from './ui/vendor-list-editor';
export {
  VENDOR_LIST_MAX_ENTRIES,
  VendorListEditor,
  draftProblem,
  entriesOf,
} from './ui/vendor-list-editor';
