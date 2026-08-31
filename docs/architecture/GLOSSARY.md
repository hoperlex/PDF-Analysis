# Domain glossary

| Term | Meaning | Important distinction |
|---|---|---|
| Object | верхнеуровневая группа/строительный объект | не filesystem folder |
| Discipline | профиль/раздел проектирования | display code/name not identity |
| Project | рабочий контейнер пользователя | может иметь many documents/versions |
| Document | логическая документация/чертёжный комплект | identity persists across versions |
| DocumentVersion | immutable published input state | new source/correction → new version |
| Blob | durable bytes with checksum/media metadata | S3 key hidden; blob_id is identity |
| InputManifest | immutable list/roles/checksums of run input | not a directory listing |
| AuditRun | business history of one audit execution/result request | not Job or Attempt |
| Job | durable schedulable work item | may have retries/attempts |
| Attempt | one concrete leased execution with fencing token | stale attempt cannot publish |
| Stage | versioned transformation with declared inputs/outputs | stage registry single source |
| Finding | stable semantic issue identity | display `F-NNN` is not key |
| FindingObservation | run-specific evidence/occurrence of a Finding | page/geometry/stage provenance |
| ExpertDecision | append-only human verdict event | current verdict is projection |
| Knowledge Base | rebuildable projection/index over accepted evidence/decisions | not independent write model |
| AnalysisProfile | immutable routing/model/parameter configuration | not current `.env`/UI dropdown |
| PromptBundle | content-addressed prompt set/version | not mutable folder name |
| NormsSnapshot | versioned authoritative norm dataset/provenance | not LLM memory |
| ModelCallRecord | immutable evidence/usage/cost record of provider call | diagnostic log is insufficient |
| Comparison | relationship/workspace for two versions/documents | owns revisions, not source docs |
| SuggestionSet | rebuildable automatic sheet-link suggestions | cannot overwrite approved links |
| SheetLink | user-approved mapping/unlinked state revision | authoritative comparison mapping |
| Raw comparison evidence | deterministic exclusion/diff/graphic artifacts | immutable per source/config revision |
| Derived AI synthesis | AI review/summary keyed to raw checksums | additive, not authority |
| Worker | remote execution capability endpoint/agent | never canonical metadata writer |
| Checkpoint | accepted integration commit + contract/migration/build/manual/automated evidence | tag alone is not checkpoint |
