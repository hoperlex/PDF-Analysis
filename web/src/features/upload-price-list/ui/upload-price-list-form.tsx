'use client';

/**
 * «Загрузить прайс-лист» on the project's «Оптимизация» tab (`W60-PRICE-LIST-01`).
 *
 * One CSV or Excel file (the first sheet is read) of at most 10 MiB, and an optional default
 * currency for rows whose currency neither their own cell nor the price column's header
 * states. The size and emptiness are checked here before a byte is sent; everything else —
 * the format, the header, each row — is the server's to judge, and its refusal is said in
 * Russian with what to do about it. A stored upload becomes the project's newest revision;
 * the panel beside this form lists it.
 */

import { useState } from 'react';

import type { PriceListRevision, ProjectUid } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';
import { useIntentKey } from '@/shared/lib';
import type { FailureMessage } from '@/shared/api/failure-message';
import { uploadFailureMessage } from '@/entities/price-list';

import { useUploadPriceList } from '../model/use-upload-price-list';

/** The largest file the API accepts, 10 MiB. */
export const PRICE_LIST_MAX_BYTES = 10 * 1024 * 1024;

/** The default currencies offered; the file's own currency always wins over this choice. */
export const DEFAULT_CURRENCY_OPTIONS: readonly { readonly code: string; readonly label: string }[] = [
  { code: '', label: 'не задана' },
  { code: 'RUB', label: 'рубль' },
  { code: 'USD', label: 'доллар США' },
  { code: 'EUR', label: 'евро' },
  { code: 'CNY', label: 'юань' },
];

const ACCEPT =
  '.csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

/** The client's own check before sending: empty or larger than the API accepts. */
export function precheckPriceListFile(file: File): string | null {
  if (file.size === 0) return 'Файл пуст.';
  if (file.size > PRICE_LIST_MAX_BYTES) return 'Файл больше 10 MiB. Разделите прайс-лист на части.';
  return null;
}

export interface UploadPriceListFormViewProps {
  readonly fileLabel: string | null;
  readonly currency: string;
  readonly precheck: string | null;
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  readonly stored: PriceListRevision | null;
  readonly onChoose: (file: File | null) => void;
  readonly onCurrency: (code: string) => void;
  readonly onSubmit: () => void;
}

/** The form from state already in hand. Rendered by the static harness in every branch. */
export function UploadPriceListFormView({
  fileLabel,
  currency,
  precheck,
  pending,
  failure,
  stored,
  onChoose,
  onCurrency,
  onSubmit,
}: UploadPriceListFormViewProps) {
  return (
    <form
      data-price-list-upload=""
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="am-form">
        <label htmlFor="price-list-file">
          <strong>Прайс-лист проекта (CSV или книга Excel, до 10 MiB)</strong>
        </label>
        <input
          id="price-list-file"
          name="file"
          type="file"
          accept={ACCEPT}
          onChange={(event) => onChoose(event.target.files?.[0] ?? null)}
        />
        {fileLabel !== null ? <p className="am-form__chosen">Выбран файл: {fileLabel}</p> : null}
        <label htmlFor="price-list-currency">Валюта по умолчанию</label>
        <select
          id="price-list-currency"
          value={currency}
          onChange={(event) => onCurrency(event.target.value)}
        >
          {DEFAULT_CURRENCY_OPTIONS.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </select>
        <p className="am-form__hint">
          Применяется к строкам, у которых валюта не указана ни в ячейке, ни в заголовке столбца
          цены. Цена берётся только из чисел файла и никогда не угадывается.
        </p>
        {precheck !== null ? <p className="am-form__problem">{precheck}</p> : null}
        <div>
          <button
            type="submit"
            className="am-button"
            disabled={fileLabel === null || precheck !== null || pending}
          >
            Загрузить прайс-лист
          </button>
        </div>
      </div>
      {pending ? <LoadingState what="прайс-лист" /> : null}
      {failure !== null ? (
        <ErrorState
          title="Прайс-лист не загружен."
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={failure.retryable ? onSubmit : undefined}
        />
      ) : null}
      {stored !== null ? (
        <p className="am-note" data-price-list-stored={stored.price_list_id}>
          Сохранена редакция {stored.revision_number}: принято позиций — {stored.accepted_row_count},
          пропущено строк — {stored.skipped_row_count}.
        </p>
      ) : null}
    </form>
  );
}

export interface UploadPriceListFormProps {
  readonly projectUid: ProjectUid;
}

export function UploadPriceListForm({ projectUid }: UploadPriceListFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [currency, setCurrency] = useState('');
  const [precheck, setPrecheck] = useState<string | null>(null);
  // The intent is this file and currency for this project: two presses over the same choice
  // are one command, and another file or currency is another one.
  const idempotencyKey = useIntentKey(
    `upload-price-list:${projectUid}:${file?.name ?? ''}:${file?.size ?? 0}:${
      file?.lastModified ?? 0
    }:${currency}`,
  );
  const mutation = useUploadPriceList();

  const send = () => {
    if (file === null || precheck !== null) return;
    mutation.mutate({
      projectUid,
      file,
      defaultCurrency: currency === '' ? null : currency,
      idempotencyKey,
    });
  };

  return (
    <UploadPriceListFormView
      fileLabel={file === null ? null : file.name}
      currency={currency}
      precheck={precheck}
      pending={mutation.isPending}
      failure={
        mutation.error === null || mutation.error === undefined
          ? null
          : uploadFailureMessage(mutation.error)
      }
      stored={mutation.data ?? null}
      onChoose={(chosen) => {
        mutation.reset();
        setFile(chosen);
        setPrecheck(chosen === null ? null : precheckPriceListFile(chosen));
      }}
      onCurrency={(code) => {
        mutation.reset();
        setCurrency(code);
      }}
      onSubmit={send}
    />
  );
}
