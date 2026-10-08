"""Release history and each account's monotone read mark (W52-SEAL-01).

Release identity is a canonical, immutable SemVer natural key. Revisions are events:
neither a release nor a revision may be rewritten or removed. The account mark is
the one mutable projection and can only move forward in release sort order.

Downgrade is deliberately forward-only for populated release history or marks. An
empty 0016 schema may be dropped; a populated one requires database restore.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0016_release_notes"
down_revision: str | None = "0015_accounts_roles_registration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE release (
            pk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            version text NOT NULL UNIQUE,
            sort_key text COLLATE "C" NOT NULL UNIQUE,
            is_archive boolean NOT NULL DEFAULT false,
            CONSTRAINT ck_release_version_nonempty CHECK (length(version) BETWEEN 5 AND 255),
            CONSTRAINT ck_release_sort_key_nonempty CHECK (length(sort_key) > 0)
        );
        CREATE TABLE release_revision (
            release_pk bigint NOT NULL REFERENCES release(pk) ON DELETE RESTRICT,
            revision integer NOT NULL CHECK (revision >= 1),
            released_on date NOT NULL,
            title text NOT NULL CHECK (length(trim(title)) > 0),
            content jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object'),
            content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
            loaded_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_release_revision PRIMARY KEY (release_pk, revision)
        );
        CREATE TABLE account_release_mark (
            user_uid text PRIMARY KEY REFERENCES app_user(user_uid) ON DELETE CASCADE,
            read_through_release_pk bigint NOT NULL REFERENCES release(pk) ON DELETE RESTRICT,
            marked_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_account_release_mark_release ON account_release_mark(read_through_release_pk);
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION am_guard_release_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $fn$
        BEGIN
            RAISE EXCEPTION 'release history is append-only'
                USING ERRCODE = 'AM003';
        END
        $fn$;
        CREATE TRIGGER trg_release_append_only
            BEFORE UPDATE OR DELETE ON release
            FOR EACH ROW EXECUTE FUNCTION am_guard_release_append_only();
        CREATE TRIGGER trg_release_revision_append_only
            BEFORE UPDATE OR DELETE ON release_revision
            FOR EACH ROW EXECUTE FUNCTION am_guard_release_append_only();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION am_guard_account_release_mark()
        RETURNS trigger LANGUAGE plpgsql AS $fn$
        DECLARE old_key text;
        DECLARE new_key text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                -- ON DELETE CASCADE from app_user is the only legitimate deletion.
                IF pg_trigger_depth() > 1 THEN RETURN OLD; END IF;
                RAISE EXCEPTION 'account release mark cannot be deleted directly'
                    USING ERRCODE = 'AM003';
            END IF;
            IF TG_OP = 'INSERT' THEN RETURN NEW; END IF;
            IF NEW.user_uid IS DISTINCT FROM OLD.user_uid THEN
                RAISE EXCEPTION 'account release mark owner is immutable'
                    USING ERRCODE = 'AM003';
            END IF;
            SELECT sort_key INTO old_key FROM release WHERE pk = OLD.read_through_release_pk;
            SELECT sort_key INTO new_key FROM release WHERE pk = NEW.read_through_release_pk;
            IF new_key IS NULL THEN
                RAISE EXCEPTION 'unknown release mark' USING ERRCODE = 'AM003';
            END IF;
            IF new_key <= old_key THEN RETURN NULL; END IF;
            NEW.marked_at := now();
            RETURN NEW;
        END
        $fn$;
        CREATE TRIGGER trg_account_release_mark
            BEFORE INSERT OR UPDATE OR DELETE ON account_release_mark
            FOR EACH ROW EXECUTE FUNCTION am_guard_account_release_mark();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("account_release_mark", "release_revision", "release"):
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            raise RuntimeError(
                "refusing to downgrade 0016_release_notes with release history or marks; "
                "restore a database backup instead"
            )
    op.execute("DROP TABLE account_release_mark;")
    op.execute("DROP TABLE release_revision;")
    op.execute("DROP TABLE release;")
    op.execute("DROP FUNCTION am_guard_account_release_mark();")
    op.execute("DROP FUNCTION am_guard_release_append_only();")
