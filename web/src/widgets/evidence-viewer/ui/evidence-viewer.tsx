'use client';

/** @jsxRuntime automatic */

/**
 * The screen this prototype exists to produce: the declared PDF page, and the exact
 * extracted quotation beside it.
 *
 * The quotation is the load-bearing half. `PROTOTYPE_PROFILE.md` §8 asks that a reviewer
 * open the page from a finding and view its exact quotation, and the quotation is rendered as
 * the server sent it — `{item.quote}` in JSX escapes markup and changes nothing else. No trim,
 * no collapse, no ellipsis, no smart quotes; `entities/finding-observation/model/quotation`
 * explains why at length. The page is context and the frames on it are a navigation aid.
 *
 * The page is drawn by `PageViewer` (`features/open-evidence`), which opens on the quotation:
 * the lines it sits on are framed from the server's own line geometry when the screen has it
 * (`blockIndex`), and from a search of the page text when it has not; a quotation that neither
 * can place is left unframed and the card says so. Each card carries the number of its frame,
 * and choosing either moves the other.
 *
 * Navigation is restricted to the observation's declared pages. Offering the other pages of
 * the document invites a reviewer to decide against text this finding never cited.
 *
 * Under the two panes, a finding that carries v2 fields shows what it rests on
 * (`FindingBasis`, `REVIEW-V2-UI-01`): the required and stated values, the norm citations and
 * the merged observations. A finding without them shows nothing more than it ever did.
 */

import { useMemo, useRef, useState } from 'react';

import type { FindingObservation, VersionBlockIndex } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, LoadingState } from '@/shared/ui';
import type { TargetResolution } from '@/features/open-evidence';
import { PageViewer } from '@/features/open-evidence';
import {
  declaredPages,
  evidenceOnPage,
  observationProviderMode,
} from '@/entities/finding-observation';

import { FindingBasis } from './finding-basis';
import { quotationTargetId, quotationTargets } from '../model/quotation-targets';
import { QuotationCard } from './quotation-card';

export interface EvidenceViewerProps {
  readonly observation: FindingObservation;
  /** `FindingDetail.merged_observations`; shown only when the server sent it (`REVIEW-V2-UI-01`). */
  readonly mergedObservations?: readonly FindingObservation[] | undefined;
  readonly activePage: number;
  readonly onPageChange: (page: number) => void;
  /** `blob:` URL of the fetched version content, or null while it is unavailable. */
  readonly documentUrl: string | null;
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  /**
   * `getVersionBlocks` for this version, read by the review screen (which owns the queries), or
   * null while it is unavailable. Without it the quotations are searched in the page text.
   */
  readonly blockIndex?: VersionBlockIndex | null | undefined;
}

/** What a reader has chosen, and the page it was chosen on: a new finding or page forgets it. */
interface Scoped<T> {
  readonly scope: string;
  readonly value: T;
}

/**
 * The page and its cards for one declared page. Its own component so the choices below can be
 * state: the early return for a finding with no evidence would otherwise sit above the hooks.
 */
