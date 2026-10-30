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
    rows = session.execute(text(
        "SELECT DISTINCT ON(group_id) group_id,state,progress FROM stage_ai_unit WHERE stage_chain_run_id=:run "
        "AND group_id LIKE 'v3:%' ORDER BY group_id,generation DESC,created_at DESC,stage_ai_unit_id DESC"
    ), {"run": run_id}).mappings().all()
    names = {"mapper": "Mapper", "miner": "Miner", "unmatched": "Разбор непарных страниц",
             "dedupe": "Dedupe", "verify": "Проверка параметров", "final": "Карточки V3"}
    final = next((r for r in reversed(rows) if r["group_id"] == "v3:final:cards" and r["state"] == "completed"), None)
    mapping = next((r["progress"].get("v3_result") for r in rows
                    if r["group_id"] == "v3:mapper:all" and r["state"] == "completed"), None)
    procedures = []
    for kind, label in names.items():
        selected = [r for r in rows if r["group_id"].split(":")[1] == kind]
        state = ("failed" if any(r["state"] == "failed" for r in selected) else
                 "completed" if selected and all(r["state"] == "completed" for r in selected) else
                 "running" if selected else "completed" if final is not None else "queued")
        if kind == "unmatched" and mapping and not mapping["unmatched_old"] and not mapping["unmatched_new"]:
            state = "completed"
        procedures.append({"name": label, "state": state})
    active = next((p["name"] for p in procedures if p["state"] in {"running", "failed"}),
                  next((p["name"] for p in procedures if p["state"] != "completed"), "Карточки V3"))
    return {"engine": ENGINE, "source_version": ORIGINAL_SHA, "procedure": active,
            "status": ("partial" if final is not None and not final["progress"].get("coverage", {}).get("complete") else
                       "completed" if final is not None else "running"),
            "coverage": None if final is None else final["progress"].get("coverage"),
            "procedures": procedures, "limitations": [
                "Эксперимент: только собственный текст PDF; графика и распознанные таблицы не проверены.",
                "Результат предварительный, нормы не проверены; решение принимает эксперт."]}
