"""``0004_cost_basis`` refuses a downgrade that would destroy provenance.

``W5-ADV`` ran ``head -> 0004 -> 0003 -> head`` against a populated database and found that
the round trip relabels every ``measured`` call as ``estimated``: the dropped column comes
back with its ``estimated`` default, and ``trg_model_call_immutable`` then refuses the
UPDATE that would put it right. The loss is silent and permanent.

That is the mirror of what ``0004``'s own upgrade comment forbids. It says a backfill would
"invent provenance for calls nobody measured"; the round trip erases provenance for calls
somebody did. `OD-02`'s revision to a proxy that reports real costs is what made the
distinction worth recording, so losing it quietly defeats the column's only purpose.

The fix is refusal, not preservation: the information genuinely cannot survive a column
drop, so the honest behaviour is to stop and make an operator decide, rather than to decide
for them by discarding it.
"""

from __future__ import annotations

from sqlalchemy import text

from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    MIGRATE_ARGV,
    run_foundation_command,
)

DOWNGRADE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "downgrade",
    "0003_open_items",
]

#: The shortest chain of rows that lets a `model_call` exist: it is a grandchild of
#: `project` through `document`/`document_version` and a child of `audit_run`.
#: `audit_run.command_id` is nullable, so no `command_record` is needed. Written as
#: literal SQL rather than through the
#: repositories on purpose -- this suite tests the migration, so it must not depend on the
#: application layer agreeing with it.
_CHAIN = """
INSERT INTO project (project_uid, name) VALUES (:prj, 'downgrade guard');
INSERT INTO document (document_uid, project_uid, display_title)
    VALUES (:doc, :prj, 'downgrade guard');
INSERT INTO document_version
    (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count)
    VALUES (:ver, :doc, 1, 'application/pdf', 1024, :sha, 1);
INSERT INTO audit_run
    (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id,
     provider_mode, frozen_input_digest)
    VALUES (:run, :prj, :ver, :profile, :bundle, 'live', :sha);
-- `ck_model_call_succeeded_has_response`: a succeeded call must carry a response digest.
INSERT INTO model_call
    (model_call_id, run_id, stage_id, provider, model_identity, provider_mode,
     request_sha256, response_sha256, status, cost_micros, cost_basis)
    VALUES (:call, :run, 'text_analysis', 'anthropic', 'claude-opus-5', 'live',
            :sha, :response_sha, 'succeeded', 38225, 'measured');
"""

#: Every id is CHECK-constrained to ``^<prefix>_[0-9A-HJKMNP-TV-Z]{26}$`` -- Crockford
#: base32, which excludes I, L, O and U. A readable filler would violate the constraint,
#: so the ids are structural rather than descriptive.
_SUFFIX = "0" * 26
_IDS = {
    "prj": f"prj_{_SUFFIX}",
    "doc": f"doc_{_SUFFIX}",
    "ver": f"ver_{_SUFFIX}",
    "run": f"run_{_SUFFIX}",
    "call": f"mc_{_SUFFIX}",
    "profile": f"ap_{_SUFFIX}",
    "bundle": f"pb_{_SUFFIX}",
    "sha": "a" * 64,
    "response_sha": "b" * 64,
}


def _seed_a_measured_call(engine) -> None:
    with engine.begin() as connection:
        for statement in filter(None, (s.strip() for s in _CHAIN.split(";"))):
            connection.execute(text(statement), _IDS)


def test_a_database_with_no_measurements_still_downgrades(
    migrated_database, migrated_engine
):
    """The precondition, and it is the whole reason this guard is not vacuous.

    If the downgrade were broken for every database, the refusal below would prove only
    that something went wrong -- not that it went wrong *because* a measurement was at
    risk. Nothing here is measured, so the path must stay open.
    """
    url = migrated_database.url.render_as_string(hide_password=False)
    # Closed before the downgrade runs. An open connection holds locks and `ALTER TABLE`
    # waits on them: the first version of this test leaked one here and alembic hung for
    # the full 180 s timeout rather than failing.
    with migrated_engine.connect() as connection:
        measured = connection.execute(
            text("SELECT count(*) FROM model_call WHERE cost_basis = 'measured'")
        ).scalar_one()
    assert measured == 0, "a freshly migrated database carries no calls at all"

    result = run_foundation_command(DOWNGRADE_ARGV, url)
    assert result.returncode == 0, result.describe()

    # And back up, so the fixture's database is left at head for the next assertion.
    assert run_foundation_command(MIGRATE_ARGV, url).returncode == 0


def test_a_measured_call_makes_the_downgrade_refuse(
    migrated_database, migrated_engine
):
    """The claim. One measured row is enough to stop it."""
    url = migrated_database.url.render_as_string(hide_password=False)
    _seed_a_measured_call(migrated_engine)

    result = run_foundation_command(DOWNGRADE_ARGV, url)

    assert result.returncode != 0, (
        "the downgrade succeeded although a measured cost was recorded; re-upgrading "
        "would relabel it as estimated and the append-only trigger would refuse to "
        "correct it\n" + result.describe()
    )
    combined = (result.stdout + result.stderr).lower()
    assert "cost_basis" in combined and "measured" in combined, (
        "the refusal must name what it is protecting, or an operator cannot act on it\n"
        + result.describe()
    )

    # The column must still be there: a refusal that half-ran would be worse than none.
    with migrated_engine.connect() as connection:
        surviving = connection.execute(
            text("SELECT cost_basis FROM model_call WHERE model_call_id = :call"),
            {"call": _IDS["call"]},
        ).scalar_one()
    assert surviving == "measured", "the refusal must leave the row exactly as it was"
