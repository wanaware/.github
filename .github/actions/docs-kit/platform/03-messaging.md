<!-- docs-kit: nav="Messaging" -->
# {{NAME}}: Messaging

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/03-messaging.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Catalog every stream and bucket once here; each service's 03-messaging.md documents its own payloads.
-->

## 1. Overview

<!-- Required diagram: flowchart LR of every stream and KV bucket (hexagon shape) between the services. -->

<How services hand work to each other: transport, claim-check pattern, ownership of streams.>

## 2. Messaging infrastructure

<NATS JetStream clusters, TLS and NKey authentication, who creates and manages streams, other transports.>

## 3. Stream catalog

| Stream | Subjects | Producer | Consumers | Documented in |
|---|---|---|---|---|
| `STREAM` | `subject` | <service> | <services> | <link to the producer's 03-messaging.md> |

## 4. Key-value buckets

| Bucket | Key format | Owner | Readers | Documented in |
|---|---|---|---|---|
| `bucket` | <key format> | <service> | <services> | <link> |

## 5. Conventions

<Naming of streams, subjects and consumers; acknowledgement and redelivery settings; headers, correlation and
tracing; payload versioning.>

## 6. Participants outside this repository

| Service | Repository | Publishes | Consumes |
|---|---|---|---|
| <service> | <repository> | <subjects> | <subjects> |
