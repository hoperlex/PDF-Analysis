/**
 * Who sees the server and the access of a run (`R-150w`, plan §9.4).
 *
 * The read-only role does not see the dispatcher's screens, and the name of the executor a run is on is the dispatcher's
 * information: «Наблюдатель» is shown the model and the stages, not the server. An account that is not known yet is left to the
 * server, as the screen's other operator controls are (`mayCancel`, `mayReadJournal`).
 */
export function maySeeServer(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}
