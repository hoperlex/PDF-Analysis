"""0068: separate human-review identity from exact evidence grounding.

Old rows and evidence remain untouched. An unverified reviewable observation has
an identity and a real gate limitation, never fabricated spans. Memory retains the
same limitation after project deletion. Refuse downgrade while this data exists.
"""
from alembic import op
from sqlalchemy import text

revision = "0068_reviewable_findings"
down_revision = "0067_precedents_wave5"
branch_labels = None
depends_on = None
_REASONS = (
    'quotation_absent', 'quotation_on_different_page', 'span_outside_page', 'span_outside_block',
    'span_length_mismatch', 'quote_in_recognised_text', 'norm_label_unknown', 'norm_quote_too_short',
    'norm_quote_ambiguous', 'norm_quote_absent', 'norm_value_not_in_quote', 'stated_value_not_in_evidence',
    'block_not_in_run_geometry', 'block_crop_mismatch', 'block_quote_not_in_recognised',
)


def _reasons(values):
    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_ungrounded_reason")
    literals = ', '.join("'" + value + "'" for value in values)
    op.execute(f"ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_ungrounded_reason "
               f"CHECK (ungrounded_reason IS NULL OR ungrounded_reason IN ({literals}))")


def upgrade():
    _reasons((*_REASONS, 'source_binding_unverified'))
    op.execute("""
        ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_grounding;
        ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_grounding_kind;
        ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_grounding_kind
            CHECK (grounding_kind IN ('text_span', 'portal_block', 'unverified'));
        ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_grounding CHECK (
            (grounded AND finding_uid IS NOT NULL AND ungrounded_reason IS NULL AND grounding_kind <> 'unverified')
            OR (NOT grounded AND ungrounded_reason IS NOT NULL
                AND ((grounding_kind = 'unverified' AND finding_uid IS NOT NULL)
                     OR (grounding_kind <> 'unverified' AND finding_uid IS NULL)))
        );
        ALTER TABLE decision_memory_content ADD COLUMN unverified_reason text NULL
            CONSTRAINT ck_decision_memory_content_unverified_reason
            CHECK (unverified_reason IS NULL OR char_length(unverified_reason) BETWEEN 1 AND 200);
        ALTER TABLE finding ADD COLUMN publication_policy text NULL
            CONSTRAINT ck_finding_publication_policy CHECK (publication_policy IS NULL OR publication_policy = 'reviewable-v1');
        ALTER TABLE decision_memory_content ADD COLUMN source_observations jsonb NOT NULL DEFAULT '[]'::jsonb
            CONSTRAINT ck_decision_memory_content_source_observations CHECK (jsonb_typeof(source_observations) = 'array');
        COMMENT ON COLUMN finding_observation.grounded IS
            'Exact source grounding only. A Finding identity also admits unverified issues to human review (0068).';
    """)


def downgrade():
    connection = op.get_bind()
    if connection.execute(text("SELECT EXISTS (SELECT 1 FROM finding_observation WHERE grounding_kind = 'unverified') "
                               "OR EXISTS (SELECT 1 FROM finding WHERE publication_policy IS NOT NULL) "
                               "OR EXISTS (SELECT 1 FROM decision_memory_content WHERE unverified_reason IS NOT NULL OR source_observations <> '[]'::jsonb)")).scalar():
        raise RuntimeError("0068: retain unverified findings, human decisions and memory; downgrade refused")
    _reasons(_REASONS)
    op.execute("""
        ALTER TABLE decision_memory_content DROP COLUMN unverified_reason;
        ALTER TABLE decision_memory_content DROP COLUMN source_observations;
        ALTER TABLE finding DROP COLUMN publication_policy;
        ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_grounding;
        ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_grounding_kind;
        ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_grounding_kind
            CHECK (grounding_kind IN ('text_span', 'portal_block'));
        ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_grounding CHECK (
            grounded = (finding_uid IS NOT NULL) AND grounded = (ungrounded_reason IS NULL)
        );
    """)
