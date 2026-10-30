"""Persisted choice of the explicitly separate native-text experiment."""
from sqlalchemy import text
from auditmanager.shared.errors import DomainError, ErrorCode

CLASSIC = "classic"
ENGINE = "v3_native_text_experimental"
ORIGINAL_SHA = "3c99481719218b9cfa7560886529916646c61939"


def validate_engine(value):
    if value not in {CLASSIC, ENGINE}:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="engine", constraint="enum")
    return value


def engine_for_run(session, run_id):
    value = session.execute(text(
        "SELECT c.outcome->>'engine' FROM stage_chain_run r "
        "JOIN command_record c ON c.command_id=r.command_id WHERE r.stage_chain_run_id=:run"
    ), {"run": run_id}).scalar_one_or_none()
    return validate_engine(value or CLASSIC)


def engine_for_batch(session, batch_id):
    value = session.execute(text(
        "SELECT c.outcome->>'engine' FROM stage_chain_batch b "
        "JOIN command_record c ON c.command_id=b.command_id WHERE b.stage_chain_batch_id=:batch"
    ), {"batch": batch_id}).scalar_one_or_none()
    return validate_engine(value or CLASSIC)


def experimental_progress(session, run_id):
    if engine_for_run(session, run_id) != ENGINE:
        return None
    from .policy import policy_for_run
    policy = policy_for_run(session, run_id)
    if policy is None:
        from .procedures import BUNDLE
        bundle = BUNDLE
    else:
        bundle = policy["bundle"]
    rows = session.execute(text(
        "SELECT DISTINCT ON(group_id) group_id,state,progress FROM stage_ai_unit WHERE stage_chain_run_id=:run "
        "AND group_id LIKE 'v3:%' AND progress->>'prompt_bundle_version'=:bundle "
        "ORDER BY group_id,generation DESC,created_at DESC,stage_ai_unit_id DESC"
    ), {"run": run_id, "bundle": bundle}).mappings().all()
    names = {"mapper": "Mapper", "miner": "Miner", "unmatched": "Разбор непарных страниц",
             "dedupe": "Dedupe", "verify": "Проверка параметров"}
    if policy is not None and policy["plan_version"] == "windowed-global-v1": names["consolidate"] = "Consolidator"
    names["final"] = "Карточки V3"
    final = next((r for r in reversed(rows) if r["group_id"] == "v3:final:cards" and r["state"] == "completed"), None)
    mapping = next((r["progress"].get("v3_result") for r in rows
                    if r["group_id"] in {"v3:mapper:all", "v3:mapper:catalogue"} and r["state"] == "completed"), None)
    procedures = []
    for kind, label in names.items():
        selected = [r for r in rows if r["group_id"].split(":")[1] == kind]
        state = ("failed" if any(r["state"] == "failed" for r in selected) else
                 "completed" if selected and all(r["state"] == "completed" for r in selected) else
                 "running" if selected else "completed" if final is not None else "queued")
        if kind == "unmatched" and mapping and not mapping["unmatched_old"] and not mapping["unmatched_new"]:
            state = "completed"
        completed = sum(row["state"] == "completed" for row in selected)
        procedures.append({"name": label, "state": state, "planned": len(selected),
                           "completed": completed, "pending": len(selected) - completed})
    active = next((p["name"] for p in procedures if p["state"] in {"running", "failed"}),
                  next((p["name"] for p in procedures if p["state"] != "completed"), "Карточки V3"))
    return {"engine": ENGINE, "source_version": ORIGINAL_SHA, "procedure": active,
            "plan_version": "native-text-v3/1" if policy is None else policy["plan_version"],
            "limits": {"pages": 16, "characters": 80000, "fragments": 400} if policy is None else policy["limits"],
            "planned_units": sum(row["planned"] for row in procedures),
            "completed_units": sum(row["completed"] for row in procedures),
            "pending_units": sum(row["pending"] for row in procedures),
            "status": ("partial" if final is not None and (not final["progress"].get("coverage", {}).get("complete")
                       or final["progress"].get("coverage", {}).get("global_consolidation", {}).get("not_compared_pairs", 0) > 0) else
                       "completed" if final is not None else "running"),
            "coverage": None if final is None else final["progress"].get("coverage"),
            "source_report": None if final is None else final["progress"].get("source_report"),
            "procedures": procedures, "limitations": [
                "Эксперимент: только собственный текст PDF; графика и распознанные таблицы не проверены.",
                "Результат предварительный, нормы не проверены; решение принимает эксперт.",
                *(["Mapper получает каталог всех страниц с ограниченными выдержками; полный текст разбирается пакетами.",
                   "Для непарных страниц выбор встречных кандидатов ограничен; семантическая полнота не подтверждена.",
                   "Глобальный свод сравнивает ограниченные межпакетные кандидаты; глобальная семантическая полнота не подтверждена."
                   if policy.get("plan_version") == "windowed-global-v1" else
                   "Удаление повторов выполняется внутри пакетов, без утверждения глобальной семантической уникальности."] if policy is not None else [])]}
