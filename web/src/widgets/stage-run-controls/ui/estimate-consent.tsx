'use client';

import type { ComparisonAiEstimate, StageChainRun } from '@/shared/api';
import { AiLabel, agreementStands, estimateLines, isBlocked } from '@/entities/version-series';

/** A full chain may still need deterministic steps when every AI answer is cached. */
export function StageEstimateConsent({ estimate, agreedDigest, disabled, onAgree, engine }: {
  readonly estimate: ComparisonAiEstimate;
  readonly agreedDigest: string | null;
  readonly disabled: boolean;
  readonly onAgree: (digest: string | null) => void;
  readonly engine?: StageChainRun['engine'];
}) {
  const blocked = isBlocked(estimate);
  return <div data-stage-estimate={estimate.estimate_digest}>
    <ul>{estimateLines(estimate).map((line) => <li key={line.key}>{line.text}</li>)}</ul>
    {engine === 'v3_native_text_experimental'
      ? <p>V3 использует только собственный текст PDF. Эта оценка и согласие относятся к одному следующему обращению к модели. Для следующего обращения потребуются новая оценка и «Продолжить»; начальное согласие не обещает завершение всех окон.</p>
      : <p>Графические области обрабатываются окнами до 4 областей (8 изображений). Оценка относится к текущему окну; для оставшихся областей может потребоваться новое согласие.</p>}
    {estimate.route.provider_mode === 'recorded' ? <p role="status">Подключение использует записанные тестовые ответы.</p> : null}
    {blocked ? <p role="alert">Запуск превышает допустимый бюджет. Измените объём или обратитесь к администратору.</p> : null}
    {estimate.calls === 0 ? <p>Новых обращений к модели не требуется. Сохранённые ответы будут использованы повторно.</p> : null}
    {agreedDigest !== null && !agreementStands(agreedDigest, estimate) ? <p role="status">Оценка изменилась. Подтвердите новую оценку.</p> : null}
    <label><input type="checkbox" checked={agreementStands(agreedDigest, estimate)} disabled={disabled || blocked}
      onChange={(event) => onAgree(event.target.checked ? estimate.estimate_digest : null)} />
      Подтверждаю передачу указанных данных выбранному исполнителю и оценку стоимости.</label>
    <p><AiLabel />. Решение по изменениям принимает эксперт.</p>
  </div>;
}
