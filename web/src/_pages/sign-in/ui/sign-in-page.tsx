/**
 * `/login` — the screen that exchanges a login and a password for a session.
 *
 * Composition only, like every other page slice: the credentials card, centred in the shared
 * guest frame, around the form from the `sign-in` feature. No query, no mutation, no domain
 * rule and — the point of the whole design — no client JavaScript that could hold a
 * credential: the form's only script is the `SubmitLock` island, which reads no field (`C-22`).
 *
 * The screen has no copy of its own (owner, 2026-11-09): the hero text and the «Демонстрация
 * сценария» panel are gone, so the card's title is the page's one `h1`. Beside the card stands a
 * wordless animated scene and behind both a drifting dot grid — decoration only, hidden from
 * assistive technology and animated in CSS, so the slice still ships no script. The frame's
 * inert section preview stays beside it; this slice does not draw it.
 *
 * Variant «B · Чертёж на тёмном» (`STYLE-ORIG-01` S4, `R-157c`): the card is a drawing sheet
 * with a teal top edge and four crop marks, the scene is a plotter at work. Two sheets of a
 * building (a facade, a section) stand behind as faint teal wireframes; in front, a plotter
 * draws the floor plan in three bands, left to right, behind a teal crosshair cursor; three
 * CAD selection boxes then pick the window in the north wall, the stair and the bath; the
 * expert's stamp lands on the title block; a small axis symbol sits bottom-left. No word, no
 * data. The resting state — plan drawn, boxes and stamp in place, no cursor — is the finished
 * frame, and is what a browser asking for reduced motion sees.
 *
 * Only a guest sees this screen: the route's guard sends a browser that already holds a
 * session to `/` (`W50-PLAN.md` §3.2, decision five), and the frame's account menu carries
 * the way out. So the screen has one shape, the credentials form, and a link to the
 * registration form for someone who has no account yet (`C-21`).
 */

import Link from 'next/link';

import { REGISTER_SCREEN } from '@/shared/config/screen-registry';
import { ErrorState } from '@/shared/ui';
import type { SessionEndReason, SignInRefusal } from '@/features/sign-in';
import { SignInForm, signInReasonMessage } from '@/features/sign-in';

import styles from './sign-in-page.module.css';

export interface SignInPageProps {
  /**
   * Unused since `C-25`: the guard never renders this screen for a session. Still accepted
   * because the route file (`app/login/page.tsx`) passes it; drop it there and here together.
   */
  readonly login?: string | null | undefined;
  /** The refusal the last attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
  /** The validated address to return to once signed in (`W50-PLAN.md` §3.2), if any. */
  readonly next?: string | null | undefined;
  readonly unknownRefusal?: boolean | undefined;
  /**
   * Why there is no session, when the server knows (`expired`, `ended` or `invalid`): said above
   * the form in one sentence. Absent when it does not — a first visit says nothing.
   */
  readonly reason?: SessionEndReason | null | undefined;
}

export function SignInPage({ refusal, next, unknownRefusal = false, reason = null }: SignInPageProps) {
  return (
    <section className={styles.screen} aria-labelledby="sign-in-title">
      <Backdrop />
      <div className={styles.card}>
        <CropMarks />
        <header className={styles.header}>
          <span className={styles.signInMark} aria-hidden="true"><BrandMark /></span>
          <div>
            <p className={styles.cardEyebrow}>Вход в систему</p>
            <h1 className={styles.cardTitle} id="sign-in-title">Продолжить работу</h1>
          </div>
        </header>
        {reason === null ? null : (
          <p className={styles.reason} role="status" data-sign-in-reason={reason}>{signInReasonMessage(reason)}</p>
        )}
        <p className={styles.formLead}>Используйте почту или прежний логин для входа.</p>
        {unknownRefusal ? <div data-sign-in-refusal="unknown"><ErrorState title="Неизвестный ответ входа" detail="Сервер вернул состояние, которое эта версия страницы не понимает." /></div> : null}
        <SignInForm refusal={refusal} next={next} />
        <p className={styles.register} data-sign-in-register="">
          Нет учётной записи? <Link href={REGISTER_SCREEN}>Подать заявку на доступ</Link>
        </p>
        <p className={styles.accessNote}>Доступ к данным — после авторизации</p>
      </div>
      <Scene />
    </section>
  );
}

