"""Cross-context surface of the optimisation boundary (`W60-PRICE-LIST-01`).

The composition root serves the commands and the reads from here; nothing else in this
package is reached from outside it (``tests/contract/architecture/test_alr05_boundaries.py``).
"""

from __future__ import annotations

from auditmanager.optimisation.commands import (
    VendorListChange,
    set_global_vendor_list,
    set_project_vendor_list,
)
from auditmanager.optimisation.identity import (
    PRICE_LIST_ID_PATTERN,
    PRICE_LIST_ID_PREFIX,
    PRICE_LIST_POSITION_ID_PATTERN,
    PRICE_LIST_POSITION_ID_PREFIX,
    VENDOR_LIST_ID_PATTERN,
    VENDOR_LIST_ID_PREFIX,
    PriceListId,
    PriceListPositionId,
    VendorListId,
)
from auditmanager.optimisation.parsing import (
    CURRENCY_SOURCES,
    FIELD_ORDER,
    FILE_CONSTRAINTS,
    MEDIA_TYPES,
    REPORT_VERSION,
    SKIP_REASONS,
    WARNING_REASONS,
    ParseOutcome,
    ParsedPosition,
    parse_price_list,
)
from auditmanager.optimisation.parsing.limits import MAX_BYTES, MAX_DATA_ROWS
from auditmanager.optimisation.policy import (
    AGGREGATE_PRICE_LIST,
    AGGREGATE_VENDOR_LIST,
    CONFLICT_VENDOR_LIST_CHANGED,
    MAX_VENDOR_LIST_ENTRIES,
    MODE_INHERIT,
    MODE_LIST,
    MODES,
    SCOPES,
    SECTION_ORDER,
    VendorListEntry,
)
from auditmanager.optimisation.queries import (
    DEFAULT_POSITION_PAGE,
    MAX_POSITION_PAGE,
    EffectiveVendorList,
    PositionPage,
    get_effective_vendor_lists,
    get_price_list_revision,
    list_global_vendor_lists,
    list_price_list_positions,
    list_price_list_revisions,
    list_vendor_list_history,
)
from auditmanager.optimisation.repository import (
    PriceListPositionRecord,
    PriceListRevisionRecord,
    VendorListRevisionRecord,
)
from auditmanager.optimisation.uploads import (
    COMMAND_TYPE_UPLOAD_PRICE_LIST,
    ROLE_PRICE_LIST_SOURCE,
    PriceListUploadOutcome,
    PriceListUploads,
)

__all__ = [
    "AGGREGATE_PRICE_LIST",
    "AGGREGATE_VENDOR_LIST",
    "COMMAND_TYPE_UPLOAD_PRICE_LIST",
    "CONFLICT_VENDOR_LIST_CHANGED",
    "CURRENCY_SOURCES",
    "DEFAULT_POSITION_PAGE",
    "FIELD_ORDER",
    "FILE_CONSTRAINTS",
    "MAX_BYTES",
    "MAX_DATA_ROWS",
    "MAX_POSITION_PAGE",
    "MAX_VENDOR_LIST_ENTRIES",
    "MEDIA_TYPES",
    "MODES",
    "MODE_INHERIT",
    "MODE_LIST",
    "PRICE_LIST_ID_PATTERN",
    "PRICE_LIST_ID_PREFIX",
    "PRICE_LIST_POSITION_ID_PATTERN",
    "PRICE_LIST_POSITION_ID_PREFIX",
    "REPORT_VERSION",
    "ROLE_PRICE_LIST_SOURCE",
    "SCOPES",
    "SECTION_ORDER",
    "SKIP_REASONS",
    "VENDOR_LIST_ID_PATTERN",
    "VENDOR_LIST_ID_PREFIX",
    "WARNING_REASONS",
    "EffectiveVendorList",
    "ParseOutcome",
    "ParsedPosition",
    "PositionPage",
    "PriceListId",
    "PriceListPositionId",
    "PriceListPositionRecord",
    "PriceListRevisionRecord",
    "PriceListUploadOutcome",
    "PriceListUploads",
    "VendorListChange",
    "VendorListEntry",
    "VendorListId",
    "VendorListRevisionRecord",
    "get_effective_vendor_lists",
    "get_price_list_revision",
    "list_global_vendor_lists",
    "list_price_list_positions",
    "list_price_list_revisions",
    "list_vendor_list_history",
    "parse_price_list",
    "set_global_vendor_list",
    "set_project_vendor_list",
]
