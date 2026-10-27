/**
 * Frozen F1.3 source-disposition preview. No run, citation or verdict is created here.
 *
 * The words that say a topic is provisional and needs the expert are behind
 * `SHOW_REVIEW_INDICATION` (`R-146ba`): off for the beta, on restores them as they were.
 */

import { SHOW_REVIEW_INDICATION } from '@/shared/config';

import policy from './beta_sources.json';
import groups from './scope_groups.json';
import titles from './topic_titles.json';
import styles from './ar-v3-beta-status.module.css';

type Item = (typeof policy.items)[number];
const byId = new Map<string, Item>(policy.items.map((item) => [item.id, item]));
const topicTitles: Record<string, string> = titles;
const scopedIds = groups.flatMap((group) => group.items);
if (
  policy.policy_version !== 'ar-beta-source-policy-v1'
  || policy.scenario !== 'new_multi_apartment_residential_F1.3'
  || policy.numeric_output_policy !== 'expert_review_required'
  || policy.composition_sha256 !== '79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781'
  || groups.map((group) => group.id).join(',') !== 'F1,F2,A1,A2,S1,S2'
  || policy.items.length !== 22
  || policy.items.some((item) => item.mode !== 'provisional_citation' && item.mode !== 'context_only')
  || byId.size !== policy.items.length
  || scopedIds.length !== policy.items.length
  || new Set(scopedIds).size !== scopedIds.length
  || scopedIds.some((id) => !byId.has(id) || !topicTitles[id])
) {
  throw new Error('AR v3 beta source policy and scope mirror differ');
}

function status(item: Item): string {
  if (SHOW_REVIEW_INDICATION) {
    return item.mode === 'provisional_citation'
      ? 'Предварительная ссылка — требуется проверка эксперта'
      : 'Только контекст — требуется проверка эксперта';
  }
  return item.mode === 'provisional_citation' ? 'Ссылка на норму' : 'Только контекст';
}

export function ArV3BetaStatus() {
  const provisional = policy.items.filter((item) => item.mode === 'provisional_citation').length;
  const contextOnly = policy.items.length - provisional;
  return (
    <section className={styles.panel} aria-labelledby="ar-v3-beta-title" data-ar-v3-beta-status>
      <h2 id="ar-v3-beta-title">{SHOW_REVIEW_INDICATION ? 'АР v3: предварительная карта норм' : 'АР v3: карта норм'}</h2>
      <p className="am-note">
        Сценарий: новый многоквартирный жилой дом Ф1.3. Карта показывает темы и доступность
        источников для будущей проверки. Она не запускает прогон v3, не подтверждает редакцию
        нормы и не выдаёт числовые выводы.
      </p>
      <p data-ar-v3-beta-counts>
        {SHOW_REVIEW_INDICATION ? (
          <>Тем: {policy.items.length}; предварительные ссылки: {provisional}; только контекст: {contextOnly}. Все пункты требуют проверки эксперта.</>
        ) : (
          <>Тем: {policy.items.length}; ссылки на нормы: {provisional}; только контекст: {contextOnly}.</>
        )}
      </p>
      <div className={styles.groups}>
        {groups.map((group) => (
          <details key={group.id} className={styles.group} data-ar-v3-scope={group.id}>
            <summary>{group.id} — {group.title} ({group.items.length})</summary>
            <ul className={styles.items}>
              {group.items.map((id) => {
                const item = byId.get(id);
                if (item === undefined) throw new Error(`Missing AR v3 beta item ${id}`);
                return (
                  <li key={id} data-ar-v3-item={id} data-ar-v3-mode={item.mode}>
                    <strong>{id} — {topicTitles[id]}</strong>
                    <span>{status(item)}</span>
                    <small>Источники: {item.sources.join(', ')}</small>
                  </li>
                );
              })}
            </ul>
          </details>
        ))}
      </div>
    </section>
  );
}
