/** Read-only authenticated report + original PDF export; callers own the download action. */
export { buildEvidencePackage, EvidencePackageError } from './model/package';
export type {
  EvidencePackageErrorCode,
  EvidencePackageOptions,
  EvidencePackageProgress,
  EvidencePackageReport,
  EvidencePackageSource,
} from './model/package';
