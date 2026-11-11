/**
 * «Как устроен этап» (`RUN-SCREEN-01a`, plan §9.4): three or four steps per chip, as the original's «Алгоритм этапа» states them.
 *
 * Each memo is written from the `purpose` of the stages the chip covers in `contracts/analysis/v1/stage-registry.json` (the extended
 * review's `comprehensive_analysis` from its procedure plan), in a reader's words: what goes in, what is done to it, what comes out.
 * The last step is the result. The text is a description of how the phase is built, not a reading of this run; it states nothing
 * about what a given run did.
 */

import type { RunChipDefinition } from '@/entities/audit-run';

export interface ChipAlgorithm {
  /** One line under the heading: what the phase is for. */
  readonly summary: string;
  /** Three or four steps, the last of them the result. */
  readonly steps: readonly string[];
}

export const CHIP_ALGORITHMS: Readonly<Record<RunChipDefinition['id'], ChipAlgorithm>> = {
  preparation: {
    summary: 'Готовит одинаковый вход для анализа текста и блоков. Модель не вызывается.',
    steps: [
      'PDF версии и его текстовый слой',
      'Страницы, блоки и их геометрия, изображения блоков',
      'Общий контекст документа для всех следующих этапов',
      'Один и тот же вход для текста и блоков',
    ],
  },
  text: {
    summary: 'Ищет несоответствия в текстовой части документа.',
    steps: [
      'Текстовый слой и общий контекст документа',
      'Правила проверки для раздела проекта',
      'Модель ищет несоответствия в тексте',
      'Текстовые наблюдения',
    ],
  },
  blocks: {
    summary: 'Ищет несоответствия в блоках: на изображениях, схемах и таблицах.',
    steps: [
      'Изображения блоков, их геометрия и общий контекст',
      'Модель смотрит блоки окнами и пакетами',
      'Каждый ответ проверяется по источникам',
      'Наблюдения по блокам',
    ],
  },
  cross_check: {
    summary: 'Сверяет источники между собой, в окне и между окнами.',
    steps: [
      'Наблюдения окон и текст страниц по частям',
      'Модель сверяет источники друг с другом и с параметрами проекта',
      'Каждый ответ проверяется по цитатам',
      'Наблюдения сверки',
    ],
  },
  merge: {
    summary: 'Собирает общий список без потери авторства. Модель не вызывается.',
    steps: [
      'Наблюдения текста и блоков',
      'Объединение по пересекающимся доказательствам и совпадающим цитатам',
      'Основным остаётся самое раннее по странице и месту',
      'Единый список наблюдений',
    ],
  },
  norms: {
    summary: 'Проверяет нормативные ссылки и цитаты.',
    steps: [
      'Наблюдение и его ссылка на норму',
      'Поиск пункта в закреплённом снимке норм',
      'Модель сверяет смысл и точную цитату',
      'Подтверждённая, исправленная или неподтверждённая ссылка',
    ],
  },
  review: {
    summary: 'Оценивает обоснованность каждого наблюдения. Это рекомендация, не решение эксперта.',
    steps: [
      'Свод наблюдений и контекст документа',
      'Проверка обоснованности каждого наблюдения',
      'Вердикт записывается рядом, доказательства не меняются',
      'Рекомендации критика',
    ],
  },
  correction: {
    summary: 'Предлагает уточнённые формулировки. Свод остаётся без изменений.',
    steps: [
      'Наблюдения и рекомендации критика',
      'Модель предлагает уточнённую формулировку',
      'Исходный свод не меняется',
      'Предложения по уточнению для эксперта',
    ],
  },
};
