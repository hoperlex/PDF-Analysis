/**
 * Three presentation-only sign-in concepts. Run from any directory:
 *   node docs/design/login-concepts/generate.mjs
 *
 * The PDF pages are 1440×900 desktop mockups, rendered at 2×. No application
 * source or user data is read; the SVGs below are the editable design source.
 */
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../../../web/package.json', import.meta.url));
const sharp = require('sharp');
const OUT = dirname(fileURLToPath(import.meta.url));
const W = 1440;
const H = 900;

const palettes = {
  light: {
    bg: '#edf4f2', paper: '#fdfefe', card: '#ffffff', soft: '#e6f0ef', ink: '#122529',
    muted: '#3f5b60', faint: '#6d898b', line: '#c8d9d6', accent: '#006a6c',
    bright: '#16a8a0', glow: '#c7ebe4', deep: '#073b43', white: '#ffffff',
  },
  dark: {
    bg: '#0d1118', paper: '#171e28', card: '#1a2029', soft: '#23303a', ink: '#eaf7f5',
    muted: '#b7caca', faint: '#819a9b', line: '#34444c', accent: '#69e4d1',
    bright: '#a3fff1', glow: '#103e42', deep: '#06191d', white: '#ffffff',
  },
};

function e(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}
function rr(x, y, w, h, r, fill, stroke = 'none', sw = 1, extra = '') {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`;
}
function circle(x, y, r, fill, stroke = 'none', sw = 1, extra = '') {
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`;
}
function ln(x1, y1, x2, y2, stroke, sw = 1, extra = '') {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`;
}
function path(d, fill = 'none', stroke = 'none', sw = 1, extra = '') {
  return `<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`;
}
function tx(x, y, label, size, color, weight = 400, extra = '') {
  return `<text x="${x}" y="${y}" font-family="Ubuntu Sans, DejaVu Sans, sans-serif" font-size="${size}" font-weight="${weight}" fill="${color}" ${extra}>${e(label)}</text>`;
}
function lines(x, y, list, size, color, weight = 400, step = size * 1.35, extra = '') {
  return list.map((line, i) => tx(x, y + i * step, line, size, color, weight, extra)).join('');
}
function svg(p, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <linearGradient id="canvas" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${p.bg}"/><stop offset="1" stop-color="${p.soft}"/></linearGradient>
    <linearGradient id="teal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${p.accent}"/><stop offset="1" stop-color="${p.bright}"/></linearGradient>
    <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${p.paper}"/><stop offset="1" stop-color="${p.soft}"/></linearGradient>
    <radialGradient id="halo"><stop offset="0" stop-color="${p.bright}" stop-opacity=".32"/><stop offset=".52" stop-color="${p.accent}" stop-opacity=".11"/><stop offset="1" stop-color="${p.accent}" stop-opacity="0"/></radialGradient>
    <filter id="lift" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="16" stdDeviation="22" flood-color="${p.deep}" flood-opacity=".16"/></filter>
    <filter id="blur"><feGaussianBlur stdDeviation="26"/></filter>
  </defs>
  ${rr(0, 0, W, H, 0, p.bg)}${body}</svg>`;
}

