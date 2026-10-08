/** The second entry is UI confirmation only; it is never sent to the API. */
export function confirmedTemporaryPassword(password: string, repeat: string): string | null {
  return password.length > 0 && password === repeat ? password : null;
}
