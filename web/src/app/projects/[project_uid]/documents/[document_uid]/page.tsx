/**
 * `/projects/{project_uid}/documents/{document_uid}` — one document and its versions.
 *
 * Delegation-only, like every route file here: the route decides nothing.
 *
 * Added by `W19-SHELL` for `D-16`. `web/docs/PC01_UI_SEAM.md` §2 froze four URLs and said
 * "there is no route for a document version"; that sentence is the defect, and the table
 * is amended in the same commit as this file rather than left to contradict the tree.
 *
 * The parameter names are the contract's path parameter names exactly — `project_uid`,
 * `document_uid` — and nothing in the UI parses either for meaning.
 */

import { DocumentDetailPage } from '@/_pages/document-detail';

export default async function DocumentRoute({
  params,
}: {
  params: Promise<{ project_uid: string; document_uid: string }>;
}) {
  const { project_uid, document_uid } = await params;
  return <DocumentDetailPage projectUid={project_uid} documentUid={document_uid} />;
}
