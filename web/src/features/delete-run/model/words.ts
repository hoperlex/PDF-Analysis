/**
 * `RUN-DELETE-01`: the words of «Удалить прогон». One place, so the run page, a row of the list and the tests say the same thing.
 */

/** The button on the run page, beside «Отменить прогон». */
export const DELETE_RUN_OFFER = 'Удалить прогон';

/** The button in a row of the list: the row is the run, so the noun is dropped. */
export const DELETE_RUN_OFFER_SHORT = 'Удалить';

/** What the open confirmation asks. */
export const DELETE_RUN_QUESTION = 'Удалить прогон?';

/** What deleting does, in the owner's words: the run leaves every list, what it found and what the expert decided stays. */
export const DELETE_RUN_NOTE = 'Прогон исчезнет из списков. Замечания и решения эксперта сохранятся.';

export const DELETE_RUN_CONFIRM = 'Удалить';
export const DELETE_RUN_CANCEL = 'Отмена';

/** Said in place of the control once the server has answered, until the list is read again. */
export const DELETE_RUN_DONE = 'Прогон удалён.';

/** `409`: the run is not partial, failed or cancelled (`state_transition_not_allowed`). */
export const DELETE_RUN_NOT_DELETABLE = 'Этот прогон удалить нельзя: он не частичный, не с ошибкой и не отменён.';

/** `404`: another person deleted it first, or it never was. */
export const DELETE_RUN_GONE = 'Прогон уже удалён или не найден.';
