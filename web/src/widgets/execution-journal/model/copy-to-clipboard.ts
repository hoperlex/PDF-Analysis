/**
 * Put text on the clipboard, and say whether it got there.
 *
 * `navigator.clipboard` is absent outside a secure context and refuses without permission, and a
 * refusal is an ordinary answer, not a fault: the caller shows it. The clipboard is passed in so a
 * test can hand it a refusing one; the page passes `browserClipboard()`.
 */
export interface TextClipboard {
  readonly writeText: (text: string) => Promise<void>;
}

/** The browser's clipboard, or `undefined` where there is none (no browser, or an insecure context). */
export function browserClipboard(): TextClipboard | undefined {
  return typeof navigator === 'undefined' ? undefined : navigator.clipboard;
}

/** `true` when the text was written; `false` when there is no clipboard or it refused. */
export async function copyToClipboard(text: string, clipboard: TextClipboard | undefined): Promise<boolean> {
  if (clipboard === undefined) return false;
  try {
    await clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
