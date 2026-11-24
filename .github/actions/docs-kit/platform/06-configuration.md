<!-- docs-kit: nav="Configuration" -->
# {{NAME}}: Configuration

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/06-configuration.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Explain the shared conventions here; each service's 06-configuration.md lists its variables in full.
-->

## 1. Overview

<!-- Required diagram: flowchart of the configuration sources (Keeper / ESO, Vault, config registry, files)
and which services read each. -->

<Where configuration comes from and how it reaches the services.>

## 2. Shared conventions

<Variable naming, variables every service reads (NATS, Vault, tracing), and how defaults are chosen.>

## 3. Per-service reference

| Service | Configuration |
|---|---|
| <service> | <link to the service's 06-configuration.md> |

## 4. Dynamic configuration

<Configuration fetched or reloaded at runtime and how changes propagate between services.>

## 5. Environments

<How development, staging and production differ, and where deployed values are managed.>

## 6. Startup validation

<What every service validates at boot and what happens when a value is missing or invalid.>
