<!-- docs-kit: nav="Operations" -->
# {{NAME}}: Operations

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/07-operations.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Values that live outside this repository (replica counts, resource limits, alerts) are managed in
wanaware-infrastructure; say so rather than guessing them.
-->

## 1. Overview

| Item | Value |
|---|---|
| Runtime platform | <e.g. GKE, one namespace per service> |
| Environments | `dev` → development, `stage` → staging, `prod` → production |
| CI/CD | <workflows and runners> |
| Deployment mechanism | <e.g. the shared wanaware/.github deployment.yaml reusable workflow> |
| Runtime configuration | <Keeper / ESO, Vault, mounted files> |
| Infrastructure as code | <where namespaces, workloads and alerts are defined> |

## 2. CI/CD

<!-- Required diagram: flowchart from merge through GitHub Actions and image build to the workloads.
List every deployable with its workflow, image and Kubernetes workload, and every pull-request gate. -->

## 3. Runtime platform

<!-- Required diagram: flowchart of the running services, their namespaces and shared infrastructure. -->

## 4. Observability

<Logging, tracing and metrics shared by every service, and where to find them.>

## 5. Scaling and capacity

<Scaling knobs shared by the services, hot spots and limits.>

## 6. Incident response

<!-- One H3 per incident that spans services, with the labels Symptoms, Likely causes, Diagnosis, Remediation.
Link to the runbooks in each service's 07-operations.md. -->

## 7. Data repair and recovery

<Replays, backfills and recovery procedures that involve more than one service.>
