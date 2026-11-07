'use client';

/**
 * The start form of one АР version, with the choice of analysis where the deployment offers one
 * (`AR-V3-OPT-IN`, design 4.3 and 4.8).
 *
 * **Where there is no choice, this is today's form and nothing else.** The radio is drawn only when the server says, in
 * `getArV3BetaPackStatus`, that a reviewed pack is installed AND `start_allowed` is true (`useArV3StartAllowed`), and the
 * account may take an expert's action. On every other answer -- loading, a failed read, no pack, a pack with starts not
 * allowed, a contract fault -- the markup is `StartRunControl` alone: no radio, no sentence, no link, no word about v3.
 *
 * **Where there is one, the standard analysis is the default every time.** The choice starts at `standard` whenever this
 * component mounts and is held in state only: nothing is stored per person, project or browser, so a remount, a reload
 * or another visit opens on the standard analysis. One start sends exactly one analysis's operation: `startRun` through
 * `StartRunControl` for the standard analysis, `startArV3BetaGroup` through `StartArV3GroupControl` for v3. v3 is its own
 * operation; there is no flag on the default start, no fallback from either to the other and no substitute offered after a
 * refusal. Choosing v3 replaces the standard form, with its executor, preset and group selectors, by the v3 form: the
 * group start takes none, and showing them would promise a choice the server ignores. Changing the choice clears what
 * the form that is left held (its estimate, its consent, its refusal).
 *
 * The caller of the v3 start holds its intent for as long as this component lives, as `useArV3GroupStartIntent` asks: a
 * start in flight keeps its key and its observer, so a status re-read that takes the radio away while the request is on its
 * way neither loses the accepted group nor mints a second key.
 */

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { ArV3BetaGroup, ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { useMayActAsExpert } from '@/entities/account';
import { arV3GroupReviewAddress, looksLikeArV3GroupId, useArV3StartAllowed } from '@/entities/audit-run';
import { AnalysisChoice, StartRunControl } from '@/features/start-run';
import type { AnalysisChoiceValue } from '@/features/start-run';
import { StartArV3GroupControl, useArV3GroupStartIntent } from '@/features/start-ar-v3-group';

/** What the v3 form says about what it starts and what it leaves alone. */
export const AR_V3_CHOICE_SENTENCE =
  'Шесть платных вызовов, по одному на область: шесть отдельных прогонов с нормативными цитатами, без числовых выводов. ' +
  'Это другой анализ, а не замена стандартного: результат стандартного анализа этой версии остаётся как есть.';

export interface AnalysisStartProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading of a standard start, so the screen can move to run progress. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
}

export function AnalysisStart({ projectUid, versionUid, onRunStarted }: AnalysisStartProps) {
  const router = useRouter();
  const mayAct = useMayActAsExpert();
  const allowed = useArV3StartAllowed(true);
  // Held here, for as long as the list is: see the header. Called whether or not the radio is drawn.
  const intent = useArV3GroupStartIntent(versionUid);
  const [analysis, setAnalysis] = useState<AnalysisChoiceValue>('standard');

  const standard = (
    <StartRunControl
      projectUid={projectUid}
      versionUid={versionUid}
      {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
    />
  );
  // The choice is offered while allowed, and kept drawn while a v3 start is on its way even if the status stops saying so.
  const offered = mayAct && (allowed || (analysis === 'ar_v3_beta' && intent.inFlight));
  if (!offered) return standard;

  const choose = (next: AnalysisChoiceValue) => {
    if (next === analysis || intent.inFlight) return;
    // What the form that is left held does not follow the person to the other one.
    intent.mutation.reset();
    intent.cost.reset();
    setAnalysis(next);
  };

  return (
    <div className="am-form" data-analysis-start data-analysis={analysis}>
      <AnalysisChoice value={analysis} disabled={intent.inFlight} onChange={choose} />
      {analysis === 'standard' ? (
        standard
      ) : (
        <>
          <StartArV3GroupControl
            projectUid={projectUid}
            versionUid={versionUid}
            intent={intent}
            onStarted={(group: ArV3BetaGroup) => {
              if (looksLikeArV3GroupId(group.group_id)) router.push(arV3GroupReviewAddress(group.group_id));
            }}
          />
          <p className="am-note" data-ar-v3-choice-note>{AR_V3_CHOICE_SENTENCE}</p>
        </>
      )}
    </div>
  );
}
