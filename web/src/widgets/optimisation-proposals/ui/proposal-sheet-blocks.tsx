'use client';

/**
 * `UI-B-09`: the block strip of the sheet a proposal names, behind a press.
 *
 * The original opens a row of the proposals table to the thumbnails of the blocks of its sheet; a press on one opens
 * the block. This is that press: «Блоки листа» on the card opens the portal-blocks widget on the proposal's page of the
 * pass's version, and the widget's own tiles and block view do the rest. Nothing is read until the press: the version
 * (its manifest tells a bundle that no run has reached from a bare PDF) and the portal blocks are asked for only
 * once the strip is open, so a pass of a hundred proposals adds no request to its first render.
 */

import { useState } from 'react';

import type { ProjectUid, VersionUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { useDocumentVersion } from '@/entities/document-version';
import { PortalBlocks } from '@/widgets/portal-blocks';

import styles from './optimisation-proposals.module.css';

export interface ProposalSheetBlocksProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** The sheet's page of the version's PDF, as the proposal names it. */
  readonly page: number;
}

/** What the open strip reads: the version, then its blocks, narrowed to the page. Exported so a static render can see it open. */
export function ProposalSheetBlocksBody({ projectUid, versionUid, page }: ProposalSheetBlocksProps) {
  const version = useDocumentVersion(versionUid);
  if (version.isPending) return <LoadingState what="блоки листа" />;
  if (version.data === undefined) {
    const failure = failureMessage(version.error);
    return (
      <ErrorState
        title="Версия не прочитана: блоков листа нет"
        detail={failure.detail}
        correlationId={failure.correlationId}
        onRetry={() => void version.refetch()}
      />
    );
  }
  return (
    <PortalBlocks
      version={{ version_uid: versionUid, project_uid: projectUid, input_manifest: version.data.input_manifest }}
      page={page}
    />
  );
}

export function ProposalSheetBlocks(props: ProposalSheetBlocksProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.sheetBlocks} data-proposal-sheet-blocks={props.page}>
      <button
        type="button"
        className="am-button am-button--quiet am-button--small"
        aria-expanded={open}
        title={`Блоки страницы ${props.page} PDF версии`}
        onClick={() => setOpen(!open)}
      >
        Блоки листа
      </button>
      {open ? <ProposalSheetBlocksBody {...props} /> : null}
    </div>
  );
}
