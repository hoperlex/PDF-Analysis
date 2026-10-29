"""The handler factory is applied by the registry to learn a handler's kind, before any dependency exists (found by the whole unit battery:
``tests/unit/comparison/work/test_handler_registry.py`` builds the shipped tuple over an empty namespace)."""

from __future__ import annotations

from types import SimpleNamespace

from auditmanager.comparison.public import HANDLER_FACTORIES, ReportHandler, report_handler
from auditmanager.comparison.report.model import WORK_KIND


def test_the_factory_reads_no_dependency_until_an_item_runs() -> None:
    handler = report_handler(SimpleNamespace())  # an empty namespace: not one attribute of the worker's dependencies exists
    assert isinstance(handler, ReportHandler)
    assert handler.kind == WORK_KIND == "comparison_report"
    assert callable(handler.run)


def test_the_shipped_tuple_holds_the_factory_once() -> None:
    assert [factory for factory in HANDLER_FACTORIES if factory is report_handler] == [report_handler]
