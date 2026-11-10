"""0065 -- the rendered PNG of a norm page: ``norm_crop_render`` (`CRIT-SEAL-52`, `D-681`; contract 1.52.0).

Revision ID: 0065_norm_crop_render
Revises: 0064_precedents_seal

`CRIT-SEAL-50` sealed the storage of the «Прецеденты» programme and left one table out, because a table that holds a Blob reference needs an entry in
``scripts/recovery/blob_reference_audit.py`` (a closed registry of Blob columns), a path that seal did not own. This seal owns it, and adds the table.

What this revision adds
-----------------------
``norm_crop_render`` (plan-v5 section 3.4, ``DECISION-MEMORY-01`` section 6.3; the norm side, **KEEP**)
    The PNG of one norm page, made once from the page's one-page PDF and published as a Blob, so that every later delivery of the page to the critic's
    task (``crop_id: norm.<nbd_...>``) reuses it. One row per (source binding, render profile): the source is the custody binding of the one-page
    PDF (``norm_custody_binding``, a ``nbd`` identity, immutable and never deleted), the profile names how it was rendered (a re-render with another
    profile is another row), and the Blob is a reference to bytes the storage port holds, with their digest, size, media type and pixel size so the
    reference audit can compare the row with the Blob. The row is immutable: a render is a derived fact of a binding that does not change.

It is not memory content. The decision memory's own crops (``decision_memory_crop``) belong to a case and leave with a forget of the case; a norm page
render belongs to the norm corpus, which a purge of product data and a forget of a case never touch. Two tables may name the same Blob (the bytes are
content-addressed), and the forget tool already keeps a Blob that any other column of the catalogue names.

Nothing writes the table yet: ``M7-NORM-PNG`` does.

Downgrade
---------
Refused while the table holds a row: dropping it would orphan the renders the critic's tasks were declared with (AGENTS section 4, no silent
fallback). Otherwise the table is dropped.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0065_norm_crop_render"
down_revision: str | None = "0064_precedents_seal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_PROFILE = "^[a-z0-9][a-z0-9._-]{0,63}$"
_SHA256 = "^[0-9a-f]{64}$"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE norm_crop_render (
            norm_custody_binding_id text NOT NULL
                CONSTRAINT ck_norm_crop_render_norm_custody_binding_id_format CHECK (norm_custody_binding_id ~ '^nbd_{ULID}$')
                CONSTRAINT fk_norm_crop_render_binding
                    REFERENCES norm_custody_binding (norm_custody_binding_id) ON DELETE RESTRICT,
            render_profile text NOT NULL
                CONSTRAINT ck_norm_crop_render_render_profile CHECK (render_profile ~ '{_PROFILE}'),
            blob_id text NOT NULL
                CONSTRAINT ck_norm_crop_render_blob_id_format CHECK (blob_id ~ '^blob_{ULID}$')
                CONSTRAINT fk_norm_crop_render_blob REFERENCES blob (blob_id) ON DELETE RESTRICT,
            sha256 text NOT NULL
                CONSTRAINT ck_norm_crop_render_sha256 CHECK (sha256 ~ '{_SHA256}'),
            size_bytes bigint NOT NULL
                CONSTRAINT ck_norm_crop_render_size_bytes CHECK (size_bytes >= 1),
            media_type text NOT NULL
                CONSTRAINT ck_norm_crop_render_media_type CHECK (media_type = 'image/png'),
            width_px integer NOT NULL
                CONSTRAINT ck_norm_crop_render_width_px CHECK (width_px >= 1),
            height_px integer NOT NULL
                CONSTRAINT ck_norm_crop_render_height_px CHECK (height_px >= 1),
            rendered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_norm_crop_render PRIMARY KEY (norm_custody_binding_id, render_profile)
        )
    """)
    # The reference audit and the forget tool look a Blob up by the columns that name it.
    op.execute("CREATE INDEX ix_norm_crop_render_blob ON norm_crop_render (blob_id)")
    op.execute(
        "CREATE TRIGGER trg_norm_crop_render_immutable BEFORE UPDATE OR DELETE ON norm_crop_render "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "COMMENT ON TABLE norm_crop_render IS "
        "'CRIT-SEAL-52 (plan-v5 section 3.4, DECISION-MEMORY-01 section 6.3): the PNG of one norm page, made once from the page''s one-page "
        "PDF (a norm_custody_binding) and published as a Blob, reused by every later delivery to the critic. One row per (binding, render "
        "profile); immutable. The norm side, KEEP: not memory content, never deleted by a purge or a forget.';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(text("SELECT EXISTS (SELECT 1 FROM norm_crop_render)")).scalar_one():
        raise RuntimeError(
            "refusing to downgrade 0065_norm_crop_render with rendered norm pages held in norm_crop_render; restore a database backup instead"
        )
    op.execute("DROP TABLE norm_crop_render")