/** The four crop marks outside the card's corners, as on a drawing sheet. Decoration only. */
function CropMarks() {
  return (
    <>
      <span className={`${styles.crop} ${styles.cropTopLeft}`} aria-hidden="true" />
      <span className={`${styles.crop} ${styles.cropTopRight}`} aria-hidden="true" />
      <span className={`${styles.crop} ${styles.cropBottomLeft}`} aria-hidden="true" />
      <span className={`${styles.crop} ${styles.cropBottomRight}`} aria-hidden="true" />
    </>
  );
}

/**
 * The living background behind the card and the scene: a dot grid, a dot every 24 px and a
 * faint line every 120 px, that drifts by one major cell and repeats. The CSS masks it into the
 * page at the edges. Decoration only — hidden from assistive technology, no text, every colour
 * a token of the theme, motion in CSS.
 */
function Backdrop() {
  return (
    <div className={styles.backdrop} aria-hidden="true">
      <svg className={styles.backdropGrid} focusable="false">
        <defs>
          <pattern id="sign-in-grid-dot" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle className={styles.gridDot} cx="1" cy="1" r="1.1" />
          </pattern>
          <pattern id="sign-in-grid-major" width="120" height="120" patternUnits="userSpaceOnUse">
            <rect width="120" height="120" fill="url(#sign-in-grid-dot)" />
            <path className={styles.gridMajor} d="M120 0H0V120" fill="none" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#sign-in-grid-major)" />
      </svg>
    </div>
  );
}

/** The plotter's bands: each is hidden by a paper-coloured cover that slides off behind the cursor. */
const PLOT_BANDS = [
  { y: 10, height: 62, cover: styles.coverA },
  { y: 72, height: 60, cover: styles.coverB },
  { y: 132, height: 68, cover: styles.coverC },
] as const;

/**
 * The scene beside the card: three sheets of a building's drawings. Behind, a facade and a
 * section as faint wireframes; in front, a floor plan with its axes, openings, stair, sanitary
 * fittings, dimension chain, section cut and title block. A plotter draws the plan in three
 * bands: a cover per band slides away to the right behind a crosshair cursor (a vertical rail,
 * a horizontal rail and a small square head). Three selection boxes then pick the window in the
 * outer wall, the stair and the bath; the expert's stamp lands on the title block; everything
 * clears and the cycle (10 s) repeats. The resting state — plan drawn, boxes and stamp in
 * place, cursor hidden — is what a browser asking for reduced motion sees.
 */
function Scene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <svg viewBox="0 0 560 470" focusable="false">
        <defs>
          <clipPath id="sign-in-plan-area">
            <rect x="14" y="10" width="322" height="190" />
          </clipPath>
        </defs>
        <g transform="translate(4 18) rotate(-5 160 110) scale(.84)">
          <g className={`${styles.ghost} ${styles.floatSlow}`}>
            <FacadeSheet />
          </g>
        </g>
        <g transform="translate(268 0) rotate(4 160 110) scale(.84)">
          <g className={`${styles.ghost} ${styles.floatFast}`}>
            <SectionSheet />
          </g>
        </g>
        <g transform="translate(92 140) scale(1.25)">
          <SheetBase width={340} height={250} />
          <g className={styles.plotLines}>
            <PlanLines />
          </g>
          <g clipPath="url(#sign-in-plan-area)">
            {PLOT_BANDS.map(({ y, height, cover }) => (
              <rect key={y} className={`${styles.cover} ${cover ?? ''}`} x="14" y={y} width="322" height={height} />
            ))}
            <g className={styles.cursorV}>
              <path className={styles.rail} d="M0 10V200" />
            </g>
            <g className={styles.cursorH}>
              <path className={styles.rail} d="M14 0H336" />
            </g>
            <g className={styles.cursorHead}>
              <rect className={styles.headBox} x="-5" y="-5" width="10" height="10" />
              <path className={styles.headTick} d="M-16 0H-8M8 0H16M0 -16V-8M0 8V16" />
            </g>
          </g>
          <SelectionBox x={72} y={31} width={54} height={18} order={styles.selectionA} />
          <SelectionBox x={193} y={100} width={32} height={58} order={styles.selectionB} />
          <SelectionBox x={268} y={98} width={34} height={52} order={styles.selectionC} />
          <g transform="translate(278 222) rotate(-8)">
            <g className={styles.stamp}>
              <rect className={styles.stampOuter} x="-56" y="-26" width="112" height="52" rx="8" />
              <rect className={styles.stampInner} x="-49" y="-19" width="98" height="38" rx="5" />
              <path className={styles.stampCheck} d="M-36 0L-27 9L-10 -8" />
              <path className={styles.stampLines} d="M0 -8H38M0 1H30M0 10H34" />
            </g>
          </g>
        </g>
        <g className={styles.ucs} transform="translate(30 440)">
          <path d="M0 0H44M0 0V-44M38 -5L44 0L38 5M-5 -38L0 -44L5 -38" />
          <rect x="-4" y="-4" width="8" height="8" />
        </g>
      </svg>
    </div>
  );
}