function logo(x, y, size, p) {
  return `<svg x="${x}" y="${y}" width="${size}" height="${size}" viewBox="0 0 36 36" fill="none" aria-hidden="true">
    <path d="M4.5 24.5 12 10.8a4.1 4.1 0 0 1 7.2 0l7.4 13.7" stroke="${p.accent}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M11.6 24.5 19 10.8a4.1 4.1 0 0 1 7.2 0l5.3 9.8" stroke="${p.accent}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M8.8 18.3h18.4" stroke="${p.accent}" stroke-width="2.2" stroke-linecap="round"/></svg>`;
}
function icon(x, y, kind, color) {
  const s = `stroke="${color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" fill="none"`;
  const shapes = {
    folder: '<path d="M2 7V5a2 2 0 0 1 2-2h5l2 2h9a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7Zm0 3h20"/>',
    grid: '<rect x="2" y="2" width="8" height="8" rx="1.5"/><rect x="14" y="2" width="8" height="8" rx="1.5"/><rect x="2" y="14" width="8" height="8" rx="1.5"/><rect x="14" y="14" width="8" height="8" rx="1.5"/>',
    compare: '<path d="M4 7h16m-4-3 4 3-4 3M20 17H4m4-3-4 3 4 3"/>',
    stages: '<rect x="3" y="4" width="7" height="16" rx="1.5"/><rect x="14" y="4" width="7" height="16" rx="1.5"/><path d="m10 9 4 3-4 3"/>',
    book: '<path d="M12 5C9 3 6 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Zm0 0v15"/>',
    file: '<path d="M6 3h9l4 4v14H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm9 0v4h4M8 12h8M8 16h6"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M19 5l-2 2M7 17l-2 2"/>',
  };
  return `<svg x="${x}" y="${y}" width="17" height="17" viewBox="0 0 24 24" ${s}>${shapes[kind]}</svg>`;
}
function sidebar(p) {
  const x = 18, y = 18, w = 218, h = 864;
  let s = rr(x, y, w, h, 24, p.paper, p.line, 1, 'filter="url(#lift)"');
  s += logo(36, 39, 29, p) + tx(69, 60, 'AuditManager', 17, p.ink, 700);
  s += circle(207, 52, 13, p.soft, p.line) + path('M210 47l-5 5 5 5', 'none', p.muted, 1.5, 'stroke-linecap="round" stroke-linejoin="round"');
  s += ln(37, 85, 216, 85, p.line, 1);
  s += tx(40, 117, 'ПРЕВЬЮ РАЗДЕЛОВ', 10, p.faint, 700, 'letter-spacing="1.3"');
  const groups = [
    { label: 'РАБОЧЕЕ', y: 147, rows: [['Проекты', 'folder'], ['Дашборд', 'grid'], ['Сравнение версий', 'compare'], ['Сравнение стадий', 'stages']] },
    { label: 'ЗНАНИЯ', y: 349, rows: [['База знаний', 'book'], ['Нормы', 'file']] },
    { label: 'СИСТЕМА', y: 487, rows: [['Настройки анализа', 'settings']] },
  ];
  for (const group of groups) {
    s += tx(40, group.y, group.label, 10, p.faint, 650, 'letter-spacing="1.4"');
    s += ln(46, group.y + 17, 46, group.y + 22 + group.rows.length * 38, p.line, 1);
    group.rows.forEach(([label, kind], i) => {
      const cy = group.y + 38 + i * 38;
      s += ln(46, cy - 5, 59, cy - 5, p.line, 1);
      s += icon(64, cy - 14, kind, p.faint) + tx(90, cy, label, 12.5, p.muted, 450);
    });
  }
  s += ln(38, 689, 216, 689, p.line, 1);
  s += rr(36, 714, 182, 139, 17, p.soft, p.line, 1);
  s += circle(58, 739, 11, p.glow) + tx(54.2, 743, '↗', 14, p.accent, 700);
  s += tx(77, 744, 'После входа', 12, p.ink, 650);
  s += lines(49, 773, ['Рабочие разделы и проекты', 'откроются после авторизации.'], 11.5, p.muted, 450, 17);
  s += rr(49, 813, 154, 27, 13, p.paper, p.line) + tx(64, 831, 'Только превью', 10.5, p.accent, 650);
  return s;
}
function topbar(p) {
  let s = ln(258, 96, 1420, 96, p.line, 1);
  s += rr(266, 24, 214, 49, 14, p.paper, p.line) + circle(285, 48, 4, p.accent);
  s += tx(299, 43, 'УЧЁТНАЯ ЗАПИСЬ', 10, p.faint, 700, 'letter-spacing="1.1"');
  s += tx(299, 61, 'Вход', 14, p.ink, 650);
  s += rr(1088, 29, 125, 39, 19, p.paper, p.line) + circle(1105, 48, 4, p.accent);
  s += tx(1117, 52, 'Гостевой режим', 11.5, p.muted, 500);
  s += rr(1225, 29, 84, 39, 19, p.paper, p.line) + circle(1247, 48, 14, p.glow);
  s += tx(1241, 53, '☼', 17, p.accent, 600) + tx(1283, 53, '☾', 17, p.muted, 500);
  s += rr(1321, 29, 93, 39, 19, p.paper, p.line) + tx(1343, 53, 'Вход', 12.5, p.ink, 650);
  return s;
}
function frame(p, content, id, theme) {
  let s = sidebar(p) + topbar(p) + content;
  s += tx(1326, 878, `${id} · ${theme === 'light' ? 'СВЕТЛАЯ' : 'ТЁМНАЯ'}`, 10, p.faint, 650, 'text-anchor="end" letter-spacing="1"');
  return svg(p, s);
}

