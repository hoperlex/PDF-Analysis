"""The error kernel against the frozen catalog.

Every assertion here has a mutation that reddens it, recorded in the docstring, because a
guard nobody has seen fail is not evidence.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditmanager.shared.errors import (
    CONTRACT_VERSION,
    DomainError,
    ErrorCode,
    InternalError,
    UnsafeDetailKey,
    UnsafeMessage,
    build,
    from_internal,
)

CONTRACT = Path(__file__).resolve().parents[3] / "contracts/domain/v1/error-codes.json"
RAW = json.loads(CONTRACT.read_text(encoding="utf-8"))


class TheEnumIsExactlyTheCatalog(unittest.TestCase):
    """Mutation: delete a member from ErrorCode -> import of codes.py raises at once."""

    def test_member_set_equals_the_catalog_key_set(self) -> None:
        self.assertEqual(frozenset(c.value for c in ErrorCode), frozenset(RAW["codes"]))

    def test_there_are_twenty_one(self) -> None:
        """Twenty-one since the wave-13 reseal: `R-3` added dependency_credential_refused."""
        self.assertEqual(len(list(ErrorCode)), 21)

    def test_contract_version_is_read_not_restated(self) -> None:
        self.assertEqual(CONTRACT_VERSION, RAW["contract_version"])


class RetryableIsPinnedToTheCatalog(unittest.TestCase):
    """Mutation: flip a retryable in the contract -> this reddens for that code."""

    def test_every_code_matches_the_catalog(self) -> None:
        for code in ErrorCode:
            with self.subTest(code=code.value):
                self.assertEqual(code.retryable, RAW["codes"][code.value]["retryable"])

    def test_retryable_is_not_a_constructor_argument(self) -> None:
        with self.assertRaises(TypeError):
            build(ErrorCode.CONFLICT, "c", retryable=True)  # type: ignore[call-arg]

    def test_the_envelope_reports_the_pinned_value(self) -> None:
        body = build(ErrorCode.DEPENDENCY_UNAVAILABLE, "c").as_dict()
        self.assertIs(body["retryable"], RAW["codes"]["dependency_unavailable"]["retryable"])


class DetailsCarryOnlyDeclaredKeys(unittest.TestCase):
    """Mutation: widen the allowed set in envelope.build -> the refusal tests redden."""

    def test_a_declared_key_is_accepted(self) -> None:
        env = build(ErrorCode.VALIDATION_FAILED, "c", details={"field": "page_count"})
        self.assertEqual(env.as_dict()["details"], {"field": "page_count"})

    def test_an_undeclared_key_raises_rather_than_being_dropped(self) -> None:
        with self.assertRaises(UnsafeDetailKey):
            build(ErrorCode.VALIDATION_FAILED, "c", details={"bucket": "audit-conv"})

    def test_a_non_scalar_value_is_refused(self) -> None:
        with self.assertRaises(UnsafeDetailKey):
            build(ErrorCode.VALIDATION_FAILED, "c", details={"field": {"nested": 1}})


class TheMessageScreenRefusesForbiddenShapes(unittest.TestCase):
    """Mutation: remove a pattern from _FORBIDDEN -> the matching case reddens."""

    CASES = {
        "filesystem path": "the object at /var/lib/minio/audit/x.pdf was refused",
        "URL": "could not reach http://127.0.0.1:59040/audit",
        "credential": "auth failed: api_key=sk-ant-abc123",
        "SQL": "SELECT id FROM blob WHERE state = 'available'",
        "stack frame": 'Traceback (most recent call last): File "s3.py", line 3',
    }

    def test_each_forbidden_shape_is_refused(self) -> None:
        for what, message in self.CASES.items():
            with self.subTest(shape=what), self.assertRaises(UnsafeMessage):
                build(ErrorCode.INTERNAL_ERROR, "c", message=message)

    def test_a_safe_sentence_passes(self) -> None:
        env = build(ErrorCode.NOT_FOUND, "c", message="No document version has that identity.")
        self.assertEqual(env.as_dict()["message"], "No document version has that identity.")

    def test_the_default_message_is_the_catalog_summary(self) -> None:
        self.assertEqual(build(ErrorCode.CONFLICT, "c").message, ErrorCode.CONFLICT.summary)


class UnmappedInternalCodesBecomeInternalError(unittest.TestCase):
    """Mutation: make from_internal re-raise -> these redden."""

    def test_an_unknown_internal_code_maps_to_internal_error(self) -> None:
        self.assertIs(from_internal("pdf_layout_weirdness"), ErrorCode.INTERNAL_ERROR)

    def test_a_known_code_maps_to_itself(self) -> None:
        self.assertIs(from_internal("cost_budget_exceeded"), ErrorCode.COST_BUDGET_EXCEEDED)

    def test_the_original_internal_code_stays_out_of_the_envelope(self) -> None:
        err = InternalError("pdf_layout_weirdness")
        body = err.envelope("c").as_dict()
        self.assertEqual(body["error_code"], "internal_error")
        self.assertNotIn("pdf_layout_weirdness", json.dumps(body))
        self.assertEqual(err.internal_code, "pdf_layout_weirdness")


class DomainErrorCarriesTheCode(unittest.TestCase):
    def test_it_builds_its_own_envelope(self) -> None:
        err = DomainError(ErrorCode.VALIDATION_FAILED, field="page_count")
        body = err.envelope("corr-9").as_dict()
        self.assertEqual(body["error_code"], "validation_failed")
        self.assertEqual(body["correlation_id"], "corr-9")
        self.assertEqual(body["details"], {"field": "page_count"})


if __name__ == "__main__":
    unittest.main()
