/**
 * The script that puts a stored appearance choice on the document before the first paint.
 *
 * `ThemeToggle` (`web/src/_app/theme-toggle.tsx`) reads the stored choice in an effect, which
 * runs after hydration, so a visitor who chose the OPPOSITE of their system's preference saw
 * one frame (in practice a flash of several hundred milliseconds on a slow page) of the system
 * theme first. This is the other half of that component: a blocking inline script, run by the
 * root layout in `<head>` before any of the body is painted, that applies the same stored
 * choice to the same element.
 *
 * It is **a function of three names and no more** — the storage key, the attribute and the
 * choices — and the root layout passes it the constants of `_app/theme.ts`, so there is one
 * spelling of each and the script cannot drift from the component that writes the choice.
 * `web/tests/unit/styles/theme-boot-script.test.ts` runs the generated source against a fake
 * `document` and `localStorage` and holds it to `readThemeChoice` + `applyThemeChoice`.
 *
 * What it does is exactly what `applyThemeChoice` does on a first load, where the attribute
 * is absent: `light` or `dark` are written to `data-theme`; `system`, an unknown value and no
 * value write nothing, so the media query decides. Storage can throw (a browser set to refuse
 * it) and does not exist in some embedded views; both are the same case as "no stored choice"
 * and the system preference decides, which is a working page and not a degraded one, so the
 * `catch` is a statement of that and not a swallowed fault. The script reads, never writes.
 *
 * The source is built from `JSON.stringify` of its inputs and nothing else, so no input can
 * leave its string literal; and every `<` is written `\u003c`, which JavaScript reads as the
 * same character inside a string and an HTML parser does not read as the start of `</script>`,
 * so no input can end the element either.
 */

export interface ThemeBootScriptInput {
  /** The `localStorage` key the choice is kept under. */
  readonly storageKey: string;
  /** The attribute on the document element the palette blocks select on. */
  readonly attribute: string;
  /** Every choice there is; `system` (no attribute) is the one this script never writes. */
  readonly choices: readonly string[];
}

/** The `system` choice: the absence of one, which removes or never writes the attribute. */
const SYSTEM_CHOICE = 'system';

/** JavaScript source to put in a blocking inline `<script>` in `<head>`. */
export function themeBootScript(input: ThemeBootScriptInput): string {
  const writable = input.choices.filter((choice) => choice !== SYSTEM_CHOICE);
  const source =
    '(function(){try{' +
    `var c=window.localStorage.getItem(${JSON.stringify(input.storageKey)});` +
    `if(${JSON.stringify(writable)}.indexOf(c)>=0)` +
    `document.documentElement.setAttribute(${JSON.stringify(input.attribute)},c);` +
    '}catch(e){}})();';
  return source.replace(/</g, '\\u003c');
}