function field(p, x, y, w, label, placeholder, password = false) {
  let s = tx(x, y, label, 12.5, p.ink, 600);
  s += rr(x, y + 11, w, 51, 12, p.soft, p.line);
  s += tx(x + 15, y + 44, password ? '••••••••••' : placeholder, 13.5, p.muted, 420);
  if (password) s += circle(x + w - 23, y + 36, 6, 'none', p.faint, 1.5) + ln(x + w - 31, y + 45, x + w - 15, y + 27, p.faint, 1.5);
  return s;
}
function formCard(p, x, y, w, h, kicker = 'ВХОД В СИСТЕМУ') {
  let s = rr(x, y, w, h, 25, p.card, p.line, 1, 'filter="url(#lift)"');
  s += rr(x + 27, y + 29, 33, 33, 11, p.glow) + logo(x + 31, y + 33, 25, p);
  s += tx(x + 72, y + 42, kicker, 10.5, p.accent, 700, 'letter-spacing="1"');
  s += tx(x + 72, y + 62, 'Продолжить работу', 21, p.ink, 700);
  s += lines(x + 28, y + 96, ['Почта или прежний логин — как в текущем приложении.'], 11.5, p.muted, 400);
  s += field(p, x + 28, y + 138, w - 56, 'Адрес электронной почты', 'Почта или прежний логин');
  s += field(p, x + 28, y + 229, w - 56, 'Пароль', 'Пароль', true);
  s += rr(x + 28, y + 324, w - 56, 51, 13, 'url(#teal)');
  s += tx(x + 49, y + 356, 'Войти', 14, p.white, 700) + tx(x + w - 65, y + 356, '→', 22, p.white, 400);
  s += tx(x + 28, y + 410, 'Нет учётной записи?', 12, p.muted, 450);
  s += tx(x + 188, y + 410, 'Подать заявку на доступ', 12, p.accent, 650);
  s += ln(x + 28, y + 433, x + w - 28, y + 433, p.line);
  s += tx(x + 28, y + 456, 'Доступ к данным — после авторизации', 11, p.faint, 450);
  return s;
}

