/**
 * The one switch of the «no human reviewed this» wording (`R-146ba`, accepted risks `A-10`, `A-11`).
 *
 * During the beta the owner took two indications off the screens: the profile label «рабочая версия,
 * проверка человеком не проводилась» and the wording that tells the user an АР v3 citation is
 * provisional and waits for the expert. This constant is the only thing that decides whether they
 * are drawn. It is `false` for the beta. Setting it to `true` brings back every one of those
 * strings exactly as they were; nothing else has to change except the test that names the beta
 * default (`web/tests/unit/review-indication/review-indication-default.test.ts`), which goes red on
 * purpose so the change is deliberate.
 *
 * What the switch does NOT govern, by the owner's and the integrator's rule:
 *
 * - the label above the version-comparison summary «Сводка подготовлена моделью, проверка человеком
 *   не проводилась»: it separates the model's text from the document's facts (`AGENTS.md` section 4);
 * - the attestation record of the sealed АР v3 pack in «Настройки анализа»;
 * - any statement that a verdict is the expert's own decision.
 *
 * It is read at the moment a string is built (a function or a render), never when a module loads, so
 * a test can set it for one case. A new string of this kind goes behind this constant the way the
 * existing ones do; `web/tests/guards/review-indication.guard.test.ts` fails on one that does not.
 */
export const SHOW_REVIEW_INDICATION = false as boolean;