/** A sheet's paper, its frame with the binding margin on the left, and its title block. */
function SheetBase({ width, height }: { readonly width: number; readonly height: number }) {
  const right = width - 8;
  const bottom = height - 8;
  return (
    <>
      <rect className={styles.paper} width={width} height={height} rx="4" />
      <rect className={styles.frame} x="18" y="8" width={right - 18} height={bottom - 8} />
      <path
        className={styles.frame}
        d={`M${right - 126} ${bottom}V${bottom - 42}H${right}M${right - 126} ${bottom - 28}H${right - 70}M${right - 126} ${bottom - 14}H${right - 70}M${right - 110} ${bottom - 42}V${bottom}M${right - 94} ${bottom - 42}V${bottom}M${right - 70} ${bottom - 42}V${bottom}M${right - 70} ${bottom - 20}H${right}M${right - 32} ${bottom - 20}V${bottom}M${right - 16} ${bottom - 20}V${bottom}`}
      />
      <path className={styles.inkThin} d={`M${right - 64} ${bottom - 34}H${right - 8}M${right - 64} ${bottom - 28}H${right - 24}`} />
    </>
  );
}

/** A window in a horizontal wall at `y`, from `x1` to `x2`: the wall broken, three lines of glazing. */
function WindowH({ x1, x2, y }: { readonly x1: number; readonly x2: number; readonly y: number }) {
  return (
    <>
      <rect className={styles.windowGap} x={x1} y={y - 3.5} width={x2 - x1} height="7" />
      <path className={styles.inkThin} d={`M${x1} ${y - 2.5}H${x2}M${x1} ${y}H${x2}M${x1} ${y + 2.5}H${x2}M${x1} ${y - 2.5}V${y + 2.5}M${x2} ${y - 2.5}V${y + 2.5}`} />
    </>
  );
}

/** A window in a vertical wall at `x`, from `y1` to `y2`. */
function WindowV({ y1, y2, x }: { readonly y1: number; readonly y2: number; readonly x: number }) {
  return (
    <>
      <rect className={styles.windowGap} x={x - 3.5} y={y1} width="7" height={y2 - y1} />
      <path className={styles.inkThin} d={`M${x - 2.5} ${y1}V${y2}M${x} ${y1}V${y2}M${x + 2.5} ${y1}V${y2}M${x - 2.5} ${y1}H${x + 2.5}M${x - 2.5} ${y2}H${x + 2.5}`} />
    </>
  );
}

/** A level mark: a leader along the level and the small filled triangle that sits on it. */
function LevelMark({ x, y, length }: { readonly x: number; readonly y: number; readonly length: number }) {
  return (
    <>
      <path className={styles.inkThin} d={`M${x} ${y}H${x + length}`} />
      <path className={styles.levelMark} d={`M${x + 4} ${y}l-3.5 -5h7z`} />
    </>
  );
}

