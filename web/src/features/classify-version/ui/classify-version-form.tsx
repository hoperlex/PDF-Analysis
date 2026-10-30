'use client';

/**
 * The expert's confirmation of one version's project stage and section
 * (`W59-SECTION-UI-01`).
 *
 * **What it offers.** Two stages — П, проектная; Р, рабочая — and all fifteen sections, the
 * ones the file name or the recognised text point at first, each with the evidence that
 * pointed, and every other section after them. Nothing is pre-selected: a suggestion is a
 * reading aid, and the owner's rule (`S-4`) is that analysis waits for an explicit choice. A
 * section with no registered analysis profile stays choosable and is marked, because the
 * classification is a fact about the document, not about what the analysis can do today; a
 * run over it is then refused with its own message, never redirected to another profile.
 *
 * **One press, one request.** The button is disabled while the request is in flight, and a
 * synchronous gate (`../model/single-flight.ts`) refuses a second press that arrives before
 * React has re-rendered — a double click sends one `PUT`.
 *
 * **What a refusal shows.** `409 version_already_classified` tells the panel above
 * (`onConflict`), which reads the stored classification back and shows it as «уже
 * подтверждено другим решением»; `403` says that only an expert may confirm; everything else
 * is the shared Russian reading with its correlation id. None offers an override.
 *
 * `ClassifyVersionFormView` is the whole markup, driven by props, so every state can be
 * rendered by the static harness; `ClassifyVersionForm` adds the state and the command.
 */

import { useState } from 'react';

import type { ProjectSection as SectionCode, ProjectStage, SectionReview, SectionReviewOption } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import type { ClassificationFailure, VersionAddress } from '@/entities/document-version';
import {
  PROJECT_STAGES,
  classificationFailure,
  orderSectionOptions,
  sectionTitleOf,
  stageChoiceText,
  suggestionEvidence,
} from '@/entities/document-version';

import { createSingleFlight } from '../model/single-flight';
import { useClassifyVersion } from '../model/use-classify-version';
import styles from './classify-version-form.module.css';

export interface ClassifyVersionFormViewProps {
  readonly review: SectionReview;
  readonly stage: ProjectStage | null;
  readonly section: SectionCode | null;
  readonly pending: boolean;
  readonly failure: ClassificationFailure | null;
  readonly onStage: (stage: ProjectStage) => void;
  readonly onSection: (section: SectionCode) => void;
  readonly onConfirm: () => void;
}

function Evidence({ option }: { readonly option: SectionReviewOption }) {
  if (option.suggestion === null) return null;
  const evidence = suggestionEvidence(option.suggestion);
  return (
    <span className={styles.evidence} data-suggestion-score={option.suggestion.score}>
      {evidence.filenamePatterns.length === 0 ? null : (
        <span className="am-form__hint">
          В имени файла:{' '}
          {evidence.filenamePatterns.map((pattern, index) => (
            <span key={pattern}>
              {index === 0 ? null : ', '}
              <code>{pattern}</code>
            </span>
          ))}
        </span>
      )}
      {evidence.textKeywords.length === 0 ? null : (
        <span className="am-form__hint">В тексте: {evidence.textKeywords.join(', ')}</span>
      )}
      {evidence.nameInText ? (
        <span className="am-form__hint">Название раздела встречается в тексте.</span>
      ) : null}
    </span>
  );
}

function SectionChoice({
  option,
  checked,
  disabled,
  onSection,
}: {
  readonly option: SectionReviewOption;
  readonly checked: boolean;
  readonly disabled: boolean;
  readonly onSection: (section: SectionCode) => void;
}) {
  return (
    <label
      className={styles.choice}
      data-section-option={option.section_code}
      data-suggested={option.suggestion === null ? 'false' : 'true'}
      data-executable={option.executable ? 'true' : 'false'}
    >
      <input
        type="radio"
        name="classification-section"
        value={option.section_code}
        data-section-choice={option.section_code}
        checked={checked}
        disabled={disabled}
        onChange={() => onSection(option.section_code)}
      />
      <span className={styles.label}>
        <span>
          {sectionTitleOf(option.section_code)}
          {option.executable ? null : (
            <>
              {' · '}
              <em data-profile-unavailable="">профиль анализа недоступен</em>
            </>
          )}
        </span>
        <Evidence option={option} />
      </span>
    </label>
  );
}

