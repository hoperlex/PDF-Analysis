"""Preserve frozen stage AI units across explicitly consented job generations."""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import Column, Integer, text

revision: str = '0043_stage_ai_generations'
down_revision: str | None = '0042_comparison_stage_review'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    original = bind.execute(text("""
        SELECT c.conname FROM pg_constraint c
        WHERE c.conrelid='stage_ai_unit'::regclass AND c.contype='u'
          AND (SELECT array_agg(a.attname::text ORDER BY k.ordinality)
               FROM unnest(c.conkey) WITH ORDINALITY k(attnum,ordinality)
               JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum)
              = ARRAY['stage_chain_run_id','kind','group_id','source_sha256']::text[]
    """)).scalar_one()
    op.add_column('stage_ai_unit', Column('generation', Integer(), nullable=False, server_default='0'))
    op.create_check_constraint('ck_stage_ai_unit_generation', 'stage_ai_unit', 'generation >= 0')
    op.drop_constraint(original, 'stage_ai_unit', type_='unique')
    op.create_unique_constraint('uq_stage_ai_unit_generation', 'stage_ai_unit',
        ['stage_chain_run_id','kind','group_id','source_sha256','generation'])
    op.execute("CREATE TRIGGER trg_stage_ai_generation_pin BEFORE UPDATE ON stage_ai_unit "
               "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('generation')")


def downgrade() -> None:
    if op.get_bind().execute(text('SELECT EXISTS(SELECT 1 FROM stage_ai_unit WHERE generation > 0)')).scalar_one():
        raise RuntimeError('stage_ai_generations_in_use')
    op.execute('DROP TRIGGER trg_stage_ai_generation_pin ON stage_ai_unit')
    op.drop_constraint('uq_stage_ai_unit_generation', 'stage_ai_unit', type_='unique')
    op.create_unique_constraint('uq_stage_ai_unit_source', 'stage_ai_unit',
        ['stage_chain_run_id','kind','group_id','source_sha256'])
    op.drop_constraint('ck_stage_ai_unit_generation', 'stage_ai_unit', type_='check')
    op.drop_column('stage_ai_unit', 'generation')
