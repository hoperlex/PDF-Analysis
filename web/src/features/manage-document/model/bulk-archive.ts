/**
 * Archive several documents at once, each by its own command (`UIP-S02-04`, `R-151a`).
 *
 * The original's «Изменить (N)» hides the chosen cards in one window; ours sends the existing archive command (`setDocumentArchived`,
 * contract 1.22.0) once per document, in the order they were chosen, each under its own idempotency key, so a document the server
 * refused does not take the others with it and a retry of the refused ones is a retry, not a new command. Nothing is deleted: the
 * versions, runs and decisions of an archived document stay, and the document comes back with «Показать архивные» and «Вернуть из архива».
 *
 * Pure: the command, the key and the wording of a failure are passed in, so a test can state each outcome. The hook that holds the
 * keys and the cache is `use-archive-documents.ts`.
 */

import type { DocumentUid, DocumentVersion } from '@/shared/api';

/** One document to archive: its identity (never its title) and the name the report calls it by. */
export interface ArchiveTarget {
  readonly documentUid: DocumentUid;
  readonly title: string;
}

export interface ArchiveFailure {
  readonly target: ArchiveTarget;
  /** The Russian sentence for why the server did not archive it. */
  readonly reason: string;
}

/** What one pass did: every document of the pass is in exactly one of the two lists. */
export interface ArchiveReport {
  readonly total: number;
  readonly archived: readonly ArchiveTarget[];
  readonly failed: readonly ArchiveFailure[];
}

export interface ArchiveProgress {
  /** Documents already answered, by the server or by a refusal. */
  readonly done: number;
  readonly total: number;
}

/** One archive command for one document, under the key it was given; resolves with the document's version as the server holds it. */
export type ArchiveSend = (target: ArchiveTarget, idempotencyKey: string) => Promise<DocumentVersion>;

export interface ArchiveDocumentsArgs {
  readonly targets: readonly ArchiveTarget[];
  readonly send: ArchiveSend;
  /** The key of the intent «archive this document»: the same key for the same document until the intent is settled. */
  readonly keyOf: (target: ArchiveTarget) => string;
  /** The Russian reason for a thrown value. */
  readonly reasonOf: (error: unknown) => string;
  /** Told after each document, and the versions the server answered with, for the cache. */
  readonly onStep?: ((progress: ArchiveProgress, archived: DocumentVersion | null) => void) | undefined;
}

/**
 * One command per document, one after another. A document named twice is sent once. A refused document is listed with its reason and
 * the pass goes on; nothing here throws for a refusal.
 */
export async function archiveDocuments({ targets, send, keyOf, reasonOf, onStep }: ArchiveDocumentsArgs): Promise<ArchiveReport> {
  const unique = [...new Map(targets.map((target) => [target.documentUid, target])).values()];
  const archived: ArchiveTarget[] = [];
  const failed: ArchiveFailure[] = [];
  let done = 0;
  for (const target of unique) {
    let version: DocumentVersion | null = null;
    try {
      version = await send(target, keyOf(target));
      archived.push(target);
    } catch (error) {
      failed.push({ target, reason: reasonOf(error) });
    }
    done += 1;
    onStep?.({ done, total: unique.length }, version);
  }
  return { total: unique.length, archived, failed };
}

/** The one message at the end of a pass: «Убрано в архив: k из N». */
export function archiveReportLine(report: ArchiveReport): string {
  return `Убрано в архив: ${report.archived.length} из ${report.total}`;
}
