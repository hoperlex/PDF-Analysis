# API v1 contract area

OpenAPI is introduced in S01/S02. Do not invent hundreds of endpoints from legacy. Add endpoints per vertical slice and freeze them before frontend implementation.

Minimum conventions:

- commands accept idempotency key where replay can duplicate effects;
- errors use domain error envelope;
- opaque IDs only;
- cursor pagination for growing lists;
- object-level authorization server-side;
- file reads return safe/scoped representations, not internal S3 key.
