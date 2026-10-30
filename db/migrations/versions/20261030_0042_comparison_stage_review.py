"""C4 stage AI, repairs, expert cards and durable batch/run scope (CMP-SEAL-C4)."""
from __future__ import annotations

from collections.abc import Sequence
from alembic import op
from sqlalchemy import text

revision: str = "0042_comparison_stage_review"
down_revision: str | None = "0041_comparison_stage_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
SHA = "^[0-9a-f]{64}$"
SYSTEMS = ("unknown","architecture","structural","electrical","heating_ventilation","water_sewage",
           "fire_protection","low_current","technology","site","other")
CATEGORIES = ("areas","floors","electrical_load","calculation_method","consumer_composition","room_composition",
              "dimensions","materials","equipment_parameters","system_configuration","fire_safety",
              "designation_rename","administrative","documentation_structure","formatting","other_project",
              "other_service","uncertain")
TABLES = ("stage_ai_unit","stage_ai_review","stage_ai_classification","stage_ai_synthesis",
          "stage_graphic_evidence","stage_link_repair","stage_link_repair_event","stage_change_card",
          "stage_card_evidence","stage_card_verdict","stage_chain_batch","stage_chain_batch_item")
IMMUTABLE = ("stage_ai_review","stage_ai_classification","stage_ai_synthesis","stage_graphic_evidence",
             "stage_link_repair","stage_link_repair_event","stage_change_card","stage_card_evidence","stage_card_verdict")
KINDS_BEFORE = ("text_analysis","comparison_pair_check","comparison_sheet_changes","comparison_spec","comparison_report")
METHODS_BEFORE = ("pair_check","sheet_changes","spec","report")


def _list(values: Sequence[str]) -> str:
    return ", ".join("'" + value + "'" for value in values)


def _table(name: str, prefix: str, columns: str, *, run: bool = True, extra: str = "") -> None:
    scope = """stage_chain_run_id text NOT NULL REFERENCES stage_chain_run(stage_chain_run_id) ON DELETE RESTRICT,""" if run else ""
    op.execute(f"""CREATE TABLE {name} (
        {name}_id text PRIMARY KEY CHECK ({name}_id ~ '^{prefix}_{ULID}$'),
        {scope}
        {columns},
        created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        {extra}
    )""")
    if run:
        op.execute(f"CREATE INDEX ix_{name}_run ON {name}(stage_chain_run_id)")


def _text_scope(reverse: bool) -> None:
    left_expr = "CASE WHEN TG_TABLE_NAME = 'stage_text_hint' AND to_jsonb(NEW)->>'source_side' = 'right' THEN 'right' ELSE 'left' END" if reverse else "'left'"
    right_expr = "CASE WHEN TG_TABLE_NAME = 'stage_text_hint' AND to_jsonb(NEW)->>'source_side' = 'right' THEN 'left' ELSE 'right' END" if reverse else "'right'"
    op.execute(f"""CREATE OR REPLACE FUNCTION am_check_stage_text_evidence_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE left_id text; right_id text; actual_side text;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM stage_link_revision r WHERE r.stage_link_revision_id = NEW.stage_link_revision_id
                           AND r.stage_pair_id = NEW.stage_pair_id) THEN
                RAISE EXCEPTION 'stage_text_revision_scope_mismatch' USING ERRCODE='AM001';
            END IF;
            left_id := coalesce(to_jsonb(NEW)->>'left_fragment_id',to_jsonb(NEW)->>'source_fragment_id');
            right_id := coalesce(to_jsonb(NEW)->>'right_fragment_id',to_jsonb(NEW)->>'target_fragment_id');
            IF left_id IS NOT NULL THEN
                SELECT side INTO actual_side FROM stage_text_fragment WHERE stage_text_fragment_id=left_id
                    AND stage_pair_id=NEW.stage_pair_id;
                IF actual_side IS DISTINCT FROM ({left_expr}) THEN
                    RAISE EXCEPTION 'stage_text_left_fragment_scope_mismatch' USING ERRCODE='AM001';
                END IF;
            END IF;
            IF right_id IS NOT NULL THEN
                SELECT side INTO actual_side FROM stage_text_fragment WHERE stage_text_fragment_id=right_id
                    AND stage_pair_id=NEW.stage_pair_id;
                IF actual_side IS DISTINCT FROM ({right_expr}) THEN
                    RAISE EXCEPTION 'stage_text_right_fragment_scope_mismatch' USING ERRCODE='AM001';
                END IF;
            END IF;
            RETURN NEW;
        END $fn$""")


