'use client';

/**
 * Create one project.
 *
 * The idempotency key is minted from the typed name, so pressing "Create" twice, or
 * retrying after a failure, is the same command under the same key and returns the same
 * project. Editing the name is a different intent and gets a different key.
 *
 * A failure is rendered as the state it is: a refusal the server will not change renders
 * as `UnsupportedState` with no retry, and a retryable failure renders as `ErrorState`
 * with one. The retry button appears only when the decoded envelope says `retryable`.
 *
 * ## Two places, one form (`UIP-S03-01`)
 *
 * The form stands on the page «Объекты» (`mode: 'page'`, the default) and as the body of the window «Новый объект» that the
 * object selector opens (`mode: 'window'`). It is the same form: the same state, the same name check, the same mutation and the
 * same intent key. The window mode changes only what a window needs:
 *
 *   - the field has the label «Название объекта» (the window's own title says «Новый объект»), with the original's example as the hint;
 *   - **no button of its own**: the window's «Создать» is in the window's row of buttons, outside the form, and submits it by
 *     `formId` (the button's `form` attribute), so Enter in the field and the button are one submit. The form says when a
 *     send is in flight (`onBusyChange`), so the window can disable that button;
 *   - a refusal is one line under the field (`CreateProjectFailureLine`) and **the name stays as it was typed**: only a
 *     success empties the field. «Создать» again is the retry, under the same key;
 *   - no «Создан …» line and no code of the new object: the window closes on success and the caller takes over
 *     (`onCreated`); the code stays in the object's «Сведения».
 */

import { useEffect, useId, useState } from 'react';

import type { Project } from '@/shared/api';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { useIntentKey } from '@/shared/lib';
import type { CreateProjectFailure, ProjectNameProblem } from '@/entities/project';
import {
  classifyCreateProjectFailure,
  projectNameProblemMessage,
  validateProjectName,
} from '@/entities/project';

import { useCreateProject } from '../model/use-create-project';
import { useMayActAsExpert } from '@/entities/account';
import { CreateProjectFailureLine } from './create-project-failure-line';

/** The hint in the window's field: the original's example, which also shows that the number leads the name. */
export const WINDOW_NAME_HINT = 'Например: 215. ЖК «Панорама»';

export interface CreateProjectFormProps {
  /** Called with the created project, so the screen can navigate or announce it. */
  readonly onCreated?: ((project: Project) => void) | undefined;
  /** `'page'` (the default): the form of the page «Объекты». `'window'`: the body of the window «Новый объект» (see the header). */
  readonly mode?: 'page' | 'window' | undefined;
  /** `'window'` only: the `id` of the `<form>`, which the window's «Создать» names in its `form` attribute. Absent: one is made. */
  readonly formId?: string | undefined;
  /** `'window'` only: told whenever a send starts (`true`) or ends (`false`), so the window can hold its button while one is in flight. */
  readonly onBusyChange?: ((busy: boolean) => void) | undefined;
}

function CreateProjectFormInner({ onCreated, mode = 'page', formId, onBusyChange }: CreateProjectFormProps) {
  const inWindow = mode === 'window';
  const ownId = useId();
  const id = formId ?? ownId;
  // The page's field keeps its old id (the page has one form); the window's is made from the form's, so a window opened over
  // the page «Объекты» does not hold a second element of the same id.
  const inputId = inWindow ? `${id}-name` : 'new-project-name';
  const [name, setName] = useState('');
  const [localProblem, setLocalProblem] = useState<ProjectNameProblem | null>(null);
  const [created, setCreated] = useState<Project | null>(null);

  const trimmed = name.trim();
  const idempotencyKey = useIntentKey(`create-project:${trimmed}`);
  const mutation = useCreateProject();
  const busy = mutation.isPending;

  useEffect(() => {
    if (inWindow) onBusyChange?.(busy);
  }, [inWindow, busy, onBusyChange]);

  const submit = () => {
    const problem = validateProjectName(name);
    setLocalProblem(problem);
    if (problem !== null) return;
    setCreated(null);
    mutation.mutate(
      { name: trimmed, idempotencyKey },
      {
        onSuccess: (project) => {
          setCreated(project);
          setName('');
          onCreated?.(project);
        },
      },
    );
  };

  const failure: CreateProjectFailure | null =
    mutation.error === null || mutation.error === undefined
      ? null
      : classifyCreateProjectFailure(mutation.error);

  const statusLines = (
    <>
      {localProblem !== null ? (
        <p className="am-form__problem" role="alert" data-create-problem={localProblem}>
          {projectNameProblemMessage(localProblem)}
        </p>
      ) : null}

      {mutation.isPending ? <LoadingState what="новый объект" /> : null}
    </>
  );

  if (inWindow) {
    return (
      <form
        className="am-form"
        id={id}
        data-create-project-form="window"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className="am-form__field">
          <label htmlFor={inputId}>Название объекта</label>
          <input
            id={inputId}
            name="name"
            type="text"
            autoComplete="off"
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setLocalProblem(null);
            }}
            placeholder={WINDOW_NAME_HINT}
          />
        </div>
        {statusLines}
        {failure !== null ? <CreateProjectFailureLine failure={failure} /> : null}
      </form>
    );
  }

  return (
    <form
      className="am-form"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor={inputId}>
        <strong>Новый объект</strong>
      </label>
      <div className="am-form__row">
        <input
          id={inputId}
          name="name"
          type="text"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setLocalProblem(null);
          }}
          placeholder="Название объекта"
        />
        <button type="submit" className="am-button" disabled={mutation.isPending}>
          Создать
        </button>
      </div>

      {statusLines}

      {failure !== null && failure.presentation === 'unsupported' ? (
        <UnsupportedState title={failure.title} detail={failure.detail} />
      ) : null}

      {failure !== null && failure.presentation === 'error' ? (
        <ErrorState
          title={failure.title}
          detail={failure.detail}
          correlationId={failure.correlationId}
          {...(failure.retryable
            ? {
                onRetry: () => {
                  mutation.mutate({ name: trimmed, idempotencyKey });
                },
                retryLabel: 'Повторить с тем же ключом',
              }
            : {})}
        />
      ) : null}

      {created !== null ? (
        <p className="am-form__created" role="status" data-created-project={created.project_uid}>
          Создан <strong>{created.name}</strong> — <code>{created.project_uid}</code>
        </p>
      ) : null}
    </form>
  );
}

/**
 * `R-150e`: offered only to an account that may take an expert's action; the server refuses it
 * to anyone else. While the account is not known yet the control stays drawn.
 */
export function CreateProjectForm(props: Parameters<typeof CreateProjectFormInner>[0]) {
  const mayAct = useMayActAsExpert();
  if (!mayAct) return <p className="am-note" data-expert-only="CreateProjectForm">Создавать объекты может эксперт.</p>;
  return <CreateProjectFormInner {...props} />;
}
