<!-- docs-kit: nav="Operations" -->
# {{NAME}}: Operations

{{NAV}}

{{META}}

<!--
TEMPLATE: {{DOCS_PATH}}/07-operations.md
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Values that live outside this repository (replica counts, resource limits, alerts) are managed in
wanaware-infrastructure; say so rather than guessing them.
-->

## 1. Overview

| Item | Value |
|---|---|
| Container image(s) | <image path(s)> |
| Dockerfile(s) | <link to each Dockerfile, e.g. ../Dockerfile> |
| Kubernetes | <namespace, Deployment(s), CronJob(s)> |
| CI/CD workflow(s) | <link to each workflow under {{ROOT}}/.github/workflows/> |
| Environments | `dev` → development, `stage` → staging, `prod` → production |

## 2. Build and deployment

<!-- Required diagram: flowchart from merge/push through GitHub Actions, image build and registry, to the
GKE workload. -->

## 3. Runtime topology

<!-- Required diagram: flowchart of the running workload: containers, ports, mounted volumes (Vault token,
NATS CA / NKey seed), and the connections it opens. -->

## 4. Observability

### 4.1 Logging

### 4.2 Tracing

### 4.3 Metrics

### 4.4 Health checks

## 5. Scaling and capacity

<Scaling knobs (workers, batch sizes, MaxAckPending sizing), resource hot spots, and limits.>

## 6. Runbooks

<!-- One H3 per common incident, using the same four bold labels each time. -->

### 6.1 <Symptom>

**Symptoms:** <what operators see>
**Likely causes:** <causes>
**Diagnosis:** <commands, logs, queries>
**Remediation:** <steps>

## 7. Data repair and recovery

<Replays, backfills, operator CLIs, migrations, and how to recover from partial failures.>
