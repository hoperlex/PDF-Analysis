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
 */

import { useState } from 'react';

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

export interface CreateProjectFormProps {
  /** Called with the created project, so the screen can navigate or announce it. */
  readonly onCreated?: ((project: Project) => void) | undefined;
}

export function CreateProjectForm({ onCreated }: CreateProjectFormProps) {
  const [name, setName] = useState('');
  const [localProblem, setLocalProblem] = useState<ProjectNameProblem | null>(null);
  const [created, setCreated] = useState<Project | null>(null);

  const trimmed = name.trim();
  const idempotencyKey = useIntentKey(`create-project:${trimmed}`);
  const mutation = useCreateProject();

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

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor="new-project-name">
        <strong>Новый проект</strong>
      </label>
      <div style={{ display: 'flex', gap: '0.5rem', margin: '0.4rem 0 0.6rem' }}>
        <input
          id="new-project-name"
          name="name"
          type="text"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setLocalProblem(null);
          }}
          placeholder="Название проекта"
          style={{ flex: '1 1 auto', padding: '0.4rem 0.5rem' }}
        />
        <button type="submit" className="am-button" disabled={mutation.isPending}>
          Create
        </button>
      </div>

      {localProblem !== null ? (
        <p role="alert" data-create-problem={localProblem}>
          {projectNameProblemMessage(localProblem)}
        </p>
      ) : null}

      {mutation.isPending ? <LoadingState what="the new project" /> : null}

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
        <p role="status" data-created-project={created.project_uid}>
          Created <strong>{created.name}</strong> — <code>{created.project_uid}</code>
        </p>
      ) : null}
    </form>
  );
}