function workstation(p, theme) {
  let s = circle(1130, 400, 330, 'url(#halo)');
  s += tx(286, 155, 'КОНЦЕПЦИЯ 01 / РАБОЧАЯ СТАНЦИЯ', 11, p.accent, 700, 'letter-spacing="1.6"');
  s += lines(286, 213, ['Возвращайтесь', 'к ясным решениям.'], 48, p.ink, 700, 54, 'letter-spacing="-1.5"');
  s += lines(289, 300, ['Проверка проектной документации, анализ и экспертные решения', 'в одном рабочем пространстве.'], 15, p.muted, 430, 22);
  s += formCard(p, 286, 347, 479, 487);

  s += rr(810, 157, 558, 676, 28, p.paper, p.line, 1, 'filter="url(#lift)"');
  s += tx(837, 193, 'РАБОЧЕЕ ПРОСТРАНСТВО', 10.5, p.faint, 700, 'letter-spacing="1.3"');
  s += rr(1237, 171, 103, 27, 13, p.glow) + tx(1257, 189, 'ДЕМО', 10.5, p.accent, 700);
  s += tx(837, 232, 'От документа до решения', 24, p.ink, 700);
  s += tx(837, 254, 'Визуальный обзор процесса после входа', 12, p.muted, 430);
  s += rr(837, 281, 504, 174, 20, p.soft, p.line);
  s += tx(857, 308, 'ЭТАПЫ АНАЛИЗА', 10.5, p.faint, 700, 'letter-spacing="1.1"');
  s += ln(887, 365, 1291, 365, p.line, 3);
  const stages = [['01', 'Документ'], ['02', 'Анализ'], ['03', 'Проверка'], ['04', 'Решение']];
  stages.forEach(([n, label], i) => {
    const x = 885 + i * 134;
    s += circle(x, 365, 23, i === 1 ? p.accent : p.paper, i === 1 ? p.accent : p.line, 1.5);
    s += tx(x, 371, n, 12, i === 1 ? p.white : p.muted, 700, 'text-anchor="middle"');
    s += tx(x, 408, label, 11.5, i === 1 ? p.accent : p.muted, i === 1 ? 650 : 450, 'text-anchor="middle"');
  });
  s += tx(837, 492, 'Разделы проекта', 17, p.ink, 650);
  const rows = [['АР', 'Архитектурные решения', 'В работе'], ['КР', 'Конструктивные решения', 'Доступно'], ['ОВ', 'Внутренние сети', 'Доступно']];
  rows.forEach(([code, label, status], i) => {
    const y = 515 + i * 92;
    s += rr(837, y, 504, 78, 16, p.card, p.line);
    s += rr(852, y + 16, 46, 46, 12, i === 0 ? p.glow : p.soft);
    s += tx(875, y + 45, code, 13, i === 0 ? p.accent : p.muted, 700, 'text-anchor="middle"');
    s += tx(911, y + 34, label, 13, p.ink, 600);
    s += tx(911, y + 56, 'Предпросмотр без данных проекта', 10.5, p.faint, 420);
    s += rr(1238, y + 24, 87, 28, 14, i === 0 ? p.glow : p.soft);
    s += tx(1281, y + 43, status, 10.5, i === 0 ? p.accent : p.muted, 600, 'text-anchor="middle"');
  });
  return frame(p, s, '01', theme);
}

function documentFocus(p, theme) {
  let s = circle(592, 502, 365, 'url(#halo)');
  s += tx(290, 170, 'КОНЦЕПЦИЯ 02 / ДОКУМЕНТ В ФОКУСЕ', 11, p.accent, 700, 'letter-spacing="1.6"');
  s += lines(290, 229, ['Смысл проекта —', 'на первом плане.'], 47, p.ink, 700, 53, 'letter-spacing="-1.4"');
  s += lines(292, 334, ['Загрузите документ. Увидьте связи. Проверьте выводы.', 'Каждый шаг остаётся понятным эксперту.'], 15, p.muted, 430, 22);

  s += `<g transform="rotate(-9 490 583)">`;
  s += rr(331, 405, 347, 356, 20, p.soft, p.line, 1, 'filter="url(#lift)"');
  s += rr(351, 428, 307, 316, 14, p.card, p.line);
  s += rr(371, 449, 117, 25, 12, p.glow) + tx(382, 466, 'PDF / ПРИМЕР', 10, p.accent, 700);
  s += tx(372, 510, 'АР · Архитектурные', 18, p.ink, 650) + tx(372, 536, 'решения', 18, p.ink, 650);
  [565, 588, 611, 634, 657].forEach((y, i) => { s += rr(372, y, i === 3 ? 176 : 254, 7, 3, i === 2 ? p.glow : p.line); });
  s += rr(371, 687, 157, 32, 10, p.glow) + tx(389, 708, 'Контекст сохранён', 11, p.accent, 650);
  s += `</g>`;
  s += `<g transform="rotate(7 644 587)">`;
  s += rr(522, 424, 264, 315, 18, p.paper, p.line, 1, 'filter="url(#lift)"');
  s += rr(546, 447, 216, 75, 14, p.glow) + tx(560, 472, 'НАЙДЕННЫЕ СВЯЗИ', 10, p.accent, 700, 'letter-spacing=".8"');
  s += tx(560, 500, 'Норма ↔ фрагмент', 14, p.ink, 650);
  [550, 593, 636, 679].forEach((y, i) => {
    s += circle(557, y, 6, i === 1 ? p.accent : p.line) + rr(574, y - 4, i === 2 ? 121 : 156, 8, 4, p.line);
  });
  s += `</g>`;
  s += path('M334 652C454 502 623 718 784 512', 'none', p.bright, 4, 'opacity=".75" stroke-linecap="round"');
  s += circle(784, 512, 8, p.accent, p.card, 3);

  s += formCard(p, 886, 201, 448, 523, 'ВАШЕ РАБОЧЕЕ ПРОСТРАНСТВО');
  s += rr(903, 747, 414, 67, 16, p.soft, p.line);
  s += circle(927, 780, 10, p.glow) + tx(923.2, 784, '✓', 13, p.accent, 700);
  s += lines(949, 775, ['Вход ведёт к вашим проектам.', 'Пример документов слева не содержит данных.'], 11, p.muted, 450, 17);
  return frame(p, s, '02', theme);
}

