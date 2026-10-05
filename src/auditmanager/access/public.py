"""What another bounded context may import from ``access`` (ALR-05).

``tests/contract/architecture/test_alr05_boundaries.py`` refuses every cross-context import
of ``auditmanager.access`` except this module. Its consumers are the composition root's
adapters and the seal that wires the W49 operations (`W49-SEAL-01`); this module re-exports
and owns no behaviour.
"""

from __future__ import annotations

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.models import (
    EMAIL_LOGIN_PATTERN,
    MAX_EMAIL_LENGTH,
    MAX_NAME_LABEL_LENGTH,
    MAX_PERSON_NAME_LENGTH,
    REGISTRATION_ID_PATTERN,
    REGISTRATION_ID_PREFIX,
    ROLE_ADMIN,
    ROLE_EXPERT,
    ROLES,
    USER_UID_PATTERN,
    USER_UID_PREFIX,
    CredentialStanding,
    RegistrationId,
    UserRecord,
    UserUid,
    name_label,
    normalize_email,
    normalize_login,
    normalize_person_name,
)
from auditmanager.access.references import ACCOUNT_REFERENCES, AccountReference
from auditmanager.access.repository import UserRepository

__all__ = [
    "ACCOUNT_REFERENCES",
    "EMAIL_LOGIN_PATTERN",
    "MAX_EMAIL_LENGTH",
    "MAX_NAME_LABEL_LENGTH",
    "MAX_PERSON_NAME_LENGTH",
    "REGISTRATION_ID_PATTERN",
    "REGISTRATION_ID_PREFIX",
    "ROLES",
    "ROLE_ADMIN",
    "ROLE_EXPERT",
    "USER_UID_PATTERN",
    "USER_UID_PREFIX",
    "AccountReference",
    "AccountRepository",
    "CredentialStanding",
    "RegistrationId",
    "UserRecord",
    "UserRepository",
    "UserUid",
    "name_label",
    "normalize_email",
    "normalize_login",
    "normalize_person_name",
]