/** Earth hatching under a ground line from `x1` to `x2` at `y`. */
function Earth({ x1, x2, y }: { readonly x1: number; readonly x2: number; readonly y: number }) {
  const strokes: string[] = [];
  for (let x = x1; x + 8 <= x2; x += 10) strokes.push(`M${x} ${y + 8}L${x + 8} ${y}`);
  return <path className={styles.inkThin} d={strokes.join('')} />;
}

const FACADE_ROWS = [58, 94, 130] as const;
const FACADE_COLUMNS = [70, 108, 146, 184, 222, 260] as const;
const FACADE_ENTRANCE = { column: 146, row: 130 } as const;

/** The facade: three storeys of windows, the entrance under its canopy, levels, a dimension. */
function FacadeSheet() {
  return (
    <>
      <SheetBase width={320} height={220} />
      <path className={styles.ground} d="M26 160H304" />
      <Earth x1={28} x2={300} y={160} />
      <path className={styles.ink} d="M56 160V40H290V160" />
      <path className={styles.inkThin} d="M50 40H296M50 35H296M50 35V40M296 35V40" />
      {FACADE_ROWS.flatMap((y) =>
        FACADE_COLUMNS.filter((x) => x !== FACADE_ENTRANCE.column || y !== FACADE_ENTRANCE.row).map((x) => (
          <g key={`${x}-${y}`}>
            <rect className={styles.inkThin} x={x} y={y} width="16" height="22" />
            <path className={styles.inkThin} d={`M${x + 8} ${y}V${y + 22}M${x} ${y + 8}H${x + 16}M${x - 2} ${y + 22}H${x + 18}`} />
          </g>
        )),
      )}
      <rect className={styles.inkThin} x="144" y="128" width="20" height="32" />
      <path className={styles.ink} d="M138 124H170M154 128V160" />
      <path className={styles.axis} d="M56 160V170M290 160V166" />
      <circle className={styles.bubble} cx="56" cy="175" r="5" />
      {[160, 124, 88, 52].map((y) => (
        <LevelMark key={y} x={22} y={y} length={30} />
      ))}
      <path className={styles.inkThin} d="M40 40V160" />
      <path className={styles.ink} d="M37 43L43 37M37 55L43 49M37 91L43 85M37 127L43 121M37 163L43 157" />
    </>
  );
}

/** One stair flight as a run of treads and risers, with the soffit beneath it. */
function flight(x0: number, y0: number, direction: 1 | -1): string {
  const steps = 6;
  const run = 10 * direction;
  const rise = 38 / steps;
  let d = `M${x0} ${y0}`;
  for (let i = 0; i < steps; i += 1) d += `v${-rise}h${run}`;
  return d;
}

/** The section: walls and slabs cut through, three stair flights, windows, axes and levels. */
function SectionSheet() {
  return (
    <>
      <SheetBase width={320} height={220} />
      <path className={styles.axis} d="M70 22V162M250 22V162" />
      <circle className={styles.bubble} cx="70" cy="17" r="5" />
      <circle className={styles.bubble} cx="250" cy="17" r="5" />
      <path className={styles.wall} d="M70 30V154M250 30V154" />
      <WindowV x={70} y1={120} y2={142} />
      <WindowV x={70} y1={82} y2={104} />
      <WindowV x={70} y1={44} y2={66} />
      <WindowV x={250} y1={120} y2={142} />
      <WindowV x={250} y1={82} y2={104} />
      <WindowV x={250} y1={44} y2={66} />
      <path className={styles.slab} d="M66 150H254M66 112H254M66 74H254M66 36H254" />
      <path className={styles.inkThin} d="M66 36V28M254 36V28" />
      <path className={styles.partition} d="M196 36V58M196 74V96M196 112V134" />
      <path className={styles.ink} d={`${flight(100, 150, 1)}${flight(160, 112, -1)}${flight(100, 74, 1)}`} />
      <path className={styles.inkThin} d="M100 154L160 116M160 116L100 78M100 78L160 40" />
      {[150, 112, 74, 36].map((y) => (
        <LevelMark key={y} x={256} y={y} length={34} />
      ))}
      <path className={styles.ground} d="M26 158H66M254 158H304" />
      <Earth x1={28} x2={64} y={158} />
      <path className={styles.inkThin} d="M62 154V168H78V154M242 154V168H258V154" />
    </>
  );
}

