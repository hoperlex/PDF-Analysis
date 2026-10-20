"""`W60-PRICE-LIST-01` phase A: global vendor lists and project overrides on real PostgreSQL.

Through ``auditmanager.optimisation.public`` only: the administrator's global list per section,
the expert's project override (``list`` or ``inherit``), the effective list of every section,
exact repeats that write nothing, stale writers refused, history with actors, refusals by role
and scope, and authors that cannot be purged.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository
from auditmanager.optimisation.public import (
    SECTION_ORDER,
    VendorListEntry,
    get_effective_vendor_lists,
    list_global_vendor_lists,
    list_vendor_list_history,
    set_global_vendor_list,
    set_project_vendor_list,
)
from auditmanager.shared.errors import DomainError, ErrorCode

accounts = AccountRepository()

CABLE = [
    {"material": "Кабель силовой", "vendor": "Кабельный завод", "note": "только с сертификатом"},
    {"material": "Кабель силовой", "vendor": "Электрокабель"},
]
LAMPS = [{"material": "Светильники", "vendor": "Световые технологии"}]


def _roles(session: Session, uid: str) -> frozenset[str]:
    return accounts.roles_of(session, uid)


def _global(session: Session, cast: Any, section: str = "EOM", entries: Any = None, **extra: Any):
    change = set_global_vendor_list(
        session,
        section_code=section,
        entries=CABLE if entries is None else entries,
        actor_uid=extra.pop("actor", cast.admin),
        actor_roles=_roles(session, extra.pop("roles_of", cast.admin)),
        **extra,
    )
    session.commit()
    return change


def _project(session: Session, cast: Any, mode: str = "list", entries: Any = None, **extra: Any):
    actor = extra.pop("actor", cast.expert)
    change = set_project_vendor_list(
        session,
        project_uid=extra.pop("project_uid", cast.project),
        section_code=extra.pop("section", "EOM"),
        mode=mode,
        entries=(LAMPS if mode == "list" else None) if entries is None else entries,
        actor_uid=actor,
        actor_roles=_roles(session, actor),
        **extra,
    )
    session.commit()
    return change


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    session = args[0]
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    session.rollback()
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


def _revisions(session: Session) -> int:
    session.rollback()
    return int(session.execute(text("SELECT count(*) FROM vendor_list_revision")).scalar_one())


def _effective(session: Session, cast: Any, project: str | None = None) -> dict[str, Any]:
    lists = get_effective_vendor_lists(
        session, project_uid=project or cast.project, actor_roles=_roles(session, cast.expert)
    )
    assert tuple(item.section_code for item in lists) == SECTION_ORDER
    return {item.section_code: item for item in lists}


# -- the global list --------------------------------------------------------------------------


def test_the_administrator_sets_a_global_list_and_an_exact_repeat_writes_nothing(session: Session, cast) -> None:
    first = _global(session, cast)
    assert first.created is True
    revision = first.revision
    assert revision is not None and revision.vendor_list_id.startswith("vnl_")
    assert (revision.scope, revision.project_uid, revision.section_code, revision.mode) == (
        "global", None, "EOM", "list",
    )
    assert (revision.revision_number, revision.entry_count, revision.set_by_user_uid) == (1, 2, cast.admin)
    assert revision.entries == (
        VendorListEntry("Кабель силовой", "Кабельный завод", "только с сертификатом"),
        VendorListEntry("Кабель силовой", "Электрокабель", None),
    )

    repeat = _global(session, cast, entries=[dict(entry) for entry in CABLE])
    assert repeat.created is False and repeat.revision == revision
    changed = _global(session, cast, entries=CABLE[:1])
    assert changed.created is True and changed.revision.revision_number == 2
    cleared = _global(session, cast, entries=[])
    assert cleared.revision.entry_count == 0 and cleared.revision.revision_number == 3
    assert _revisions(session) == 3


def test_only_an_administrator_sets_the_global_list(session: Session, cast) -> None:
    for who in ("expert", "nobody"):
        uid = getattr(cast, who)
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, set_global_vendor_list, session, section_code="EOM",
            entries=CABLE, actor_uid=uid, actor_roles=_roles(session, uid),
        )
        assert dict(refused.detail_fields) == {"aggregate_type": "VendorList", "required_capability": "role:admin"}
    assert _global(session, cast, actor=cast.admin_expert, roles_of=cast.admin_expert).created
    assert _revisions(session) == 1


# -- the project override ---------------------------------------------------------------------


def test_the_effective_list_is_the_project_override_else_the_global_list_else_none(session: Session, cast) -> None:
    global_revision = _global(session, cast).revision
    _global(session, cast, section="OV", entries=LAMPS)
    effective = _effective(session, cast)
    assert (effective["EOM"].source, effective["EOM"].effective) == ("global", global_revision)
    assert (effective["AR"].source, effective["AR"].effective) == ("none", None)
    assert effective["OV"].source == "global"

    override = _project(session, cast).revision
    assert (override.scope, override.project_uid, override.mode, override.set_by_user_uid) == (
        "project", cast.project, "list", cast.expert,
    )
    effective = _effective(session, cast)
    assert (effective["EOM"].source, effective["EOM"].effective) == ("project", override)
    assert effective["EOM"].global_revision == global_revision
    assert effective["EOM"].project_revision == override
    # Another project still follows the global list.
    assert _effective(session, cast, cast.other_project)["EOM"].source == "global"

    inherit = _project(session, cast, mode="inherit").revision
    assert (inherit.mode, inherit.entry_count, inherit.revision_number) == ("inherit", 0, 2)
    effective = _effective(session, cast)
    assert (effective["EOM"].source, effective["EOM"].effective) == ("global", global_revision)
    assert effective["EOM"].project_revision == inherit

    empty = _project(session, cast, entries=[]).revision
    effective = _effective(session, cast)
    assert (effective["EOM"].source, effective["EOM"].effective) == ("project", empty)
    assert empty.entries == () and empty.revision_number == 3


def test_project_repeats_write_nothing(session: Session, cast) -> None:
    nothing = _project(session, cast, mode="inherit")
    assert (nothing.created, nothing.revision) == (False, None)
    first = _project(session, cast)
    assert _project(session, cast).created is False
    _project(session, cast, mode="inherit")
    again = _project(session, cast, mode="inherit")
    assert again.created is False and again.revision.mode == "inherit"
    assert first.revision.revision_number == 1
    assert _revisions(session) == 2


def test_only_an_expert_overrides_a_project_list_and_inherit_carries_no_entries(session: Session, cast) -> None:
    for who in ("admin", "nobody"):
        uid = getattr(cast, who)
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, set_project_vendor_list, session, project_uid=cast.project,
            section_code="EOM", mode="list", entries=LAMPS, actor_uid=uid, actor_roles=_roles(session, uid),
        )
        assert refused.detail_fields["required_capability"] == "role:expert"
    refused = _refused(
        ErrorCode.VALIDATION_FAILED, set_project_vendor_list, session, project_uid=cast.project,
        section_code="EOM", mode="inherit", entries=LAMPS, actor_uid=cast.expert,
        actor_roles=_roles(session, cast.expert),
    )
    assert refused.detail_fields["constraint"] == "inherit_has_no_entries"
    assert _revisions(session) == 0


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"project_uid": "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, ErrorCode.NOT_FOUND),
        ({"project_uid": "bad"}, ErrorCode.VALIDATION_FAILED),
        ({"section_code": "ЭОМ"}, ErrorCode.VALIDATION_FAILED),
        ({"mode": "replace"}, ErrorCode.VALIDATION_FAILED),
        ({"entries": [{"material": "без поставщика"}]}, ErrorCode.VALIDATION_FAILED),
        ({"expected_vendor_list_id": "bad"}, ErrorCode.VALIDATION_FAILED),
    ],
)
def test_malformed_project_requests_are_refused_and_write_nothing(
    session: Session, cast, overrides: dict[str, Any], code: ErrorCode
) -> None:
    arguments: dict[str, Any] = {
        "project_uid": cast.project, "section_code": "EOM", "mode": "list", "entries": LAMPS,
        "actor_uid": cast.expert, "actor_roles": _roles(session, cast.expert),
    }
    arguments.update(overrides)
    _refused(code, set_project_vendor_list, session, **arguments)
    assert _revisions(session) == 0


def test_a_writer_that_read_a_stale_revision_is_refused(session: Session, cast) -> None:
    first = _global(session, cast).revision
    second = _global(session, cast, entries=LAMPS, expected_vendor_list_id=first.vendor_list_id).revision
    refused = _refused(
        ErrorCode.CONFLICT, set_global_vendor_list, session, section_code="EOM", entries=CABLE,
        actor_uid=cast.admin, actor_roles=_roles(session, cast.admin),
        expected_vendor_list_id=first.vendor_list_id,
    )
    assert dict(refused.detail_fields) == {"aggregate_type": "VendorList", "conflict_reason": "vendor_list_changed"}
    # "I saw no list" when one exists is stale too; on an empty scope it is current.
    _refused(
        ErrorCode.CONFLICT, set_global_vendor_list, session, section_code="EOM", entries=CABLE,
        actor_uid=cast.admin, actor_roles=_roles(session, cast.admin), expect_current=True,
    )
    assert _project(session, cast, expect_current=True).created is True
    assert _revisions(session) == 3
    assert second.revision_number == 2


def test_history_is_newest_first_with_actors_and_reads_need_a_role(session: Session, cast) -> None:
    _global(session, cast)
    _global(session, cast, entries=LAMPS, actor=cast.admin_expert, roles_of=cast.admin_expert)
    _project(session, cast)
    roles = _roles(session, cast.expert)
    history = list_vendor_list_history(session, section_code="EOM", actor_roles=roles)
    assert [(r.revision_number, r.set_by_user_uid) for r in history] == [(2, cast.admin_expert), (1, cast.admin)]
    project_history = list_vendor_list_history(
        session, section_code="EOM", project_uid=cast.project, actor_roles=roles
    )
    assert [(r.scope, r.set_by_user_uid) for r in project_history] == [("project", cast.expert)]
    globals_ = dict(list_global_vendor_lists(session, actor_roles=roles))
    assert tuple(globals_) == SECTION_ORDER
    assert globals_["EOM"].revision_number == 2 and globals_["AR"] is None

    nobody = _roles(session, cast.nobody)
    for call, kwargs in (
        (get_effective_vendor_lists, {"project_uid": cast.project}),
        (list_global_vendor_lists, {}),
        (list_vendor_list_history, {"section_code": "EOM"}),
    ):
        refused = _refused(ErrorCode.PERMISSION_DENIED, call, session, actor_roles=nobody, **kwargs)
        assert refused.detail_fields["required_capability"] == "role:admin|expert"
    _refused(ErrorCode.NOT_FOUND, get_effective_vendor_lists, session,
             project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", actor_roles=roles)
    _refused(ErrorCode.VALIDATION_FAILED, list_vendor_list_history, session,
             section_code="XX", actor_roles=roles)


@pytest.mark.parametrize("scope", ["global", "project"])
def test_a_vendor_list_author_cannot_be_purged(session: Session, cast, scope: str) -> None:
    if scope == "global":
        _global(session, cast, actor=cast.admin_expert, roles_of=cast.admin_expert)
        subject = cast.admin_expert
    else:
        _project(session, cast)
        subject = cast.expert
    seed = str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
    accounts.archive_account(session, actor_uid=seed, user_uid=subject)
    session.commit()
    refused = _refused(ErrorCode.CONFLICT, accounts.purge_account, session, actor_uid=seed, user_uid=subject)
    assert dict(refused.detail_fields) == {"conflict_reason": "account_referenced"}
    assert "vendor_list_revision.set_by_user_uid" in accounts.references_to(session, subject)
