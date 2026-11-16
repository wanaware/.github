<!-- docs-kit: nav="Development" -->
# {{NAME}}: Development & Testing

{{NAV}}

{{META}}

<!--
TEMPLATE: {{DOCS_PATH}}/08-development.md
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
In a monorepo, repository-wide setup (private Go modules, CI gates) is in the repository-root
docs/08-development.md; link to it instead of repeating it.
-->

## 1. Prerequisites

<Tools and access needed to build, run and test this service.>

## 2. Repository layout

```text
{{SET_DIR}}/
├── cmd/            <entry points>
└── ...
```

## 3. Running locally

<Commands, docker compose, emulators, required local credentials.>

## 4. Testing

| Suite | Location | Command | Runs in CI |
|---|---|---|---|
| Unit | `./...` | `go test ./...` | <workflow / job> |

## 5. Tools and scripts

| Tool | Path | Purpose |
|---|---|---|
| <name> | <link to the script> | <purpose> |

## 6. Conventions

<Patterns specific to this service: error handling, logging, dependency wiring, configuration access,
code generation.>

## 7. Keeping these docs current

<!-- Map each code area to the document and section that describes it. Keep the documentation row. -->

| When you change… | Update… |
|---|---|
| <code area> | <document and section> |
| Any of these documents | Re-verify the page and update its "Last verified against source" line; run `python3 docs/templates/docs_kit.py check` from the repository root |
