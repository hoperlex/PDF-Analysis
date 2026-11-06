"""A published run of a version, made in-process under the v1 reference profile (`PROD-11-AR-V1-V2-REMOVAL-01`).

The served ``startRun`` routes a version classified АР to the draft original-source АР text profile
(1.0.0; `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`, 3821261a) and accepts it once the request carries
a priced cost consent. Between `PROD-11-AR-V1-V2-REMOVAL-01` and that hotfix it refused the version
with ``section_profile_unavailable``; it does not any more. The АР specification, price and
optimisation reads (`PROD-10` finding 2, `D-222`) take the saved text of the newest **published**
run of the version whatever made it, and their suites need such a run on an АР version in recorded
mode. The served route cannot give them one: the recorded adapter finds an answer only by the exact
request key, and the draft АР profile has no synthetic recording (see ``test_section_recordings.py``
in ``tests/integration/sections``), while the committed recordings and oracles are the v1 machinery's
reference profile's. So this helper makes the run the way the executor has always made it, outside
the served routes: it starts the run with the explicit pair the reference profile carries and
executes it with that profile and the recorded adapter. The run, its saved text layer and everything
the reads do with them are what they were; only the route to it is not the product's. Where an АР
version gets its published run in production (the served ordinary start on the draft АР profile,
or the v3 group where it is activated) is not exercised by the suites that use this.

It reads ``DATABASE_URL`` and the ``S3_*`` names from the process environment, like the composed
application the suite already built, and spends nothing (recorded mode).
"""

from __future__ import annotations

import os
import secrets

from sqlalchemy.orm import Session

from auditmanager.analysis.text import ProviderConfig, ProviderMode, RecordedAdapter
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage import S3BlobStore, S3StorageSettings
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE, resolve_reference_profile


def publish_reference_run(version_uid: str, *, tag: str = "reference") -> str:
    """Start and execute the version's run under the reference profile; return its ``run_id``."""
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
    store = S3BlobStore(S3StorageSettings.from_env())
    config = ProviderConfig(
        mode=ProviderMode.RECORDED, model_id="claude-opus-5", run_cost_ceiling_usd=1.0,
        api_key=None, ceiling_is_explicit=False,
    )
    try:
        with Session(engine, expire_on_commit=False) as session:
            started = start_audit_run(
                session, version_uid=version_uid,
                analysis_profile_id=str(V1_REFERENCE_PROFILE.analysis_profile_id),
                prompt_bundle_id=str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id),
                provider_mode="recorded",
                idempotency_key=IdempotencyKey(f"reference-run-{tag}-{secrets.token_hex(6)}"),
            )
            session.commit()
            execute_run(
                session, started.run_id, blob_store=store, adapter=RecordedAdapter(),
                provider_config=config, text_profiles=resolve_reference_profile,
            )
            session.commit()
            return str(started.run_id)
    finally:
        engine.dispose()
