/** Read-only authenticated report + original PDF export; callers own the download action. */
export { buildEvidencePackage, EvidencePackageError } from './model/package';
// `UIP-S02-05`: several finished packages in one ZIP, with an index of what each is.
export { buildEvidenceBundle, EVIDENCE_BUNDLE_MAX_BYTES, EVIDENCE_BUNDLE_MAX_FILES } from './model/package';
export type {
  EvidenceBundleFile,
  EvidenceBundleOptions,
  EvidencePackageErrorCode,
  EvidencePackageOptions,
  EvidencePackageProgress,
  EvidencePackageReport,
  EvidencePackageSource,
} from './model/package';
