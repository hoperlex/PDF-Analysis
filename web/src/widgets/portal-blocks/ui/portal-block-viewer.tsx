'use client';

/** @jsxRuntime automatic */

/**
 * The block view: one portal block over the whole screen (`UI-PARITY`, «Блоки»).
 *
 * The original's block view is the model — 94vh, at most 1440px; the image on the left with a wheel
 * zoom, ‹ › with «i / n» within the page selection the reader came from, a 380px panel on the right,
 * closed by ×, Esc or a click outside. The panel carries what the API gives for the block (the
 * portal's status, the recognised text with its flags, the portal's description, each marked as what
 * it is) and, when the run's findings were read, the findings whose evidence sits in the block (with the server's block
 * links, `UI-PARITY-C6`) or, without them, the findings that cite the block's page.
 *
 * **«i / n» is within the selection**, the page chosen above the tiles or all of them; ‹ and › stop
 * at either end and do not wrap. The arrow keys do the same.
 *
 * A native modal `<dialog>`, as the review screen's full-screen view is: the browser keeps focus
 * inside, Esc closes it and the screen behind is inert. Where `showModal` is missing (a static render,
 * the unit suite) it is drawn open as it is, which is what the styling census needs; `staticOpen` says so.
 */

import { useEffect, useRef } from 'react';
import Link from 'next/link';

import type { PortalBlock, ProjectUid, RunId, VersionUid } from '@/shared/api';
import { portalBlockCropUrl } from '@/shared/api';
import { routes } from '@/shared/lib';
import { SeverityBadge } from '@/entities/finding';
import { portalBlockTypeLabel, stepIndex } from '@/entities/block';

import type { PageFindings } from '../model/page-findings';
import { runSourcePhrase } from '../model/page-findings';
import { BlockImageStage } from './block-image-stage';
import { PortalBlockCard } from './portal-block-card';
import styles from './portal-block-viewer.module.css';

export interface PortalBlockViewerProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** The blocks of the selection the reader is walking, in tile order. */
  readonly blocks: readonly PortalBlock[];
  /** The open block's place in `blocks`. */
  readonly index: number;
  readonly onIndex: (index: number) => void;
  readonly onClose: () => void;
  /** The open block's findings (`scope: 'block'`) or its page's in the run's findings, or `null` when no number may be said. */
  readonly pageFindings: PageFindings | null;
  /** The run the findings belong to. */
  readonly runId: RunId | null;
  /** When that run started; the panel says which run the count is from. */
  readonly runAt?: string | undefined;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

/**
 * «Замечания в блоке» (the findings whose evidence sits in the block) or «Замечания на странице N» (the findings that cite
 * the page, honestly not the block's, when the run's block links are not known).
 */