/** The plan the plotter draws, without its sheet: axes, walls with windows, doors, a stair, a bathroom, dimensions. */
function PlanLines() {
  return (
    <>
      <path className={styles.axis} d="M56 26V170M150 26V170M226 26V170M300 26V170M44 40H306M44 100H306M44 160H306" />
      {[56, 150, 226, 300].map((x) => (
        <circle key={x} className={styles.bubble} cx={x} cy="20" r="5" />
      ))}
      {[40, 100, 160].map((y) => (
        <circle key={y} className={styles.bubble} cx="38" cy={y} r="5" />
      ))}
      <path className={styles.wall} d="M56 40H300V160H56Z" />
      <WindowH x1={76} x2={120} y={40} />
      <WindowH x1={172} x2={210} y={40} />
      <WindowH x1={248} x2={284} y={40} />
      <WindowH x1={80} x2={124} y={160} />
      <WindowV x={56} y1={64} y2={96} />
      <WindowV x={300} y1={54} y2={84} />
      <rect className={styles.windowGap} x="160" y="156.5" width="20" height="7" />
      <path className={styles.partition} d="M150 40V104M150 124V160M150 100H252M272 100H300M226 100V112M226 130V160" />
      <path className={styles.inkThin} d="M150 124H130M130 124A20 20 0 0 1 150 104M272 100V80M272 80A20 20 0 0 0 252 100M226 112H244M244 112A18 18 0 0 1 226 130M160 160V140M160 140A20 20 0 0 1 180 160" />
      <rect className={styles.inkThin} x="198" y="106" width="22" height="46" />
      <path className={styles.inkThin} d="M198 112H220M198 118H220M198 124H220M198 130H220M198 136H220M198 142H220M198 148H220M209 148V112M206 117L209 111L212 117" />
      <rect className={styles.inkThin} x="274" y="104" width="22" height="40" rx="3" />
      <rect className={styles.inkThin} x="277" y="107" width="16" height="34" rx="6" />
      <rect className={styles.inkThin} x="236" y="150" width="12" height="5" />
      <ellipse className={styles.inkThin} cx="242" cy="143" rx="5" ry="6.5" />
      <rect className={styles.inkThin} x="254" y="147" width="14" height="9" rx="2" />
      <path className={styles.cut} d="M110 26V33M110 167V174" />
      <path className={styles.inkThin} d="M110 26H118M115 23L119 26L115 29M110 174H118M115 171L119 174L115 177" />
      <path className={styles.inkThin} d="M56 163V182M150 163V182M226 163V182M300 163V182M50 178H306" />
      <path className={styles.ink} d="M53 181L59 175M147 181L153 175M223 181L229 175M297 181L303 175" />
    </>
  );
}

/** A CAD selection box on the plan: a translucent fill, a dashed outline and a square grip at each corner. */
function SelectionBox({
  x,
  y,
  width,
  height,
  order,
}: {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly order: string | undefined;
}) {
  const corners = [
    [x, y],
    [x + width, y],
    [x, y + height],
    [x + width, y + height],
  ] as const;
  return (
    <g className={`${styles.selection} ${order ?? ''}`}>
      <rect className={styles.selectionFill} x={x} y={y} width={width} height={height} />
      <rect className={styles.selectionLine} x={x} y={y} width={width} height={height} />
      {corners.map(([cx, cy]) => (
        <rect key={`${cx}-${cy}`} className={styles.selectionGrip} x={cx - 3} y={cy - 3} width="6" height="6" />
      ))}
    </g>
  );
}

/** The product mark, the same three strokes the frame's brand link draws. */
function BrandMark() {
  return (
    <svg viewBox="0 0 36 36" fill="none" focusable="false">
      <path d="M4.5 24.5 12 10.8a4.1 4.1 0 0 1 7.2 0l7.4 13.7" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11.6 24.5 19 10.8a4.1 4.1 0 0 1 7.2 0l5.3 9.8" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8.8 18.3h18.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}