function EvidencePanes({
  observation,
  page,
  documentUrl,
  isLoading,
  error,
  blockIndex,
}: Pick<EvidenceViewerProps, 'observation' | 'documentUrl' | 'isLoading' | 'error' | 'blockIndex'> & {
  readonly page: number;
}) {
  const quotations = useMemo(() => evidenceOnPage(observation, page), [observation, page]);
  const scope = `${observation.finding_observation_id}:${page}`;

  // The card the reader chose, and what the viewer last reported about this page. Both belong to
  // one finding on one page; a different finding or page starts with neither.
  const [chosen, setChosen] = useState<Scoped<string> | null>(null);
  const [reported, setReported] = useState<Scoped<ReadonlyMap<string, TargetResolution>> | null>(null);

  const targets = useMemo(() => quotationTargets(quotations, blockIndex), [quotations, blockIndex]);

  const resolutions = reported !== null && reported.scope === scope ? reported.value : null;
  const firstPlaced = targets.find((target) => resolutions?.get(target.id)?.status === 'found');
  const activeId = chosen !== null && chosen.scope === scope ? chosen.value : (firstPlaced?.id ?? null);

  const cards = useRef<Map<string, HTMLLIElement>>(new Map());
  const choose = (id: string) => {
    setChosen({ scope, value: id });
    cards.current.get(id)?.scrollIntoView({ block: 'nearest' });
  };

  return (
    <div className="am-evidence__panes">
      <div className="am-evidence__page">
        {isLoading === true ? <LoadingState what="страницу документа" /> : null}
        {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
        {isLoading !== true && (error === undefined || error === null) ? (
          documentUrl === null ? (
            <ErrorState
              title="Страницу не удалось показать"
              detail={
                <p>
                  Байты документа недоступны. Эта панель никогда не рисует пустую
                  страницу так, будто в PDF ничего нет.
                </p>
              }
            />
          ) : (
            <PageViewer
              documentUrl={documentUrl}
              pageNumber={page}
              targets={targets}
              activeTargetId={activeId}
              onTargetSelect={choose}
              onResolved={(results) => {
                setReported({ scope, value: results });
              }}
              label={`Страница ${page} проверяемого документа`}
            />
          )
        ) : null}
      </div>

      <div className="am-evidence__quotations">
        <h3>Цитаты на странице {page}</h3>
        {/*
          * NO EMPTY BRANCH HERE, and its absence is the repair `D-85` asked for.
          *
          * A `quotations.length === 0` case stood here and could not run on any input:
          * `pages` is the DISTINCT set of `page_number` over this observation's own
          * evidence, and `page` is either an `activePage` that is in that set or
          * `pages[0]`. So `page` always cites at least one quotation, and the branch was
          * dead code carrying a dead CSS rule -- the empty-case paragraph, now deleted
          * from `globals.css` -- which is how the census came to report it as a colour
          * rule no screen reaches. Its class name is deliberately not repeated here:
          * `styling-layer.test.ts` reads every product class token out of this file,
          * comments included, and requires the stylesheet to declare each one. It caught
          * this very sentence twice -- first for naming the deleted class, then for the
          * bare prefix in the explanation -- which is the guard being right both times.
          *
          * The invariant is asserted rather than trusted:
          * `tests/unit/review/viewer-and-panels.test.ts` renders this viewer with an
          * `activePage` the observation does not cite and with pages in a scrambled
          * order, and requires a quotation on the page that comes back. An observation
          * with no evidence at all never reaches here -- `pages.length === 0` is refused
          * by `EvidenceViewer`, as a reported integrity violation rather than an empty panel.
          */}
        <ul className="am-quotation-list">
          {quotations.map((item, at) => (
            <QuotationCard
              key={`${item.evidence_ordinal}`}
              item={item}
              badge={String(at + 1)}
              placement={resolutions?.get(quotationTargetId(item)) ?? null}
              active={activeId === quotationTargetId(item)}
              onSelect={() => {
                choose(quotationTargetId(item));
              }}
              itemRef={(element) => {
                if (element === null) cards.current.delete(quotationTargetId(item));
                else cards.current.set(quotationTargetId(item), element);
              }}
            />
          ))}
        </ul>
        <p className="am-evidence__limits">
          Рамки и подсветка на странице помогают найти место: это подсказка, а не свидетельство.
          Свидетельство — цитата: она показана точно так, как её прислал сервер, и по рамке не
          пересчитывается.
        </p>
      </div>
    </div>
  );
}

export function EvidenceViewer({
  observation,
  mergedObservations,
  activePage,
  onPageChange,
  documentUrl,
  isLoading,
  error,
  blockIndex,
}: EvidenceViewerProps) {
  const pages = declaredPages(observation);

  if (pages.length === 0) {
    return (
      <ErrorState
        title="Нарушение целостности данных"
        detail={
          <p>
            У этой находки нет свидетельств. Шлюз свидетельств P02 делает такое
            невозможным, поэтому это сообщается, а не показывается пустой панелью.
          </p>
        }
      />
    );
  }

  const page = pages.includes(activePage) ? activePage : (pages[0] as number);

  return (
    <div className="am-evidence" data-active-page={page}>
      <nav className="am-evidence__pages" aria-label="Заявленные страницы">
        {pages.map((candidate) => (
          <button
            key={candidate}
            type="button"
            className="am-button"
            data-page={candidate}
            data-active={candidate === page ? 'true' : 'false'}
            aria-current={candidate === page ? 'page' : undefined}
            onClick={() => {
              onPageChange(candidate);
            }}
          >
            стр. {candidate}
          </button>
        ))}
        <span className="am-evidence__provider" data-provider-mode={observationProviderMode(observation)}>
          {observationProviderMode(observation) === 'live' ? 'живой вызов' : 'из записи'}
        </span>
      </nav>

      <EvidencePanes
        observation={observation}
        page={page}
        documentUrl={documentUrl}
        isLoading={isLoading}
        error={error}
        blockIndex={blockIndex}
      />

      <FindingBasis observation={observation} mergedObservations={mergedObservations} />
    </div>
  );
}
