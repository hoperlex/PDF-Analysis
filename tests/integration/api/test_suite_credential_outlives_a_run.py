"""The credential this suite presents must outlive a complete run of the suite.

``driver.TEST_TOKEN`` is minted once, when ``driver.py`` is imported by the first ``conftest``
that loads it -- at collection -- and is the default credential of every request the driver
sends. Minted at the production lifetime (``TOKEN_LIFETIME_SECONDS``, 3600 s) it expired an hour
into a complete ``tests/integration`` run, and every directory after that hour that drives the
served application through the driver (``tests/integration/executors``) answered ``401``: 57
failures in a 95-minute run, none of them a defect (``FIX-P02-GUARDS-01``).

This pins the property, not the number: the credential verifies after a run longer than the
longest complete run so far (5740 s) and longer than the production lifetime, and it is still
bounded, so that "valid for the length of a run" has not turned into "never expires".
"""

from __future__ import annotations

import time

from w13_api_driver import (
    DEPLOYMENT_SECRET,
    SUITE_CREDENTIAL_LIFETIME_SECONDS,
    TEST_SUBJECT,
    TEST_TOKEN,
)

from auditmanager.api.security import API_TOKEN_VARIABLE, TOKEN_LIFETIME_SECONDS, build_signer

#: Longer than the longest complete run of ``tests/integration`` measured so far (5740 s), with
#: room for a slower host.
A_LONG_RUN_SECONDS = 6 * 3600

#: The most the suite credential may live: a week is a lifetime for a test token already.
A_BOUND_SECONDS = 7 * 24 * 3600


def _signer():
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    return signer


def test_the_suite_credential_is_valid_after_a_run_longer_than_the_production_lifetime():
    signer, now = _signer(), time.time()
    assert signer.verify(TEST_TOKEN, now=now).user_uid == TEST_SUBJECT.user_uid
    assert TOKEN_LIFETIME_SECONDS < A_LONG_RUN_SECONDS < SUITE_CREDENTIAL_LIFETIME_SECONDS
    for elapsed in (TOKEN_LIFETIME_SECONDS + 1, 5740, A_LONG_RUN_SECONDS):
        subject = signer.verify(TEST_TOKEN, now=now + elapsed)
        assert subject is not None, f"the suite credential has expired after {elapsed} s"
        assert subject.user_uid == TEST_SUBJECT.user_uid


def test_the_suite_credential_is_still_bounded():
    """A credential that never expired would hide a defect in the expiry check itself.

    The bound is written here and not read from the driver, so that widening the driver's
    constant to "forever" fails this test instead of moving it along.
    """
    signer, now = _signer(), time.time()
    assert SUITE_CREDENTIAL_LIFETIME_SECONDS <= A_BOUND_SECONDS
    assert signer.verify(TEST_TOKEN, now=now + A_BOUND_SECONDS + 60) is None
