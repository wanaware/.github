<!-- docs-kit: nav="Data model" -->
# {{NAME}}: Data Model

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/02-data-model.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Describe the data shared between services. Each service's own stores belong in its 02-data-model.md.
-->

## 1. Overview

<The main kinds of data the system handles, which service owns each, and where the authoritative copy lives.>

## 2. Core domain model

<!-- Required diagram: classDiagram or erDiagram of the domain types shared between services. -->

## 3. Data flow and lineage

<How a record moves through the services, what each step adds or changes, and how to trace a record back
to its source.>

## 4. Shared schemas and contracts

<Schemas, payload types and configuration documents shared between services, and where each is defined.>

## 5. Data stores

| Store | Kind | Owner | Readers / writers | Documented in |
|---|---|---|---|---|
| <store> | <PostgreSQL / Neo4j / GCS / NATS KV / Redis> | <service> | <services> | <link to the service's 02-data-model.md> |

## 6. Tenancy and data isolation

<How customer / tenant scoping appears in shared data and how every service enforces it.>
