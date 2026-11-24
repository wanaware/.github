<!-- docs-kit: nav="Auth" -->
# {{NAME}}: Authentication & Authorization

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/04-authentication.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Explain the shared model once here; each service's 04-authentication.md covers only what is specific to it.
Never include secret values, tokens, or internal hostnames that are not already in the repository.
-->

## 1. Overview

| Concern | Mechanism |
|---|---|
| Identity providers | <e.g. Zitadel through user-auth-service> |
| Inbound authentication | <mechanism> |
| Authorization | <permission model> |
| Tenant resolution | <how the customer is determined> |
| Service-to-service | <credentials between services> |
| Secrets | <Vault / Keeper / mounted files> |

## 2. Callers

| Caller | Identity | Services it calls |
|---|---|---|
| <users, integrators, other services> | <token type> | <services> |

## 3. Inbound authentication

<!-- Required diagram: sequenceDiagram of a request being authenticated. -->

## 4. Authorization

<Permission model shared by the services: actions, roles, policy files, public and platform operations.>

## 5. Tenancy

<How every service resolves the customer and keeps tenants apart; how platform (tenant-less) calls work.>

## 6. Service-to-service authentication

<!-- Required diagram: sequenceDiagram of outbound credential acquisition and caching. -->

## 7. Secrets management

| Secret | Source | Used by | Notes |
|---|---|---|---|
| <name> | <Vault path / Keeper record / mounted file> | <services> | <rotation, caching> |

## 8. Security considerations

<Threats that span services, the controls that address them, and known gaps.>
