'use client';

/**
 * «Назначить работу» — the administrator's form (`W61-DISPATCHER-01`).
 *
 * A project (from `listProjects`), optionally one document of it (from `listDocuments`), an
 * expert (the active experts the screen read through `listUsers`) and an optional note. The
 * server checks all of it again: the document's project, the expert's role and standing, and
 * the one-open-assignment-per-scope rule.
 */

import { useState } from 'react';

import { ErrorState } from '@/shared/ui';
import { assignmentFailure, assignmentScope } from '@/entities/assignment';
import { useDocumentList } from '@/entities/document-version';
import { useProjectList } from '@/entities/project';

import { useCreateAssignment } from '../model/use-create-assignment';

export interface ExpertChoice {
  readonly userUid: string;
  readonly label: string;
}

export interface CreateAssignmentFormProps {
  readonly experts: readonly ExpertChoice[];
  /**
   * `R-151m`: the header's project, which the form starts on so an administrator working in one project does not pick it again;
   * `null` or absent for «Все проекты». Only the start: the field stays free, and a change of the header re-mounts the form.
   */
  readonly defaultProjectUid?: string | null | undefined;
}

function DocumentChoice({
  projectUid,
  value,
  onChange,
}: {
  readonly projectUid: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
}) {
  const documents = useDocumentList(projectUid);
  const items = documents.isSuccess ? documents.data.items : [];
  return (
    <label className="am-form__field">
      Документ (необязательно)
      <select value={value} onChange={(event) => onChange(event.target.value)} disabled={!documents.isSuccess}>
        <option value="">Весь проект</option>
        {items.map((document) => (
          <option key={document.document_uid} value={document.document_uid}>
            {document.display_title ?? document.document_uid}
          </option>
        ))}
      </select>
    </label>
  );
}

export function CreateAssignmentForm({ experts, defaultProjectUid = null }: CreateAssignmentFormProps) {
  const projects = useProjectList();
  const create = useCreateAssignment();
  const [projectUid, setProjectUid] = useState(defaultProjectUid ?? '');
  const [documentUid, setDocumentUid] = useState('');
  const [assignee, setAssignee] = useState('');
  const [note, setNote] = useState('');
  const [created, setCreated] = useState<{ readonly uid: string; readonly what: string; readonly who: string } | null>(null);

  const projectItems = projects.isSuccess ? projects.data.items : [];
  const ready = projectUid !== '' && assignee !== '' && !create.isPending;

  return (
    <form
      className="am-form"
      data-create-assignment=""
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready) return;
        create.mutate(
          { projectUid, documentUid: documentUid === '' ? null : documentUid, assigneeUserUid: assignee, note },
          {
            onSuccess: (assignment) => {
              setCreated({ uid: assignment.assignment_uid, what: assignmentScope(assignment), who: assignment.assignee_label });
              setDocumentUid('');
              setNote('');
            },
          },
        );
      }}
    >
      <label className="am-form__field">
        Проект
        <select
          value={projectUid}
          required
          onChange={(event) => {
            setProjectUid(event.target.value);
            setDocumentUid('');
          }}
        >
          <option value="">Выберите проект</option>
          {projectItems.map((project) => (
            <option key={project.project_uid} value={project.project_uid}>
              {project.name}
            </option>
          ))}
        </select>
      </label>
      {projectUid === '' ? null : (
        <DocumentChoice projectUid={projectUid} value={documentUid} onChange={setDocumentUid} />
      )}
      <label className="am-form__field">
        Эксперт
        <select value={assignee} required onChange={(event) => setAssignee(event.target.value)}>
          <option value="">Выберите эксперта</option>
          {experts.map((expert) => (
            <option key={expert.userUid} value={expert.userUid}>
              {expert.label}
            </option>
          ))}
        </select>
      </label>
      <label className="am-form__field">
        Комментарий (необязательно)
        <textarea value={note} maxLength={2000} rows={2} onChange={(event) => setNote(event.target.value)} />
      </label>
      <div className="am-form__row">
        <button type="submit" className="am-button" disabled={!ready} data-create-assignment-submit="">
          Назначить
        </button>
        {projectUid === '' || assignee === '' ? (
          <span className="am-form__hint" data-create-assignment-hint="">
            {projectUid === '' ? 'Выберите проект' : 'Выберите эксперта'}, чтобы назначить работу.
          </span>
        ) : null}
      </div>
      {created !== null && !create.isError ? (
        <p className="am-form__created" role="status" data-create-assignment-done={created.uid}>
          Назначение создано. {created.what}, ответственный: {created.who}.
        </p>
      ) : null}
      {create.isError ? (() => {
        const failure = assignmentFailure(create.error);
        return (
          <div data-create-assignment-failure={failure.kind}>
            <ErrorState title="Назначение не создано." detail={failure.detail} correlationId={failure.correlationId} />
          </div>
        );
      })() : null}
    </form>
  );
}
