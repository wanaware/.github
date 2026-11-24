<!-- docs-kit: nav="API" -->
# {{NAME}}: API Reference

{{NAV}}

{{META}}

<!--
TEMPLATE: {{DOCS_PATH}}/05-api.md
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Asynchronous interfaces (NATS) are documented in 03-messaging.md; this document covers request/response
and streaming endpoints.
-->

## 1. Overview

| Interface | Protocol | Path | Port | Authentication |
|---|---|---|---|---|
| <GraphQL API / health / UI> | <HTTP / WebSocket> | `/graphql` | `8080` | <mechanism> |

<!-- Required diagram (when the service exposes an API): flowchart of the request pipeline
(router → middleware → auth → resolver → service → store). -->

## 2. GraphQL API

### 2.1 Endpoint and schema

<Endpoint, schema file locations, code generation (gqlgen?), introspection and playground availability.>

### 2.2 Queries

| Operation | Purpose | Authorization |
|---|---|---|
| <query> | <purpose> | <action / role / public / platform> |

### 2.3 Mutations

| Operation | Purpose | Authorization |
|---|---|---|
| <mutation> | <purpose> | <action / role / public / platform> |

### 2.4 Subscriptions

### 2.5 Example

## 3. HTTP endpoints

| Method | Path | Purpose | Authentication |
|---|---|---|---|
| `GET` | `/health` | <purpose> | None |

## 4. Streaming and WebSocket endpoints

## 5. Error model

<Error shapes, GraphQL error extensions / codes, HTTP status codes and when each is returned.>

## 6. Health and readiness

| Endpoint | Port | Checks | Used by |
|---|---|---|---|
| `/health` | `8080` | <what it checks> | <Kubernetes probe / load balancer> |

## 7. Versioning and compatibility

<Schema evolution rules, deprecated operations, clients that depend on this API.>