function PageFindingsPanel({
  projectUid,
  runId,
  runAt,
  page,
  reading,
}: {
  readonly projectUid: ProjectUid;
  readonly runId: RunId;
  readonly runAt: string | undefined;
  readonly page: number;
  readonly reading: PageFindings;
}) {
  const source = runSourcePhrase(runAt);
  const block = reading.scope === 'block';
  return (
    <section
      className={styles.findings}
      aria-label={block ? 'Замечания в блоке' : 'Замечания на странице'}
      data-page-findings-panel={reading.count}
      {...(block ? { 'data-findings-scope': 'block' } : {})}
    >
      <h4 className={styles.findingsTitle}>{block ? `Замечания в блоке (${reading.count})` : `Замечания на странице ${page} (${reading.count})`}</h4>
      <p className={styles.findingsNote}>
        {block
          ? 'Замечания прогона, цитата которых лежит в этом блоке'
          : 'Замечание указывает страницу PDF, а не блок: прогон не называет блок портала, поэтому здесь все замечания, в которых есть цитата с этой страницы'}
        {source === null ? null : <> ({source})</>}.
      </p>
      {reading.count === 0 ? (
        <p className={styles.findingsNote}>
          {block ? 'Ни одно замечание прогона не привязано к этому блоку по положению цитаты.' : 'Ни в одном замечании прогона нет цитаты с этой страницы.'}
        </p>
      ) : (
        <ul className={styles.findingList}>
          {reading.findings.map((finding) => (
            <li key={finding.finding_uid} className={styles.finding} data-finding-uid={finding.finding_uid}>
              {finding.decided_severity === undefined ? null : (
                <SeverityBadge severity={finding.decided_severity} title="Важность, решённая экспертом" />
              )}
              <span className={styles.findingText}>{finding.observation.finding_text}</span>{' '}
              <Link
                className={styles.findingLink}
                href={`${routes.review(projectUid, runId)}?${new URLSearchParams({ finding: finding.finding_uid }).toString()}`}
              >
                Открыть в разборе
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function PortalBlockViewer({
  projectUid,
  versionUid,
  blocks,
  index,
  onIndex,
  onClose,
  pageFindings,
  runId,
  runAt,
  staticOpen = false,
}: PortalBlockViewerProps) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const element = dialog.current;
    if (element === null || staticOpen || typeof element.showModal !== 'function') return;
    if (!element.open) element.showModal();
    const closed = () => {
      closeRef.current();
    };
    element.addEventListener('close', closed);
    return () => {
      element.removeEventListener('close', closed);
      if (element.open) element.close();
    };
  }, [staticOpen]);

  const block = blocks[index];
  if (block === undefined) return null;

  const previous = stepIndex(index, blocks.length, -1);
  const next = stepIndex(index, blocks.length, 1);
  const typeLabel = portalBlockTypeLabel(block.block_type);
  const caption = `${typeLabel} · стр. ${block.page_number}`;
  const crop = block.crop;
  const src = crop === undefined ? null : portalBlockCropUrl(versionUid, block.portal_block_id);

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      open={staticOpen ? true : undefined}
      aria-label="Блок страницы документа"
      data-block-viewer=""
      onClick={(event) => {
        // A press on the backdrop lands on the dialog itself; inside, it lands on the content.
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        const target = event.key === 'ArrowLeft' ? previous : event.key === 'ArrowRight' ? next : null;
        if (target === null) return;
        event.preventDefault();
        onIndex(target);
      }}
    >
      <div className={styles.box}>
        <header className={styles.bar}>
          <div className={styles.steps} role="group" aria-label="Блоки выбранных страниц">
            <button
              type="button"
              className={styles.step}
              onClick={() => {
                if (previous !== null) onIndex(previous);
              }}
              disabled={previous === null}
              aria-label="Предыдущий блок"
              title="Предыдущий блок"
            >
              ‹
            </button>
            <span className={styles.position} data-viewer-position={index + 1}>
              {`${index + 1} / ${blocks.length}`}
            </span>
            <button
              type="button"
              className={styles.step}
              onClick={() => {
                if (next !== null) onIndex(next);
              }}
              disabled={next === null}
              aria-label="Следующий блок"
              title="Следующий блок"
            >
              ›
            </button>
          </div>
          <span className={styles.title} title={caption}>
            {caption}
          </span>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Закрыть" title="Закрыть (Esc)">
            ✕
          </button>
        </header>
        <div className={styles.body}>
          <div className={styles.picture} data-block-picture={src === null ? 'absent' : 'present'}>
            {src === null || crop === undefined ? (
              <p className={styles.noPicture}>
                {block.block_type === 'image'
                  ? 'Изображения у этого блока нет: фрагмент не вырезан.'
                  : 'У блока этого типа нет изображения: его содержимое — в панели справа.'}
              </p>
            ) : (
              <>
                <BlockImageStage key={`${index}:${block.portal_block_id}`} src={src} alt={`${typeLabel}: фрагмент страницы ${block.page_number} PDF`} />
                <p className={styles.pictureCaption}>
                  {`${caption}. Размер, пикс.: ${crop.width_px} × ${crop.height_px}.`}{' '}
                  <a href={src} target="_blank" rel="noopener noreferrer">
                    Открыть фрагмент целиком
                  </a>
                </p>
              </>
            )}
          </div>
          <aside className={styles.side} aria-label="О блоке" data-block-panel="">
            <PortalBlockCard block={block} versionUid={versionUid} showCrop={false} />
            {pageFindings === null || runId === null ? null : (
              <PageFindingsPanel projectUid={projectUid} runId={runId} runAt={runAt} page={block.page_number} reading={pageFindings} />
            )}
          </aside>
        </div>
      </div>
    </dialog>
  );
}