function signalOrbit(p, theme) {
  let s = circle(1070, 497, 410, 'url(#halo)');
  s += tx(290, 164, 'КОНЦЕПЦИЯ 03 / СИГНАЛЬНАЯ ОРБИТА', 11, p.accent, 700, 'letter-spacing="1.6"');
  s += lines(290, 220, ['Точность начинается', 'со входа.'], 47, p.ink, 700, 53, 'letter-spacing="-1.4"');
  s += lines(292, 321, ['Один вход — и вся цепочка проверки перед вами.', 'От файла до объяснимого экспертного решения.'], 15, p.muted, 430, 22);
  s += formCard(p, 287, 367, 467, 481);

  s += rr(826, 173, 530, 627, 31, p.paper, p.line, 1, 'filter="url(#lift)"');
  s += tx(855, 208, 'ДЕМОНСТРАЦИЯ СЦЕНАРИЯ', 10.5, p.faint, 700, 'letter-spacing="1.3"');
  s += rr(1213, 188, 113, 28, 14, p.glow) + tx(1269, 207, 'НЕ ДАННЫЕ', 10, p.accent, 700, 'text-anchor="middle"');
  s += tx(855, 245, 'Проверка как система связей', 21, p.ink, 700);
  s += circle(1091, 520, 221, 'url(#halo)');
  [173, 140, 107, 73].forEach((r, i) => { s += circle(1091, 521, r, 'none', i % 2 ? p.line : p.glow, 1.5, `stroke-dasharray="${i === 1 ? '7 10' : '1 0'}"`); });
  s += path('M918 521a173 173 0 0 1 266-146', 'none', p.accent, 5, 'stroke-linecap="round" opacity=".85"');
  s += path('M1198 597a140 140 0 0 1-214 49', 'none', p.bright, 4, 'stroke-linecap="round" opacity=".7"');
  s += circle(1091, 521, 62, p.card, p.accent, 2, 'filter="url(#lift)"') + logo(1058, 488, 66, p);
  const nodes = [
    { x: 1091, y: 348, n: '01', label: 'Документ' },
    { x: 1240, y: 598, n: '02', label: 'Анализ' },
    { x: 944, y: 599, n: '03', label: 'Эксперт' },
  ];
  nodes.forEach((node, i) => {
    s += circle(node.x, node.y, 27, i === 1 ? p.accent : p.card, p.line, 1.5);
    s += tx(node.x, node.y + 5, node.n, 12, i === 1 ? p.white : p.accent, 700, 'text-anchor="middle"');
    s += tx(node.x, node.y + (i === 0 ? -42 : 50), node.label, 11, p.muted, 600, 'text-anchor="middle"');
  });
  s += rr(861, 729, 460, 47, 15, p.soft, p.line);
  s += circle(882, 752, 5, p.accent) + tx(898, 757, 'Управляемый процесс · прозрачные этапы', 12, p.muted, 550);
  return frame(p, s, '03', theme);
}

