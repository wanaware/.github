<!-- docs-kit: nav="Development" -->
# {{NAME}}: Development & Testing

{{NAV}}

{{META}}

<!--
TEMPLATE: docs/08-development.md (repository level)
Do not rename, reorder, add or remove the numbered H2 headings. H3 subsections may be added freely.
If a section does not apply, keep the heading and write: _Not applicable._ followed by one sentence saying why.
Cover what applies to every service; each service's 08-development.md covers its own setup and tests.
-->

## 1. Prerequisites

| Tool | Version | Used for |
|---|---|---|
| <tool> | <version> | <purpose> |
| Python 3 | 3.9 or later | `docs/templates/docs_kit.py` (documentation check) |

## 2. Repository layout

```text
{{REPO_DIR}}/
├── .github/workflows/      CI/CD
├── docs/                   Platform documentation (this directory)
│   └── templates/          Documentation kit: templates, settings and checker
└── {{COMPONENTS_DIR}}/
    └── <service>/          One directory per service, each with its own docs/
```

## 3. Dependencies and private modules

<How services get private modules (for example github.com/wanaware/common/*) locally and in CI, and how
shared code is versioned.>

## 4. Building and testing

| Service | Build | Test | Runs in CI |
|---|---|---|---|
| <service> | <command> | <command> | <workflow / job> |

## 5. Branching, pull requests and CI

<Branches and environments, pull-request rules (title and description checks), and the CI gates a pull
request must pass.>

## 6. Documentation workflow

Documentation lives next to the code and changes in the same pull request. The rules are in the [documentation standards](10-documentation-standards.md). In short:

1. Find the document to update in the "Keeping these docs current" table of the service's `08-development.md`.
2. Keep the page anatomy: title, navigation bar, metadata line and numbered H2 headings from the templates in `docs/templates/`.
3. Update the metadata line's date and commit when you re-verify a document against the code.
4. Run `python3 docs/templates/docs_kit.py check` and check that Mermaid diagrams render.
