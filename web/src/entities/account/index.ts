/**
 * Public API of the `account` entity (`W50-PLAN.md` §3.6). Importers use
 * `@/entities/account` and nothing deeper.
 *
 * `W50-HOME-01` and `W50-SHELL-FRAME` consume it: the Russian role labels, the name and the
 * avatar's letters, and the `account.me` query.
 */

export {
  MalformedAccountError,
  ROLE_LABELS,
  rolesCombinationAllowed,
  ASSIGNABLE_ROLES,
  VIEWER_ROLE_OFFERED,
  UnknownRoleError,
  displayLabelOf,
  initialsOf,
  isKnownRole,
  roleLabel,
  roleLabels,
  unreadableAccountDetail,
} from './model/account';

export { meQueryOptions, useMe } from './api/use-me';
export { mayActAsExpert, useMayActAsExpert } from './api/use-may-act';
