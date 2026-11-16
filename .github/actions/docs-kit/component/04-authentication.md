<!-- docs-kit: nav="Auth" -->
# {{NAME}}: Authentication & Authorization

{{NAV}}

{{META}}

<!--
TEMPLATE: {{DOCS_PATH}}/04-authentication.md
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Describe only what is specific to this service. Where a platform-wide mechanism (user-auth-service, Zitadel,
Vault, common/auth) is documented elsewhere (the repository-root docs/04-authentication.md in a monorepo),
link to it rather than repeating it.
Never include secret values, tokens, or internal hostnames that are not already in the repository.
-->

## 1. Overview

| Concern | Mechanism |
|---|---|
| Inbound authentication | <how callers are identified, or None> |
| Authorization | <permission model> |
| Tenant resolution | <how the customer is determined> |
| Outbound authentication | <credentials used for calls this service makes> |
| Secrets | <where secrets come from> |

## 2. Inbound authentication

<!-- Required diagram (when the service accepts requests): sequenceDiagram of a request being authenticated. -->

## 3. Authorization

<Permission model: OPA policy / permissions file, roles, public and platform operations. Include an
operation → required action / role table.>

## 4. Tenancy

<How the customer is resolved (token claims, Customer-Id header rules, delegation credentials), and how
tenant-less (platform) calls are handled.>

## 5. Outbound authentication

| Target | Credential | Tenant scope | Implementation |
|---|---|---|---|
| <service> | <credential type> | <customer / none> | <link to the implementation> |

<!-- Required diagram (when the service makes authenticated calls): sequenceDiagram of credential acquisition
and caching. -->

## 6. Secrets management

| Secret | Source | Used for | Notes |
|---|---|---|---|
| <name> | <Vault path / Keeper env / mounted file> | <purpose> | <rotation, caching> |

## 7. Security considerations

<Threats specific to this service, the controls that address them, and known gaps.>
