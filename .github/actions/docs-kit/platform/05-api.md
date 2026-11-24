<!-- docs-kit: nav="API" -->
# {{NAME}}: API Reference

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/05-api.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Catalog the APIs here; each service's 05-api.md documents its operations in full.
-->

## 1. Overview

<Which services expose APIs, to whom, and the protocols they use.>

## 2. API catalog

| Service | Interface | Path | Callers | Documented in |
|---|---|---|---|---|
| <service> | <GraphQL / HTTP / WebSocket> | `/graphql` | <callers> | <link to the service's 05-api.md> |

## 3. Conventions

<Shared conventions: GraphQL schema style, error codes and extensions, pagination, headers, authentication.>

## 4. External APIs

| API | Owner | Used by | Purpose |
|---|---|---|---|
| <platform or third-party API> | <team or repository> | <services> | <purpose> |

## 5. Health and readiness

<The health endpoints every service exposes and how Kubernetes probes use them.>

## 6. Versioning and compatibility

<Schema evolution rules, deprecations, and clients that depend on these APIs.>