const concepts = [
  {
    file: '01-workstation.pdf', name: 'Рабочая станция', mode: 'Спокойный продуктовый экран',
    intro: ['Знакомая рабочая оболочка помогает сразу понять,', 'куда попадёт пользователь после авторизации.'],
    motion: [
      ['01 · Появление', 'Панель, хедер и форма входят', 'за 320 мс с мягким смещением 8 px.', 'Поля появляются каскадом 60 мс.'],
      ['02 · Живой процесс', 'Линия четырёх этапов медленно', 'подсвечивается по кругу за 8 секунд.', 'Превью не изображает реальные данные.'],
      ['03 · Действие', 'Фокус поля: цветная рамка 160 мс.', 'После отправки — «Входим…»', 'в пределах той же кнопки.'],
    ],
    timeline: [['0 мс', 'Оболочка'], ['180 мс', 'Форма'], ['460 мс', 'Поля'], ['Покой', 'Тихая линия']],
    draw: workstation,
  },
  {
    file: '02-document-focus.pdf', name: 'Документ в фокусе', mode: 'Редакционный, презентационный',
    intro: ['Образ документа делает назначение продукта очевидным,', 'а форма остаётся главным действием справа.'],
    motion: [
      ['01 · Слои', 'Карточки документа входят с разницей', '100 мс; глубина — до 12 px при движении', 'указателя, без движения самой формы.'],
      ['02 · Сканирование', 'Тонкий луч проходит по фрагментам', 'раз в 5 секунд и высвечивает связи.', 'Это декоративный цикл, без обращения к API.'],
      ['03 · Вход', 'Форма проявляется за 420 мс.', 'При фокусе на ней фоновое движение', 'ставится на паузу. Ошибка не сдвигает поля.'],
    ],
    timeline: [['0 мс', 'Заголовок'], ['180 мс', 'Документы'], ['420 мс', 'Форма'], ['Покой', 'Скан-линия']],
    draw: documentFocus,
  },
  {
    file: '03-signal-orbit.pdf', name: 'Сигнальная орбита', mode: 'Смелая имиджевая композиция',
    intro: ['Орбита объясняет связность анализа, норм и экспертного', 'решения, не притворяясь реальным дашбордом.'],
    motion: [
      ['01 · Орбита', 'Внешние дуги вращаются очень медленно:', '24 секунды на оборот. Узлы остаются', 'неподвижны, поэтому подписи не прыгают.'],
      ['02 · Отклик', 'При наведении и фокусе подсветка', 'переходит к соответствующему узлу.', 'Кнопка имеет короткий световой проход.'],
      ['03 · Приоритет формы', 'Форма всегда поверх визуального слоя.', 'Во время ввода свечение приглушается.', 'Ошибки показываются текстом без тряски.'],
    ],
    timeline: [['0 мс', 'Заголовок'], ['240 мс', 'Орбита'], ['500 мс', 'Форма'], ['Покой', 'Медленный цикл']],
    draw: signalOrbit,
  },
];