export function ClassifyVersionFormView({
  review,
  stage,
  section,
  pending,
  failure,
  onStage,
  onSection,
  onConfirm,
}: ClassifyVersionFormViewProps) {
  const { suggested, rest } = orderSectionOptions(review.options);
  const chosen = review.options.find((option) => option.section_code === section) ?? null;

  return (
    <form
      className="am-form"
      data-classification-form=""
      onSubmit={(event) => {
        event.preventDefault();
        onConfirm();
      }}
    >
      <fieldset className={styles.group}>
        <legend className={styles.legend}>Стадия проекта</legend>
        {PROJECT_STAGES.map((value) => (
          <label key={value} className={styles.choice}>
            <input
              type="radio"
              name="classification-stage"
              value={value}
              data-stage-choice={value}
              checked={stage === value}
              disabled={pending}
              onChange={() => onStage(value)}
            />
            <span className={styles.label}>{stageChoiceText(value)}</span>
          </label>
        ))}
      </fieldset>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Раздел</legend>
        {review.recognised_text_consulted ? null : (
          <p className="am-form__hint" data-recognised-text="not-consulted">
            Распознанный текст этой версии ещё не прочитан, поэтому подсказки сделаны только по
            имени файла.
          </p>
        )}
        {suggested.length === 0 ? (
          <p className="am-form__hint" data-suggested-count="0">
            Ни имя файла, ни текст версии не указали на раздел. Выберите его сами.
          </p>
        ) : (
          <>
            <p className="am-form__hint" data-suggested-count={suggested.length}>
              Подсказки по имени файла и тексту версии — это не решение: раздел выбираете вы.
            </p>
            {suggested.map((option) => (
              <SectionChoice
                key={option.section_code}
                option={option}
                checked={section === option.section_code}
                disabled={pending}
                onSection={onSection}
              />
            ))}
            <p className="am-form__hint">Остальные разделы:</p>
          </>
        )}
        {rest.map((option) => (
          <SectionChoice
            key={option.section_code}
            option={option}
            checked={section === option.section_code}
            disabled={pending}
            onSection={onSection}
          />
        ))}
      </fieldset>

      {chosen !== null && !chosen.executable ? (
        <p className="am-form__hint" data-chosen-profile="unavailable">
          Для этого раздела профиль анализа ещё не зарегистрирован. Подтвердить раздел можно, но
          прогон по версии будет отклонён, пока профиль не появится; анализ по другому разделу
          вместо него не запускается.
        </p>
      ) : null}

      <div className="am-form__row">
        <button
          type="submit"
          className="am-button"
          data-classification-confirm=""
          disabled={pending || stage === null || section === null}
        >
          Подтвердить раздел
        </button>
      </div>

      {pending ? <LoadingState what="подтверждение стадии и раздела" /> : null}

      {failure === null ? null : (
        <p className="am-form__problem" role="alert" data-classification-failure={failure.kind}>
          {failure.detail}
          {failure.correlationId === null ? null : (
            <>
              {' '}
              Идентификатор корреляции <code>{failure.correlationId}</code>.
            </>
          )}
        </p>
      )}
    </form>
  );
}

export interface ClassifyVersionFormProps {
  readonly address: VersionAddress;
  readonly review: SectionReview;
  /** Called on `409 version_already_classified`, after the stored answer is asked for again. */
  readonly onConflict?: (() => void) | undefined;
}

export function ClassifyVersionForm({ address, review, onConflict }: ClassifyVersionFormProps) {
  const [stage, setStage] = useState<ProjectStage | null>(null);
  const [section, setSection] = useState<SectionCode | null>(null);
  const [flight] = useState(createSingleFlight);
  const mutation = useClassifyVersion();

  const confirm = () => {
    if (stage === null || section === null) return;
    flight.run(() =>
      mutation.mutateAsync({ ...address, stage, section }).catch((error: unknown) => {
        if (classificationFailure(error).kind === 'already_classified') onConflict?.();
      }),
    );
  };

  return (
    <ClassifyVersionFormView
      review={review}
      stage={stage}
      section={section}
      pending={mutation.isPending}
      failure={mutation.error === null ? null : classificationFailure(mutation.error)}
      onStage={setStage}
      onSection={setSection}
      onConfirm={confirm}
    />
  );
}
