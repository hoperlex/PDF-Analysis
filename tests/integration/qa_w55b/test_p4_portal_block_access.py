"""Probe 4 -- who may read «Блоки»'s data, on a real version with real crops (`W55B-QA-01`).

``test_role_register.py`` sweeps the registers with stand-in ports and sample paths. This
probe asks the served application about a version that exists and a crop that exists, with
accounts in every standing the seam distinguishes, and compares each answer with the
register written out here from the rulings (`R-60` as `R-80` amends it: product reads need
any one role; product changes ``expert``) -- not read from ``security.py``.

There is no per-project membership in this product: a role is held across the deployment
(`R-55`). "A user not on the project" is therefore any other account with a role, and the
expected answer for it is the role's, which this probe states and checks.
"""

from __future__ import annotations

import pytest

from w55b_qa_support import (
    SECRET,
    call,
    classify,
    committed,
    create_project,
    portal_blocks,
    start_run,
    upload,
    wait_terminal,
)


@pytest.fixture(scope="module")
def produced(api_control, accounts) -> dict:
    """A version of ``ar_baseline.zip`` uploaded, classified and run by one expert, and one
    of its crops."""
    api_control.ensure(None)
    owner = accounts.credential("access-owner")
    project = create_project(owner, "QA P4 access")
    answer = upload(project, committed("ar_baseline.zip"), owner)
    assert answer.status == 201, answer
    version = answer.json()["version_uid"]
    classify(answer.json(), owner)  # `W59-SECTION-SEAL-01`: no run of an unclassified version
    run = start_run(version, owner)
    assert run.status == 202, run
    assert wait_terminal(run.json()["run_id"], owner)["state"] == "published"
    _, items = portal_blocks(version, owner)
    image = next(i["portal_block_id"] for i in items if "crop" in i)
    return {"owner": owner, "project": project, "version": version, "image": image}


def _foreign_credential() -> str:
    """A well-formed credential signed with a key this deployment does not hold."""
    from auditmanager.api.security import Subject, build_signer

    signer = build_signer({"AUDITMANAGER_API_TOKEN": SECRET + "-another-deployment"})
    assert signer is not None
    return signer.issue(
        Subject(user_uid="usr_01M2545JSD15ETSNNV904X991S", login="x@suite.invalid", token_epoch=1, display_label="X"),
        is_default_credential=False,
    ).token


#: standing -> (HTTP status, error_code, required_capability) for the two portal reads.
READ_EXPECTED = {
    "owner_expert": (200, None, None),
    "other_expert": (200, None, None),
    "admin_only": (200, None, None),
    "expert_and_admin": (200, None, None),
    "no_role": (403, "permission_denied", "role:admin|expert"),
    "incomplete_profile": (403, "permission_denied", "profile_completed"),
    "default_credential": (403, "permission_denied", "password_changed"),
    "archived": (401, "authentication_required", None),
    "unauthenticated": (401, "authentication_required", None),
    "malformed": (401, "authentication_required", None),
    "foreign_signature": (401, "authentication_required", None),
}


@pytest.fixture(scope="module")
def credentials(produced, accounts) -> dict[str, str | None]:
    return {
        "owner_expert": produced["owner"],
        "other_expert": accounts.credential("access-other-expert"),
        "admin_only": accounts.credential("access-admin", roles=frozenset({"admin"})),
        "expert_and_admin": accounts.credential("access-both", roles=frozenset({"expert", "admin"})),
        "no_role": accounts.credential("access-none", roles=frozenset()),
        "incomplete_profile": accounts.credential("access-incomplete", complete=False),
        "default_credential": accounts.credential("access-default", default_credential=True),
        "archived": accounts.credential("access-archived", archived=True),
        "unauthenticated": None,
        "malformed": "am2.not-a-credential.at-all",
        "foreign_signature": _foreign_credential(),
    }


def _assert_answer(answer, expected) -> None:
    status, code, capability = expected
    assert answer.status == status, answer
    if code is not None:
        body = answer.json()
        assert body["error_code"] == code, body
        assert body.get("details", {}).get("required_capability") == capability, body


@pytest.mark.parametrize("standing", sorted(READ_EXPECTED))
def test_listing_the_portal_blocks_answers_each_standing_as_the_register_says(produced, credentials, standing) -> None:
    """Expected: ``READ_EXPECTED[standing]`` -- any one role reads (an expert who did not upload
    the version included, since roles are deployment-wide), an account with no role is
    ``403 role:admin|expert``, an incomplete profile ``403 profile_completed``, a default
    credential ``403 password_changed``, and an archived account, no credential, a malformed
    one or one signed by another deployment ``401 authentication_required``. A refused answer
    carries no block data."""
    answer = call("GET", f"/versions/{produced['version']}/portal-blocks", token=credentials[standing])
    _assert_answer(answer, READ_EXPECTED[standing])
    if answer.status == 200:
        assert answer.json()["block_count"] == 12
    else:
        assert b"blk_" not in answer.body


@pytest.mark.parametrize("standing", sorted(READ_EXPECTED))
def test_streaming_a_crop_answers_each_standing_as_the_register_says(produced, credentials, standing) -> None:
    """Expected: as for the list; a refused answer is a JSON envelope, never PNG bytes."""
    answer = call(
        "GET",
        f"/versions/{produced['version']}/portal-blocks/{produced['image']}/crop",
        token=credentials[standing],
    )
    _assert_answer(answer, READ_EXPECTED[standing])
    if answer.status == 200:
        assert answer.headers["content-type"] == "image/png"
    else:
        assert not answer.body.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    ("standing", "status", "capability"),
    [("admin_only", 403, "role:expert"), ("other_expert", 201, None)],
)
def test_uploading_a_bundle_needs_the_expert_role(produced, credentials, standing, status, capability) -> None:
    """Expected: ``uploadDocument`` is an ``expert`` change: an administrator without ``expert``
    is ``403 role:expert`` (and nothing is created); another expert uploads into the first
    expert's project (``201``) -- projects are not owned."""
    answer = upload(produced["project"], committed("ar_baseline_minimal.zip"), credentials[standing])
    assert answer.status == status, answer
    if capability is not None:
        assert answer.json()["details"]["required_capability"] == capability


def test_an_unknown_version_is_not_found_for_both_reads(produced) -> None:
    """Expected: an expert asking about a version that does not exist gets ``404 not_found``
    from both reads -- never ``not_produced`` for a version that is not there."""
    missing = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    for path in (f"/versions/{missing}/portal-blocks", f"/versions/{missing}/portal-blocks/{produced['image']}/crop"):
        answer = call("GET", path, token=produced["owner"])
        assert answer.status == 404, (path, answer)
        assert answer.json()["error_code"] == "not_found"