function notes(concept, n) {
  const p = palettes.light;
  let s = rr(0, 0, W, H, 0, p.bg);
  s += circle(1280, 130, 260, 'url(#halo)');
  s += tx(78, 75, `AUDITMANAGER / КОНЦЕПЦИЯ 0${n}`, 12, p.accent, 700, 'letter-spacing="1.5"');
  s += tx(78, 134, concept.name, 42, p.ink, 700, 'letter-spacing="-1"');
  s += tx(80, 169, concept.mode, 16, p.muted, 500);
  s += lines(80, 205, concept.intro, 14, p.muted, 430, 21);
  const cols = [78, 510, 942];
  concept.motion.forEach((item, i) => {
    const x = cols[i];
    s += rr(x, 272, 404, 282, 22, p.paper, p.line, 1, 'filter="url(#lift)"');
    s += rr(x + 23, 296, 46, 32, 10, p.glow) + tx(x + 46, 317, `0${i + 1}`, 12, p.accent, 700, 'text-anchor="middle"');
    s += tx(x + 23, 366, item[0].slice(5), 21, p.ink, 700);
    s += lines(x + 23, 414, item.slice(1), 14, p.muted, 430, 25);
  });
  s += tx(80, 614, 'СЦЕНАРИЙ ПО ВРЕМЕНИ', 11, p.accent, 700, 'letter-spacing="1.5"');
  s += rr(78, 635, 1268, 124, 21, p.paper, p.line);
  s += ln(178, 692, 1247, 692, p.line, 3);
  concept.timeline.forEach(([when, what], i) => {
    const x = 178 + i * 356;
    s += circle(x, 692, 10, i === 3 ? p.paper : p.accent, p.accent, 2);
    s += tx(x, 676, when, 12, p.accent, 700, 'text-anchor="middle"');
    s += tx(x, 726, what, 13, p.ink, 600, 'text-anchor="middle"');
  });
  s += rr(78, 785, 1268, 68, 16, p.glow);
  s += circle(106, 819, 13, p.paper) + tx(101.3, 823, '✓', 14, p.accent, 700);
  s += tx(132, 815, 'Доступность и адаптация', 13.5, p.ink, 700);
  s += tx(132, 836, 'При reduced motion все декоративные циклы выключены. На планшете панель сжимается до иконок, на телефоне становится верхним меню.', 12.5, p.muted, 450);
  return svg(p, s);
}

function pdfFromJpegs(jpegs) {
  const objs = [null];
  objs[1] = Buffer.from('<< /Type /Catalog /Pages 2 0 R >>');
  objs[2] = Buffer.from(`<< /Type /Pages /Kids [${jpegs.map((_, i) => `${3 + i * 3} 0 R`).join(' ')}] /Count ${jpegs.length} >>`);
  for (let i = 0; i < jpegs.length; i += 1) {
    const page = 3 + i * 3, content = page + 1, image = page + 2;
    objs[page] = Buffer.from(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${W} ${H}] /Resources << /XObject << /Im0 ${image} 0 R >> >> /Contents ${content} 0 R >>`);
    const commands = Buffer.from(`q\n${W} 0 0 ${H} 0 0 cm\n/Im0 Do\nQ\n`);
    objs[content] = Buffer.concat([Buffer.from(`<< /Length ${commands.length} >>\nstream\n`), commands, Buffer.from('endstream')]);
    objs[image] = Buffer.concat([
      Buffer.from(`<< /Type /XObject /Subtype /Image /Width ${W * 2} /Height ${H * 2} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegs[i].length} >>\nstream\n`),
      jpegs[i], Buffer.from('\nendstream'),
    ]);
  }
  const chunks = [Buffer.from('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n', 'latin1')];
  const offsets = [0];
  let size = chunks[0].length;
  for (let id = 1; id < objs.length; id += 1) {
    offsets[id] = size;
    const chunk = Buffer.concat([Buffer.from(`${id} 0 obj\n`), objs[id], Buffer.from('\nendobj\n')]);
    chunks.push(chunk);
    size += chunk.length;
  }
  const xref = size;
  chunks.push(Buffer.from(`xref\n0 ${objs.length}\n0000000000 65535 f \n${offsets.slice(1).map((n) => `${String(n).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size ${objs.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`));
  return Buffer.concat(chunks);
}

await mkdir(OUT, { recursive: true });
for (const [i, concept] of concepts.entries()) {
  const pages = [concept.draw(palettes.light, 'light'), concept.draw(palettes.dark, 'dark'), notes(concept, i + 1)];
  const jpegs = [];
  for (const page of pages) {
    const image = await sharp(Buffer.from(page)).resize(W * 2, H * 2).flatten({ background: '#ffffff' }).jpeg({ quality: 90, chromaSubsampling: '4:4:4' }).toBuffer();
    jpegs.push(image);
  }
  await writeFile(join(OUT, concept.file), pdfFromJpegs(jpegs));
  const preview = await sharp(Buffer.from(pages[0])).resize(960, 600).png().toBuffer();
  await writeFile(join(OUT, concept.file.replace('.pdf', '-preview.png')), preview);
  console.log(concept.file, '3 pages');
}
