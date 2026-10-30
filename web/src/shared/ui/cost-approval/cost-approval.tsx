'use client';

/** Pure presentation shared by the two start forms; no routing, pricing or API calls. */
export interface CostApprovalEstimate {
  readonly estimate_digest: string;
  readonly billing: 'metered' | 'unmetered';
  readonly provider_mode: 'live' | 'recorded';
  readonly currency: 'USD';
  readonly model_id: string;
  readonly text_characters: number;
  readonly page_count: number;
  readonly windows: number;
  readonly calls: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly estimated_cost_micros: number;
  readonly recommended_ceiling_micros: number;
}

/** Exact decimal USD parsing; rounding a user's cap upwards would change their approval. */
export function ceilingMicros(value: string, minimum: number): number | null {
  const match = /^(\d+)(?:[.,](\d{1,6}))?$/.exec(value.trim());
  if (match === null || !Number.isSafeInteger(minimum) || minimum < 0) return null;
  const micros = BigInt(match[1]!) * 1_000_000n + BigInt((match[2] ?? '').padEnd(6, '0'));
  if (micros > BigInt(Number.MAX_SAFE_INTEGER) || micros < BigInt(minimum)) return null;
  return Number(micros);
}

export function microsAsUsd(value: number): string {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error('Invalid cost estimate amount');
  const amount = BigInt(value);
  const decimal = String(amount % 1_000_000n).padStart(6, '0').replace(/0+$/, '');
  return `${amount / 1_000_000n}${decimal === '' ? '' : `.${decimal}`}`;
}

/** Invalid server readings cannot become a confirmable amount. */
export function usableCostEstimate(value: CostApprovalEstimate): boolean {
  return value !== null && typeof value === 'object'
    && /^[0-9a-f]{64}$/.test(value.estimate_digest)
    && ['metered', 'unmetered'].includes(value.billing)
    && ['live', 'recorded'].includes(value.provider_mode)
    && value.currency === 'USD' && typeof value.model_id === 'string' && value.model_id.length > 0
    && [value.text_characters, value.page_count, value.windows, value.calls, value.input_tokens,
      value.output_tokens, value.estimated_cost_micros, value.recommended_ceiling_micros]
      .every((number) => Number.isSafeInteger(number) && number >= 0)
    && value.recommended_ceiling_micros >= value.estimated_cost_micros;
}

export interface CostApprovalProps {
  readonly estimate: CostApprovalEstimate;
  readonly ceiling: string;
  readonly approved: boolean;
  readonly disabled: boolean;
  readonly onCeilingChange: (value: string) => void;
  readonly onApprovedChange: (value: boolean) => void;
}

export function CostApproval({ estimate, ceiling, approved, disabled, onCeilingChange, onApprovedChange }: CostApprovalProps) {
  const sufficient = ceilingMicros(ceiling, Math.max(estimate.billing === 'metered' ? 1 : 0, estimate.estimated_cost_micros)) !== null;
  return <fieldset disabled={disabled} data-cost-approval>
    <legend>Стоимость перед запуском</legend>
    <p>{estimate.billing === 'unmetered'
      ? 'Подключение без тарификации в приложении. Денежная оценка не отражает внешний счёт провайдера.'
      : `Предварительная оценка: ${microsAsUsd(estimate.estimated_cost_micros)} USD.`}</p>
    {estimate.provider_mode === 'recorded' ? <p className="am-note">Тестовый режим (recorded): сохранённые ответы. Оценка не является фактическим расходом.</p> : null}
    <p>Модель: {estimate.model_id}. Страниц: {estimate.page_count}; символов: {estimate.text_characters}; окон: {estimate.windows}; вызовов: {estimate.calls}.</p>
    <p>Токены: вход — {estimate.input_tokens}, ответ — до {estimate.output_tokens}.</p>
    <label>Лимит стоимости, USD
      <input type="text" inputMode="decimal" maxLength={24} value={ceiling} aria-invalid={!sufficient}
        onChange={(event) => onCeilingChange(event.currentTarget.value)} />
    </label>
    <p className="am-note">Рекомендуемый лимит: {microsAsUsd(estimate.recommended_ceiling_micros)} USD. Лимит должен покрывать оценку; окончательный расход зависит от ответа провайдера.</p>
    {sufficient ? null : <p role="alert">Введите конечный лимит не ниже оценки, до шести знаков после запятой. Для тарифицируемого подключения лимит должен быть положительным.</p>}
    <label><input type="checkbox" checked={approved && sufficient} disabled={disabled || !sufficient}
      onChange={(event) => onApprovedChange(event.currentTarget.checked)} />
      Подтверждаю оценку и лимит для выбранных параметров
    </label>
  </fieldset>;
}
