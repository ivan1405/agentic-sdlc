# API & contract design

<!-- summary: Contract-first, versioned, backward-compatible; consistent errors, pagination, and idempotency. -->
<!-- tier: domain -->
<!-- category: Product & Interface -->

An API is a promise to callers you don't control. Breaking it is expensive and
often silent, so design the contract before the implementation and change it
deliberately.

**Contract-first.** Define the schema (OpenAPI, protobuf, GraphQL SDL, JSON
Schema) before writing handlers, and treat it as the source of truth both sides
generate from. The contract is reviewed like code.

**Backward compatibility is the default.** Add fields, don't repurpose or remove
them. A change that could break an existing caller is a new version, not an edit
to the current one. Version explicitly (URL, header, or package) and document
the deprecation window.

**Consistent, typed errors.** One error shape across the whole surface: a stable
machine-readable code, a human message, and enough detail to act — never a raw
stack trace. Use the transport's status semantics correctly (client vs server
fault); don't return `200` with an error body.

**Idempotency for writes.** Retries happen. Unsafe operations take an
idempotency key (or are naturally idempotent) so a retried request doesn't
double-charge or double-create.

**Pagination and limits from day one.** Any list endpoint is paginated and
bounded — an unbounded list is an outage the first time the data grows. Return
stable ordering and a continuation token, not offset math that skips rows under concurrent writes.

**Validate at the edge.** Reject malformed requests with a clear error before any
business logic runs (see boundary validation). Be strict in what you accept.
