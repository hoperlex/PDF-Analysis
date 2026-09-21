'use client';

/** @jsxRuntime automatic */

/**
 * The screen this prototype exists to produce: the declared PDF page, and the exact
 * extracted quotation beside it.
 *
 * The quotation is the load-bearing half. `PROTOTYPE_PROFILE.md` §8 asks that a reviewer
 * open the page from a finding and view its exact quotation; `P3-WEB-02` lists a bounding
 * box, a highlight rectangle and text-layer selection sync as explicit non-goals. So the
 * page is context and the quotation is evidence, and the quotation is rendered as the
 * server sent it — `{item.quote}` in JSX escapes markup and changes nothing else. No trim,
 * no collapse, no ellipsis, no smart quotes; `entities/finding-observation/model/quotation`
 * explains why at length.
 *
 * The page island is bounded to one `<object>`. `OD-09` is untaken and this session may add
 * no dependency, so it is the browser's own PDF viewer addressed by the `#page=N` fragment.
 * Its limits are stated to the reviewer rather than hidden: page-level navigation, no
 * overlay.
 *
 * Navigation is restricted to the observation's declared pages. Offering the other pages of
 * the document invites a reviewer to decide against text this finding never cited.
 */

import type { Evidence, FindingObservation } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, LoadingState } from '@/shared/ui';
import { pdfPageUrl } from '@/features/open-evidence';
import {
  anchorLabel,
  anchorMatchesQuotation,
  declaredPages,
  evidenceOnPage,
  observationProviderMode,
} from '@/entities/finding-observation';

export interface EvidenceViewerProps {
  readonly observation: FindingObservation;
  readonly activePage: number;
  readonly onPageChange: (page: number) => void;
  /** `blob:` URL of the fetched version content, or null while it is unavailable. */
  readonly documentUrl: string | null;
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
}

function QuotationCard({ item }: { item: Evidence }) {
  const consistent = anchorMatchesQuotation(item);
  return (
    <li className="am-quotation" data-evidence-ordinal={item.evidence_ordinal}>
      {/*
        `data-evidence-quote` carries the same string as the visible text so a test can
        assert byte-identity against the API value without parsing rendered markup.
      */}
      <blockquote className="am-quotation__text" data-evidence-quote={item.quote}>
        {item.quote}
      </blockquote>
      {/*
        `block_id` is deliberately not rendered. The contract calls it "a secondary anchor
        into this version's block index. Not a contract identifier" — it is an internal
        index handle that tells the reviewer nothing the page number and character range do
        not, and printing an internal handle is how an object key reaches a screen when
        something upstream puts one in the wrong field. The leakage check in
        tests/unit/review/key-leakage.test.ts caught exactly that and this is the repair.
      */}
      <p className="am-quotation__anchor">{anchorLabel(item)}</p>
      {consistent ? null : (
        <p className="am-quotation__inconsistent" role="alert">
          Заявленная длина фрагмента не совпадает с цитатой. Якорь показан так, как его
          прислал сервер, и здесь он не пересчитывается.
        </p>
      )}
    </li>
  );
}

export function EvidenceViewer({
  observation,
  activePage,
  onPageChange,
  documentUrl,
  isLoading,
  error,
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
  const quotations = evidenceOnPage(observation, page);

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
          {observationProviderMode(observation)}
        </span>
      </nav>

      <div className="am-evidence__panes">
        <div className="am-evidence__page">
          {isLoading === true ? <LoadingState what="the document page" /> : null}
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
              <object
                className="am-evidence__object"
                data={pdfPageUrl(documentUrl, page)}
                type="application/pdf"
                aria-label={`Страница ${page} проверяемого документа`}
                data-viewer-src={pdfPageUrl(documentUrl, page)}
              >
                <p>
                  Этот браузер не умеет показывать PDF внутри страницы. Свидетельство —
                  цитата рядом с панелью; сама страница нужна как контекст.
                </p>
              </object>
            )
          ) : null}
        </div>

        <div className="am-evidence__quotations">
          <h3>Цитаты на странице {page}</h3>
          {quotations.length === 0 ? (
            <p className="am-evidence__none">
              Это наблюдение не ссылается ни на одну цитату на странице {page}.
            </p>
          ) : (
            <ul className="am-quotation-list">
              {quotations.map((item) => (
                <QuotationCard key={`${item.evidence_ordinal}`} item={item} />
              ))}
            </ul>
          )}
          <p className="am-evidence__limits">
            Навигация только по страницам: без подсветки фрагмента и рамки. Цитата выше —
            точная строка, которую шлюз привязки проверил по её якорю.
          </p>
        </div>
      </div>
    </div>
  );
}