def upgrade() -> None:
    _table("stage_chain_batch","scb", """
        project_uid text NOT NULL REFERENCES project(project_uid) ON DELETE RESTRICT,
        state text NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','running','paused','completed','failed','cancelled')),
        with_ai boolean NOT NULL DEFAULT true,
        actor_user_uid text NOT NULL REFERENCES app_user(user_uid) ON DELETE RESTRICT CHECK(actor_user_uid ~ '^usr_[0-9A-HJKMNP-TV-Z]{26}$'),
        command_id text NOT NULL UNIQUE REFERENCES command_record(command_id) ON DELETE RESTRICT,
        updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
    """,run=False)
    _table("stage_chain_batch_item","scbi", """
        stage_chain_batch_id text NOT NULL REFERENCES stage_chain_batch(stage_chain_batch_id) ON DELETE RESTRICT,
        stage_pair_id text NOT NULL REFERENCES stage_pair(stage_pair_id) ON DELETE RESTRICT,
        stage_link_revision_id text NOT NULL REFERENCES stage_link_revision(stage_link_revision_id) ON DELETE RESTRICT,
        position integer NOT NULL CHECK(position >= 1),
        state text NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','running','completed','failed','cancelled')),
        stage_chain_run_id text NULL REFERENCES stage_chain_run(stage_chain_run_id) ON DELETE RESTRICT,
        consent jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(consent)='object'),
        updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(stage_chain_batch_id,position),
        UNIQUE(stage_chain_batch_id,stage_pair_id)
    """,run=False)
    op.execute("""ALTER TABLE stage_chain_run
        ADD COLUMN kind text NOT NULL DEFAULT 'deterministic' CHECK(kind IN ('deterministic','full')),
        ADD COLUMN with_ai boolean NOT NULL DEFAULT false,
        ADD COLUMN effective_link_revision_id text NULL REFERENCES stage_link_revision(stage_link_revision_id) ON DELETE RESTRICT,
        ADD COLUMN comparison_ai_job_id text NULL REFERENCES comparison_ai_job(comparison_ai_job_id) ON DELETE RESTRICT,
        ADD COLUMN stage_chain_batch_id text NULL REFERENCES stage_chain_batch(stage_chain_batch_id) ON DELETE RESTRICT,
        ADD COLUMN pause_reason text NULL,
        ADD COLUMN repair_cycle_count integer NOT NULL DEFAULT 0 CHECK(repair_cycle_count BETWEEN 0 AND 1)""")
    op.execute("CREATE TRIGGER trg_stage_chain_c4_pins BEFORE UPDATE ON stage_chain_run FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('kind','with_ai','stage_chain_batch_id')")
    op.execute("""CREATE FUNCTION am_check_stage_effective_revision() RETURNS trigger LANGUAGE plpgsql AS $fn$
        BEGIN
          IF NEW.effective_link_revision_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM stage_link_revision r WHERE r.stage_link_revision_id=NEW.effective_link_revision_id AND r.stage_pair_id=NEW.stage_pair_id
          ) THEN RAISE EXCEPTION 'stage_effective_revision_scope_mismatch' USING ERRCODE='AM001'; END IF;
          RETURN NEW;
        END $fn$""")
    op.execute("CREATE TRIGGER trg_stage_effective_revision BEFORE INSERT OR UPDATE ON stage_chain_run FOR EACH ROW EXECUTE FUNCTION am_check_stage_effective_revision()")
    op.execute("ALTER TABLE comparison_ai_job ADD COLUMN stage_chain_run_id text NULL REFERENCES stage_chain_run(stage_chain_run_id) ON DELETE RESTRICT")
    op.execute("ALTER TABLE comparison_ai_job DROP CONSTRAINT ck_comparison_ai_job_method")
    op.execute("ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_method CHECK(method IN ('pair_check','sheet_changes','spec','report','stage_review'))")
    op.execute("ALTER TABLE comparison_ai_job DROP CONSTRAINT ck_comparison_ai_job_scope")
    op.execute("""ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_scope CHECK (
        (method='stage_review' AND stage_chain_run_id IS NOT NULL AND comparison_matrix_id IS NULL
         AND comparison_series_id IS NULL AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL)
        OR (stage_chain_run_id IS NULL AND (
          (method='pair_check' AND comparison_matrix_id IS NOT NULL AND comparison_series_id IS NULL AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL)
          OR (method='sheet_changes' AND comparison_matrix_id IS NULL AND comparison_transition_id IS NULL AND ((comparison_series_id IS NOT NULL) <> (comparison_sheet_pair_id IS NOT NULL)))
          OR (method='spec' AND comparison_transition_id IS NOT NULL AND comparison_matrix_id IS NULL AND comparison_series_id IS NULL AND comparison_sheet_pair_id IS NULL)
          OR (method='report' AND comparison_series_id IS NOT NULL AND comparison_matrix_id IS NULL AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL))))""")
    op.execute("CREATE UNIQUE INDEX uq_comparison_ai_job_live_stage ON comparison_ai_job(stage_chain_run_id) WHERE method='stage_review' AND state IN ('queued','running','paused')")
    op.execute("""CREATE FUNCTION am_check_stage_ai_job_scope() RETURNS trigger LANGUAGE plpgsql AS $fn$
        BEGIN
          IF NEW.method='stage_review' AND NOT EXISTS (
            SELECT 1 FROM stage_chain_run r JOIN stage_pair p ON p.stage_pair_id=r.stage_pair_id
            WHERE r.stage_chain_run_id=NEW.stage_chain_run_id AND p.project_uid=NEW.project_uid AND p.left_document_uid=NEW.document_uid
          ) THEN RAISE EXCEPTION 'stage_ai_job_scope_mismatch' USING ERRCODE='AM001'; END IF;
          RETURN NEW;
        END $fn$""")
    op.execute("CREATE TRIGGER trg_stage_ai_job_scope BEFORE INSERT OR UPDATE ON comparison_ai_job FOR EACH ROW EXECUTE FUNCTION am_check_stage_ai_job_scope()")
    op.execute("CREATE TRIGGER trg_stage_ai_job_pin BEFORE UPDATE ON comparison_ai_job FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('stage_chain_run_id')")
    op.execute("ALTER TABLE executor_route_event DROP CONSTRAINT ck_executor_route_work_kind")
    op.execute(f"ALTER TABLE executor_route_event ADD CONSTRAINT ck_executor_route_work_kind CHECK(work_kind IN ({_list(KINDS_BEFORE + ('comparison_stage_review',))}))")

    _table("stage_ai_unit","saunit",f"""
        comparison_ai_job_id text NULL REFERENCES comparison_ai_job(comparison_ai_job_id) ON DELETE RESTRICT,
        kind text NOT NULL CHECK(kind IN ('review','classify','synthesize')),
        group_id text NOT NULL CHECK(char_length(group_id) BETWEEN 1 AND 128),
        source_sha256 text NOT NULL CHECK(source_sha256 ~ '{SHA}'),
        state text NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','running','completed','failed','cancelled')),
        payload jsonb NOT NULL DEFAULT '{{}}'::jsonb CHECK(jsonb_typeof(payload)='object'),
        failure_reason text NULL,
        updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(stage_chain_run_id,kind,group_id,source_sha256),
        UNIQUE(stage_ai_unit_id,stage_chain_run_id)
    """)
    for name,prefix,data in (
        ("stage_ai_review","sarev","decisions jsonb NOT NULL CHECK(jsonb_typeof(decisions)='array' AND jsonb_array_length(decisions)<=800)"),
        ("stage_ai_classification","sacls","cards jsonb NOT NULL CHECK(jsonb_typeof(cards)='array')"),
        ("stage_ai_synthesis","sasyn","result jsonb NOT NULL CHECK(jsonb_typeof(result)='object')"),
    ):
        _table(name,prefix,f"""
            stage_ai_unit_id text NOT NULL,
            content_key text NOT NULL CHECK(content_key ~ '{SHA}'),
            group_id text NOT NULL CHECK(char_length(group_id) BETWEEN 1 AND 128),
            source_sha256 text NOT NULL CHECK(source_sha256 ~ '{SHA}'),
            {data},
            model_identity jsonb NOT NULL DEFAULT '{{}}'::jsonb CHECK(jsonb_typeof(model_identity)='object'),
            UNIQUE(stage_chain_run_id,content_key),
            UNIQUE({name}_id,stage_chain_run_id),
            FOREIGN KEY(stage_ai_unit_id,stage_chain_run_id) REFERENCES stage_ai_unit(stage_ai_unit_id,stage_chain_run_id) ON DELETE RESTRICT
        """)
    _table("stage_graphic_evidence","sge",f"""
        stage_link_item_id text NOT NULL REFERENCES stage_link_item(stage_link_item_id) ON DELETE RESTRICT,
        left_profile_id text NULL REFERENCES comparison_page_profile(comparison_page_profile_id) ON DELETE RESTRICT,
        right_profile_id text NULL REFERENCES comparison_page_profile(comparison_page_profile_id) ON DELETE RESTRICT,
        comparison_sheet_pair_result_id text NULL REFERENCES comparison_sheet_pair_result(comparison_sheet_pair_result_id) ON DELETE RESTRICT,
        status text NOT NULL CHECK(status IN ('not_checked','unreliable','reliable')),
        reason text NOT NULL,
        regions jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(regions)='array'),
        content_key text NOT NULL CHECK(content_key ~ '{SHA}'),
        CHECK(status<>'reliable' OR (left_profile_id IS NOT NULL AND right_profile_id IS NOT NULL AND comparison_sheet_pair_result_id IS NOT NULL)),
        UNIQUE(stage_chain_run_id,content_key)
    """)
    _table("stage_link_repair","crp",f"""
        before_revision_id text NOT NULL REFERENCES stage_link_revision(stage_link_revision_id) ON DELETE RESTRICT,
        after_revision_id text NOT NULL REFERENCES stage_link_revision(stage_link_revision_id) ON DELETE RESTRICT,
        proof jsonb NOT NULL CHECK(jsonb_typeof(proof)='object'),
        before_snapshot jsonb NOT NULL CHECK(jsonb_typeof(before_snapshot)='array'),
        after_snapshot jsonb NOT NULL CHECK(jsonb_typeof(after_snapshot)='array'),
        content_key text NOT NULL CHECK(content_key ~ '{SHA}'),
        UNIQUE(stage_chain_run_id),
        UNIQUE(stage_link_repair_id,stage_chain_run_id)
    """)
    _table("stage_link_repair_event","crpe", """
        stage_link_repair_id text NOT NULL REFERENCES stage_link_repair(stage_link_repair_id) ON DELETE RESTRICT,
        action text NOT NULL CHECK(action IN ('applied','undone','superseded')),
        actor_user_uid text NOT NULL REFERENCES app_user(user_uid) ON DELETE RESTRICT,
        command_id text NOT NULL REFERENCES command_record(command_id) ON DELETE RESTRICT,
        revision_id text NOT NULL REFERENCES stage_link_revision(stage_link_revision_id) ON DELETE RESTRICT,
        recompute_run_id text NULL REFERENCES stage_chain_run(stage_chain_run_id) ON DELETE RESTRICT,
        UNIQUE(stage_link_repair_id,command_id)
    """,run=False)
    _table("stage_change_card","ccd",f"""
        stage_ai_classification_id text NULL REFERENCES stage_ai_classification(stage_ai_classification_id) ON DELETE RESTRICT,
        card_key text NOT NULL CHECK(card_key ~ '{SHA}'),
        evidence_digest text NOT NULL CHECK(evidence_digest ~ '{SHA}'),
        class_name text NOT NULL CHECK(class_name IN ('PROJECT_CHANGE','SERVICE_STRUCTURE','REVIEW')),
        category text NOT NULL CHECK(category IN ({_list(CATEGORIES)})),
        title text NOT NULL CHECK(char_length(title) BETWEEN 1 AND 260),
        system text NOT NULL CHECK(system IN ({_list(SYSTEMS)})),
        evidence_ids jsonb NOT NULL CHECK(jsonb_typeof(evidence_ids)='array' AND jsonb_array_length(evidence_ids)>0),
        before_text text NOT NULL DEFAULT '',
        after_text text NOT NULL DEFAULT '',
        UNIQUE(stage_chain_run_id,card_key),
        UNIQUE(stage_change_card_id,stage_chain_run_id)
    """)
    _table("stage_card_evidence","sce", """
        stage_change_card_id text NOT NULL,
        kind text NOT NULL CHECK(kind IN ('TEXT','TABLE','GRAPHIC')),
        source_fragment_id text NULL REFERENCES stage_text_fragment(stage_text_fragment_id) ON DELETE RESTRICT,
        source_difference_id text NULL REFERENCES stage_text_difference(stage_text_difference_id) ON DELETE RESTRICT,
        source_graphic_evidence_id text NULL REFERENCES stage_graphic_evidence(stage_graphic_evidence_id) ON DELETE RESTRICT,
        side text NOT NULL CHECK(side IN ('left','right','both')),
        page_profile_id text NULL REFERENCES comparison_page_profile(comparison_page_profile_id) ON DELETE RESTRICT,
        box_anchor jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(box_anchor)='object'),
        absence_proven boolean NOT NULL DEFAULT false,
        CHECK(num_nonnulls(source_fragment_id,source_difference_id,source_graphic_evidence_id)=1),
        FOREIGN KEY(stage_change_card_id,stage_chain_run_id) REFERENCES stage_change_card(stage_change_card_id,stage_chain_run_id) ON DELETE RESTRICT
    """)
    _table("stage_card_verdict","cdv",f"""
        stage_change_card_id text NOT NULL REFERENCES stage_change_card(stage_change_card_id) ON DELETE RESTRICT,
        revision_no integer NOT NULL CHECK(revision_no>=1),
        decision text NOT NULL CHECK(decision IN ('accepted','rejected')),
        reason text NOT NULL DEFAULT '' CHECK(char_length(reason)<=2000 AND (decision<>'rejected' OR char_length(btrim(reason))>0)),
        evidence_digest text NOT NULL CHECK(evidence_digest ~ '{SHA}'),
        actor_user_uid text NOT NULL REFERENCES app_user(user_uid) ON DELETE RESTRICT,
        command_id text NOT NULL REFERENCES command_record(command_id) ON DELETE RESTRICT,
        carried_from_verdict_id text NULL REFERENCES stage_card_verdict(stage_card_verdict_id) ON DELETE RESTRICT,
        UNIQUE(stage_change_card_id,revision_no),
        UNIQUE(stage_change_card_id,command_id)
    """,run=False)
    op.execute("""CREATE FUNCTION am_check_stage_c4_scope() RETURNS trigger LANGUAGE plpgsql AS $fn$
      DECLARE j jsonb := to_jsonb(NEW); pair_id text; revision_id text; card_class text; expected_digest text; latest_no integer;
      BEGIN
        IF TG_TABLE_NAME='stage_ai_unit' AND j->>'comparison_ai_job_id' IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM comparison_ai_job a WHERE a.comparison_ai_job_id=j->>'comparison_ai_job_id' AND a.stage_chain_run_id=j->>'stage_chain_run_id'
        ) THEN RAISE EXCEPTION 'stage_ai_unit_scope_mismatch' USING ERRCODE='AM001'; END IF;
        IF TG_TABLE_NAME IN ('stage_graphic_evidence','stage_link_repair','stage_card_evidence','stage_change_card') THEN
          SELECT r.stage_pair_id,coalesce(r.effective_link_revision_id,r.stage_link_revision_id) INTO pair_id,revision_id
            FROM stage_chain_run r WHERE r.stage_chain_run_id=j->>'stage_chain_run_id';
          IF TG_TABLE_NAME='stage_graphic_evidence' AND NOT EXISTS (
            SELECT 1 FROM stage_link_item i WHERE i.stage_link_item_id=j->>'stage_link_item_id' AND i.stage_link_revision_id=revision_id
              AND i.left_profile_id IS NOT DISTINCT FROM j->>'left_profile_id' AND i.right_profile_id IS NOT DISTINCT FROM j->>'right_profile_id'
          ) THEN RAISE EXCEPTION 'stage_graphic_scope_mismatch' USING ERRCODE='AM001'; END IF;
          IF TG_TABLE_NAME='stage_graphic_evidence' AND j->>'status'='reliable' AND (
            (SELECT count(*) FROM stage_link_item i WHERE i.stage_link_revision_id=revision_id AND i.left_profile_id=j->>'left_profile_id')<>1
            OR (SELECT count(*) FROM stage_link_item i WHERE i.stage_link_revision_id=revision_id AND i.right_profile_id=j->>'right_profile_id')<>1
          ) THEN RAISE EXCEPTION 'stage_graphic_many_to_many_unchecked' USING ERRCODE='AM001'; END IF;
          IF TG_TABLE_NAME='stage_link_repair' AND (
            NOT EXISTS (SELECT 1 FROM stage_link_revision r WHERE r.stage_link_revision_id=j->>'before_revision_id' AND r.stage_pair_id=pair_id)
            OR NOT EXISTS (SELECT 1 FROM stage_link_revision r WHERE r.stage_link_revision_id=j->>'after_revision_id' AND r.stage_pair_id=pair_id)
          ) THEN RAISE EXCEPTION 'stage_repair_scope_mismatch' USING ERRCODE='AM001'; END IF;
          IF TG_TABLE_NAME='stage_change_card' AND j->>'stage_ai_classification_id' IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM stage_ai_classification c WHERE c.stage_ai_classification_id=j->>'stage_ai_classification_id' AND c.stage_chain_run_id=j->>'stage_chain_run_id'
          ) THEN RAISE EXCEPTION 'stage_card_classification_scope_mismatch' USING ERRCODE='AM001'; END IF;
          IF TG_TABLE_NAME='stage_card_evidence' THEN
            IF j->>'source_fragment_id' IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stage_text_fragment f WHERE f.stage_text_fragment_id=j->>'source_fragment_id' AND f.stage_pair_id=pair_id)
              OR j->>'source_difference_id' IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stage_text_difference d WHERE d.stage_text_difference_id=j->>'source_difference_id' AND d.stage_link_revision_id=revision_id)
              OR j->>'source_graphic_evidence_id' IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stage_graphic_evidence g WHERE g.stage_graphic_evidence_id=j->>'source_graphic_evidence_id' AND g.stage_chain_run_id=j->>'stage_chain_run_id')
            THEN RAISE EXCEPTION 'stage_card_evidence_scope_mismatch' USING ERRCODE='AM001'; END IF;
          END IF;
        END IF;
        IF TG_TABLE_NAME='stage_card_verdict' THEN
          PERFORM pg_advisory_xact_lock(hashtextextended('stage_verdict:'||(j->>'stage_change_card_id'),0));
          SELECT c.class_name,c.evidence_digest INTO card_class,expected_digest FROM stage_change_card c WHERE c.stage_change_card_id=j->>'stage_change_card_id';
          SELECT coalesce(max(v.revision_no),0) INTO latest_no FROM stage_card_verdict v WHERE v.stage_change_card_id=j->>'stage_change_card_id';
          IF card_class='SERVICE_STRUCTURE' OR expected_digest IS DISTINCT FROM j->>'evidence_digest' OR (j->>'revision_no')::integer<>latest_no+1 THEN
            RAISE EXCEPTION 'stage_card_verdict_revision_invalid' USING ERRCODE='AM001';
          END IF;
        END IF;
        IF TG_TABLE_NAME='stage_link_repair_event' AND NOT EXISTS (
          SELECT 1 FROM stage_link_repair x JOIN stage_chain_run r ON r.stage_chain_run_id=x.stage_chain_run_id
            JOIN stage_link_revision v ON v.stage_pair_id=r.stage_pair_id
          WHERE x.stage_link_repair_id=j->>'stage_link_repair_id' AND v.stage_link_revision_id=j->>'revision_id'
            AND (j->>'recompute_run_id' IS NULL OR EXISTS (SELECT 1 FROM stage_chain_run n WHERE n.stage_chain_run_id=j->>'recompute_run_id' AND n.stage_pair_id=r.stage_pair_id))
        ) THEN RAISE EXCEPTION 'stage_repair_event_scope_mismatch' USING ERRCODE='AM001'; END IF;
        IF TG_TABLE_NAME='stage_chain_batch_item' AND NOT EXISTS (
          SELECT 1 FROM stage_chain_batch b JOIN stage_pair p ON p.project_uid=b.project_uid JOIN stage_link_revision r ON r.stage_pair_id=p.stage_pair_id
          WHERE b.stage_chain_batch_id=j->>'stage_chain_batch_id' AND p.stage_pair_id=j->>'stage_pair_id' AND r.stage_link_revision_id=j->>'stage_link_revision_id'
            AND (j->>'stage_chain_run_id' IS NULL OR EXISTS (SELECT 1 FROM stage_chain_run run WHERE run.stage_chain_run_id=j->>'stage_chain_run_id' AND run.stage_pair_id=p.stage_pair_id AND run.stage_link_revision_id=r.stage_link_revision_id))
        ) THEN RAISE EXCEPTION 'stage_batch_scope_mismatch' USING ERRCODE='AM001'; END IF;
        RETURN NEW;
      END $fn$""")
    for table in ("stage_ai_unit","stage_graphic_evidence","stage_link_repair","stage_change_card","stage_card_evidence","stage_card_verdict","stage_chain_batch_item","stage_link_repair_event"):
        op.execute(f"CREATE TRIGGER trg_{table}_scope BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION am_check_stage_c4_scope()")
    for table in IMMUTABLE:
        op.execute(f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION am_immutable_row()")
    for table,columns in {
        "stage_ai_unit": ("stage_ai_unit_id","stage_chain_run_id","comparison_ai_job_id","kind","group_id","source_sha256","payload","created_at"),
        "stage_chain_batch": ("stage_chain_batch_id","project_uid","with_ai","actor_user_uid","command_id","created_at"),
        "stage_chain_batch_item": ("stage_chain_batch_item_id","stage_chain_batch_id","stage_pair_id","stage_link_revision_id","position","consent","created_at"),
    }.items():
        op.execute(f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({_list(columns)})")
    op.execute("ALTER TABLE stage_text_hint ADD COLUMN source_side text NOT NULL DEFAULT 'left' CHECK(source_side IN ('left','right'))")
    _text_scope(True)


def downgrade() -> None:
    connection=op.get_bind()
    for table in TABLES:
        if connection.execute(text(f"SELECT EXISTS(SELECT 1 FROM {table})")).scalar():
            raise RuntimeError("0042 populated comparison stage review refuses downgrade")
    if connection.execute(text("SELECT EXISTS(SELECT 1 FROM comparison_ai_job WHERE method='stage_review') OR EXISTS(SELECT 1 FROM executor_route_event WHERE work_kind='comparison_stage_review') OR EXISTS(SELECT 1 FROM stage_text_hint WHERE source_side='right') OR EXISTS(SELECT 1 FROM stage_chain_run WHERE kind='full' OR with_ai OR effective_link_revision_id IS NOT NULL OR stage_chain_batch_id IS NOT NULL OR repair_cycle_count<>0)")).scalar():
        raise RuntimeError("0042 referenced stage review scope refuses downgrade")
    _text_scope(False)
    op.execute("ALTER TABLE stage_text_hint DROP COLUMN source_side")
    op.execute("DROP TRIGGER trg_stage_ai_job_pin ON comparison_ai_job")
    op.execute("DROP TRIGGER trg_stage_ai_job_scope ON comparison_ai_job")
    op.execute("DROP FUNCTION am_check_stage_ai_job_scope()")
    op.execute("DROP INDEX uq_comparison_ai_job_live_stage")
    op.execute("ALTER TABLE comparison_ai_job DROP CONSTRAINT ck_comparison_ai_job_scope")
    op.execute("ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_scope CHECK (stage_chain_run_id IS NULL)")
    op.execute("ALTER TABLE comparison_ai_job DROP CONSTRAINT ck_comparison_ai_job_method")
    op.execute(f"ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_method CHECK(method IN ({_list(METHODS_BEFORE)}))")
    op.execute("ALTER TABLE executor_route_event DROP CONSTRAINT ck_executor_route_work_kind")
    op.execute(f"ALTER TABLE executor_route_event ADD CONSTRAINT ck_executor_route_work_kind CHECK(work_kind IN ({_list(KINDS_BEFORE)}))")
    op.execute("DROP TRIGGER trg_stage_chain_c4_pins ON stage_chain_run")
    op.execute("DROP TRIGGER trg_stage_effective_revision ON stage_chain_run")
    op.execute("DROP FUNCTION am_check_stage_effective_revision()")
    op.execute("ALTER TABLE stage_chain_run DROP COLUMN comparison_ai_job_id, DROP COLUMN effective_link_revision_id, DROP COLUMN stage_chain_batch_id, DROP COLUMN kind, DROP COLUMN with_ai, DROP COLUMN pause_reason, DROP COLUMN repair_cycle_count")
    op.execute("ALTER TABLE comparison_ai_job DROP COLUMN stage_chain_run_id CASCADE")
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table} CASCADE")
    op.execute("DROP FUNCTION am_check_stage_c4_scope()")
    # Restore the exact C2 method scope shape after the C4 column is gone.
    op.execute("ALTER TABLE comparison_ai_job DROP CONSTRAINT IF EXISTS ck_comparison_ai_job_scope")
    op.execute("""ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_scope CHECK (
      (method='pair_check' AND comparison_matrix_id IS NOT NULL AND comparison_series_id IS NULL AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL)
      OR (method='sheet_changes' AND comparison_matrix_id IS NULL AND comparison_transition_id IS NULL AND ((comparison_series_id IS NOT NULL) <> (comparison_sheet_pair_id IS NOT NULL)))
      OR (method='spec' AND comparison_transition_id IS NOT NULL AND comparison_matrix_id IS NULL AND comparison_series_id IS NULL AND comparison_sheet_pair_id IS NULL)
      OR (method='report' AND comparison_series_id IS NOT NULL AND comparison_matrix_id IS NULL AND comparison_transition_id IS NULL AND comparison_sheet_pair_id IS NULL))""")
