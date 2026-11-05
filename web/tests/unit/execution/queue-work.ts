/**
 * What a queue item says about the work (`UI-PARITY-QUEUE-A`, contract 1.18.0): the project, document and version
 * every job belongs to. They are required members of `ExecutionQueueItem`, so each fixture that builds an item spreads
 * this; a test about the readable row overrides the members it asserts on.
 */
export const QUEUE_WORK = {
  project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
  project_name: 'Школа № 7',
  document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  document_name: 'АР, лист 3',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
  version_ordinal: 2,
} as const;
