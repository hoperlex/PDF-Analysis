# Contract pin registry

This is the checklist of consumers of the independent facts file and of the live/history
boundary convention. The expected values live in `tests/support/expected_facts.json`, never in
the contract artifact they judge. The registry keeps the affected consumers enumerable instead
of discoverable only after a reseal fails.

The machine-readable block is consumed by
`tests/contract/api_v1/test_doc_prose_facts.py`. `path` plus `needle` identifies the consumer;
`event` names the change that can require moving it. A changed or removed needle fails the
inventory until the registry and the owning change move together.

```json
{
  "registry_version": 1,
  "pins": [
    {
      "pin_id": "surface-doc-prose-triple",
      "family": "surface",
      "path": "tests/contract/api_v1/test_doc_prose_facts.py",
      "needle": "assert triple == SurfaceTriple(",
      "event": "OpenAPI reseal changing a path, operation or component-schema count"
    },
    {
      "pin_id": "surface-conformance-operation-count",
      "family": "surface",
      "path": "tests/contract/api_v1/test_openapi_conformance.py",
      "needle": "FROZEN_OPERATION_COUNT = FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-conformance-schema-count",
      "family": "surface",
      "path": "tests/contract/api_v1/test_openapi_conformance.py",
      "needle": "FROZEN_SCHEMA_COUNT = FACTS.schema_count",
      "event": "OpenAPI reseal changing the component-schema count"
    },
    {
      "pin_id": "surface-conformance-operation-set",
      "family": "surface",
      "path": "tests/contract/api_v1/test_openapi_conformance.py",
      "needle": "FROZEN_OPERATIONS: tuple[tuple[str, str, str], ...] = FACTS.operations",
      "event": "OpenAPI reseal changing a method, path or operationId"
    },
    {
      "pin_id": "surface-conformance-schema-set",
      "family": "surface",
      "path": "tests/contract/api_v1/test_openapi_conformance.py",
      "needle": "FROZEN_SCHEMA_NAMES: frozenset[str] = FACTS.schema_names",
      "event": "OpenAPI reseal changing a component-schema name"
    },
    {
      "pin_id": "surface-served-path-count",
      "family": "surface",
      "path": "tests/integration/api/test_served_document_and_health_plane.py",
      "needle": "PATH_COUNT = FACTS.path_count",
      "event": "OpenAPI reseal changing the path count"
    },
    {
      "pin_id": "surface-served-operation-count",
      "family": "surface",
      "path": "tests/integration/api/test_served_document_and_health_plane.py",
      "needle": "OPERATION_COUNT = FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-served-schema-count",
      "family": "surface",
      "path": "tests/integration/api/test_served_document_and_health_plane.py",
      "needle": "SCHEMA_COUNT = FACTS.schema_count",
      "event": "OpenAPI reseal changing the component-schema count"
    },
    {
      "pin_id": "surface-router-and-document-count",
      "family": "surface",
      "path": "tests/integration/api/test_operation_surface.py",
      "needle": "def test_the_document_and_router_match_the_expected_operation_count(",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-router-count",
      "family": "surface",
      "path": "tests/integration/api/test_operation_surface.py",
      "needle": "assert len(router.routes) == FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-path-and-operation-count",
      "family": "surface",
      "path": "tests/integration/api/test_operation_surface.py",
      "needle": "assert len(paths) == FACTS.path_count and sum(",
      "event": "OpenAPI reseal changing the path or operation count"
    },
    {
      "pin_id": "surface-router-operation-id-count",
      "family": "surface",
      "path": "tests/integration/api/test_router_and_body_rules.py",
      "needle": "assert len(router.operation_ids) == FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-router-route-count-control",
      "family": "surface",
      "path": "tests/integration/api/test_router_and_body_rules.py",
      "needle": "assert len(router.routes) == FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-composition-token-case",
      "family": "surface",
      "path": "tests/integration/composition/test_api_token_channel.py",
      "needle": "assert len(application.router.routes) == FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-composition-recorded",
      "family": "surface",
      "path": "tests/integration/composition/test_composition_root.py",
      "needle": "def test_it_builds_all_the_frozen_operations(self) -> None:",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-composition-proxy",
      "family": "surface",
      "path": "tests/integration/composition/test_composition_root.py",
      "needle": "def test_a_proxied_application_wires_all_the_operations(self) -> None:",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-e2e-composition",
      "family": "surface",
      "path": "tests/e2e/pc01/test_acceptance.py",
      "needle": "assert len(client.app.router.routes) == FACTS.operation_count",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-frontend-lock-paths",
      "family": "surface",
      "path": "web/tests/guards/frontend-lock.guard.test.ts",
      "needle": "expect(lock.openapi.paths).toBe(expectedFacts.surface.path_count);",
      "event": "OpenAPI reseal changing the path count"
    },
    {
      "pin_id": "surface-frontend-lock-operations",
      "family": "surface",
      "path": "web/tests/guards/frontend-lock.guard.test.ts",
      "needle": "expect(lock.openapi.operations).toBe(expectedFacts.surface.operations.length);",
      "event": "OpenAPI reseal changing the operation count"
    },
    {
      "pin_id": "surface-frontend-lock-schemas",
      "family": "surface",
      "path": "web/tests/guards/frontend-lock.guard.test.ts",
      "needle": "expect(lock.openapi.component_schemas).toBe(expectedFacts.surface.schema_names.length);",
      "event": "OpenAPI reseal changing the component-schema count"
    },
    {
      "pin_id": "error-migration-domain-count",
      "family": "error_catalog",
      "path": "tests/contract/domain_p02/test_contract_vocabulary.py",
      "needle": "assert len(migration_module.ERROR_CODES) == FACTS.stored_error_codes",
      "event": "Domain error-catalog addition or removal"
    },
    {
      "pin_id": "error-openapi-enum-count",
      "family": "error_catalog",
      "path": "tests/contract/domain_p02/test_openapi_document.py",
      "needle": "assert len(declared) == len(set(declared)) == FACTS.api_error_codes",
      "event": "Domain error-catalog addition or removal and its OpenAPI reseal"
    },
    {
      "pin_id": "error-screen-source-count",
      "family": "error_catalog",
      "path": "tests/integration/api/test_envelope_screen_rules.py",
      "needle": "assert len(raw[\"codes\"]) == FACTS.api_error_codes",
      "event": "Domain error-catalog addition or removal"
    },
    {
      "pin_id": "error-frontend-contract-enum-count",
      "family": "error_catalog",
      "path": "web/tests/contract/seam-operations.contract.test.ts",
      "needle": "expect(ERROR_CODE_VALUES).toHaveLength(expectedFacts.error_catalog.api_codes);",
      "event": "Domain error-catalog addition or removal and its generated frontend reseal"
    },
    {
      "pin_id": "error-frontend-failure-enum-count",
      "family": "error_catalog",
      "path": "web/tests/unit/api/failure-surface.test.ts",
      "needle": "expect(ERROR_CODE_VALUES).toHaveLength(expectedFacts.error_catalog.api_codes);",
      "event": "Domain error-catalog addition or removal and its generated frontend reseal"
    },
    {
      "pin_id": "migration-application-head",
      "family": "migration_head",
      "path": "tests/contract/api_v1/test_doc_prose_facts.py",
      "needle": "assert _true_migration_head() == FACTS.migration_head",
      "event": "A new application migration head"
    },
    {
      "pin_id": "history-current-state-heading-shape",
      "family": "history_boundary",
      "path": "tests/contract/api_v1/test_doc_prose_facts.py",
      "needle": "_GENUINE_HISTORICAL_HEADING_SHAPE = re.compile(",
      "event": "A deliberate change to CURRENT_STATE.md live/history section convention"
    }
  ]
}
```

## Event checklist

| event | required action |
|---|---|
| OpenAPI reseal | move the hand-maintained `surface` facts, regenerate the client/mirror/lock, then inspect every `surface` consumer |
| error-code addition/removal | move the separate API and stored-vocabulary facts as applicable, reseal the enum and inspect every `error_catalog` consumer |
| new migration | move the hand-maintained `migration_head` fact with the migration; never derive it from the same graph it judges |
| current-state history heading change | move the heading deliberately and rerun the duplicate/early-boundary mutations before accepting `history_boundary` |

The scanner is intentionally conservative: HTTP status literals, pagination bounds, local enum
sizes and historical wave reports are not surface expectations merely because their number
happens to equal a surface count. A new independent contract-size literal outside the facts file
fails the inventory. A new facts consumer adds a registry entry.
