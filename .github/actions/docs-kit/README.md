# Docs kit

> **This kit is the Asset Pipeline documentation standard, packaged for every repository.** The documents, templates, rules and checker all come from [`wanaware/asset-pipeline`](https://github.com/wanaware/asset-pipeline/tree/6241560553e4f30849ec018607f003ca6d320294/docs): its service templates in [`docs/templates/service/`](https://github.com/wanaware/asset-pipeline/tree/6241560553e4f30849ec018607f003ca6d320294/docs/templates/service), its rulebook [`docs/10-documentation-standards.md`](https://github.com/wanaware/asset-pipeline/blob/6241560553e4f30849ec018607f003ca6d320294/docs/10-documentation-standards.md) and its checker [`scripts/check-docs.py`](https://github.com/wanaware/asset-pipeline/blob/6241560553e4f30849ec018607f003ca6d320294/scripts/check-docs.py), taken from `dev` at [`6241560`](https://github.com/wanaware/asset-pipeline/commit/6241560553e4f30849ec018607f003ca6d320294) (2026-11-16). The kit generalizes them so that any repository, single-service or monorepo, can deploy the same documentation through CI. [Based on Asset Pipeline](#based-on-asset-pipeline) lists what each file comes from and what changed.

Every repository that adopts the kit gets the same documents, titles, numbered sections and diagram conventions as Asset Pipeline, with a check that keeps them that way. Asset Pipeline's own [`docs/`](https://github.com/wanaware/asset-pipeline/tree/6241560553e4f30849ec018607f003ca6d320294/docs) and `services/*/docs/` are the reference example of the standard applied.

| Piece | Path | Role |
|---|---|---|
| Templates | [`component/`](component/), [`platform/`](platform/), [`shared/`](shared/) | The document set, from Asset Pipeline. `component/` is a service's set (the whole repository's, in a single-service repository); `platform/` is the repository-level set of a monorepo; `shared/` holds the glossary and the documentation standards. |
| Kit script | [`docs_kit.py`](docs_kit.py) | Asset Pipeline's `check-docs.py`, generalized; also scaffolds documents from the templates. Standard library only, Python 3.9+. |
| Action | [`action.yml`](action.yml) | Runs the script in CI (`command: check` or `scaffold`) and renders Mermaid diagrams. |
| Check workflow | [`docs-check.yaml`](../../workflows/docs-check.yaml) | Reusable pull-request gate. |
| Scaffold workflow | [`docs-scaffold.yaml`](../../workflows/docs-scaffold.yaml) | Reusable workflow that deploys the documentation into a repository through a pull request. |
| Starter workflow | [`workflow-templates/documentation.yml`](../../../workflow-templates/documentation.yml) | What a repository adds to use both. Offered under Actions → New workflow for organization repositories. |
| Tests | [`tests/`](tests/), [`docs-kit-tests.yaml`](../../workflows/docs-kit-tests.yaml) | Unit tests and an end-to-end run of the action on a sample monorepo. |

## Based on Asset Pipeline

The standard was introduced in Asset Pipeline (`docs: add documentation standards, templates and platform docs scaffold`, 2026-11-14) and applied there to the platform and all eight services. This kit takes it from `dev` at [`6241560`](https://github.com/wanaware/asset-pipeline/commit/6241560553e4f30849ec018607f003ca6d320294). Each piece of the kit maps to a file in that commit:

| Kit | Comes from in Asset Pipeline | What changed |
|---|---|---|
| [`component/`](component/) `README.md`, `01-architecture.md` … `08-development.md` | [`docs/templates/service/`](https://github.com/wanaware/asset-pipeline/tree/6241560553e4f30849ec018607f003ca6d320294/docs/templates/service), the same nine files | Same sections, guidance and required diagrams. Generalized: "3. Position in the pipeline" is "3. Position in the platform", the "Pipeline stage" row is "Platform role", and Asset-Pipeline-specific wording and paths are generic. The kit writes the title, navigation bar and metadata line instead of authors copying them, and placeholders sit outside backticks so the check can find them. |
| [`platform/`](platform/) `README.md`, `01-architecture.md` … `08-development.md` | The repository-level documents in [`docs/`](https://github.com/wanaware/asset-pipeline/tree/6241560553e4f30849ec018607f003ca6d320294/docs). Asset Pipeline has no template for these; the kit's follow their sections | Same sections in `01`, `03`, `04`, `06` and `07`. Generic names where Asset Pipeline's are specific to it: "2. The pipeline at a glance" is "2. System at a glance"; "2. Canonical asset model", "3. Data lineage" and "4. Configuration model" are "2. Core domain model", "3. Data flow and lineage" and "4. Shared schemas and contracts"; "4. Platform APIs the pipeline calls" is "4. External APIs"; "3. Working with private Go modules" is "3. Dependencies and private modules", and "6. Syncing from the standalone repositories" is dropped. |
| [`shared/09-glossary.md`](shared/09-glossary.md) | [`docs/09-glossary.md`](https://github.com/wanaware/asset-pipeline/blob/6241560553e4f30849ec018607f003ca6d320294/docs/09-glossary.md) | Same layout (one table of terms), without Asset Pipeline's terms. |
| [`shared/10-documentation-standards.md`](shared/10-documentation-standards.md) | [`docs/10-documentation-standards.md`](https://github.com/wanaware/asset-pipeline/blob/6241560553e4f30849ec018607f003ca6d320294/docs/10-documentation-standards.md) | The same rules: principles, layout, standard document set, page anatomy, writing conventions, diagram conventions, earlier documents, keeping documentation current. Examples use neutral names, the layout section matches the repository (single or monorepo), and §9 describes the kit. Generated into each repository, where it says that it comes from Asset Pipeline. |
| [`docs_kit.py`](docs_kit.py) | [`scripts/check-docs.py`](https://github.com/wanaware/asset-pipeline/blob/6241560553e4f30849ec018607f003ca6d320294/scripts/check-docs.py) | The same structure and link checks, with its CommonMark fence handling unchanged. Settings come from `docs/templates/docs-kit.json` instead of fixed `services/` paths. Added: scaffolding, placeholder and guidance-comment detection, diagram-convention checks, service-linking and reference-link checks. |
| [`tests/test_docs_kit.py`](tests/test_docs_kit.py) | [`scripts/test_check_docs.py`](https://github.com/wanaware/asset-pipeline/blob/6241560553e4f30849ec018607f003ca6d320294/scripts/test_check_docs.py) | Its fence tests are ported with the same cases (`OutsideFencesTest`); the other tests are new. |
| Diagram rendering in [`action.yml`](action.yml) | The Mermaid CLI command in §8.1 of the standards (`@mermaid-js/mermaid-cli@11.12.0`) | The same tool and version, run in CI on the documents a pull request changes. |

Checked against Asset Pipeline at that commit (83 documents, 3,251 relative links), the kit reports only the headings it generalized, listed above: "Position in the pipeline" in the eight service READMEs, and four repository-level documents. Asset Pipeline can adopt the kit by renaming those headings, or keep its own by editing its copy of the templates after the scaffold.

Asset Pipeline still has its own copies (`docs/templates/service/`, `scripts/check-docs.py`). Change the standard here from now on, so that every repository, Asset Pipeline included once it adopts the kit, gets the change through a refresh.

## Adopting it in a repository

1. Add `.github/workflows/documentation.yml` from the starter workflow (Actions → New workflow → Documentation, or copy [the file](../../../workflow-templates/documentation.yml)) in a pull request into `dev`. Until the repository has adopted the documentation, the check only warns.
2. Merging it runs the scaffold, which opens a pull request (`chore/standard-docs`) with:
   - `docs/templates/`: the templates, a copy of `docs_kit.py`, and `docs-kit.json` with the repository's settings;
   - every standard document, rendered from the templates with the repository's name, navigation bar and metadata line filled in;
   - `docs/10-documentation-standards.md`, the rulebook, generated for the repository's layout.
3. Fill the documents in from the code on that branch: replace every `<placeholder>`, delete the guidance comments, set each page's "Last verified against source" date and commit. `python3 docs/templates/docs_kit.py check` lists what is left. To merge the skeleton first and fill it in over several pull requests, set `allow_placeholders: true` on the check job until the documents are complete.

The scaffold detects the layout: a repository whose `services/` directory has two or more subdirectories is a **monorepo** (repository-level `docs/` from `platform/`, plus `services/<service>/docs/` from `component/` for each service); anything else is **single** (one `docs/` from `component/`). Override it, the services directory, the title name or the branch named in metadata lines with the workflow inputs or in `docs/templates/docs-kit.json`.

```json
{
  "schema": 1,
  "name": "Asset Pipeline",
  "repository": "wanaware/asset-pipeline",
  "layout": "monorepo",
  "components_dir": "services",
  "exclude": [],
  "branch": "dev"
}
```

`exclude` lists directories under the services directory that are not services.

## What the check enforces

| Check | Rule |
|---|---|
| `MISSING` | Every standard document of every set exists. |
| `TITLE`, `NAV`, `META` | The title (`# <name>: <suffix>`), navigation bar and metadata line match the template; the metadata line has a real date. |
| `HEADINGS` | The H2 headings are exactly the template's, in order (not for the glossary and standards). |
| `PLACEHOLDER` | No `<placeholder>` from the template, guidance comment, `TEMPLATE:` marker or unset date or commit is left. Warnings with `allow_placeholders`. |
| `LINK`, `ANCHOR` | Relative links, reference definitions and `#anchors` in the standard documents resolve, as GitHub resolves them: `/path` from the repository root, anchors to `#` and underlined (Setext) headings, nothing inside code (fenced or indented) or HTML comments. |
| `MERMAID` | Diagrams, block quotes included, use the allowed types, `sequenceDiagram` starts with `autonumber`, and there are no `%%{init}%%` directives, `click`, `style` or colours. In CI, diagrams in changed documents must also render with the Mermaid CLI. |
| `UNLINKED` | In a monorepo, `docs/README.md` links every service's `docs/README.md`. |
| `README`, `STALE`, `KIT` | Warnings and notices: a README that does not link its documentation, a hand-edited generated file, a repository copy of the kit that is older than this one. |

## How the pieces fit

Templates are Markdown with a front-matter comment (`<!-- docs-kit: nav="Data model" -->`; `managed` for generated documents, `free-headings` for documents without a fixed H2 list), `{{TOKENS}}` that the kit fills in (`NAME`, `NAV`, `META`, `ROOT`, `DOCS_ROOT`, `DOCS_PATH`, `SET_DIR`, `REPO`, `REPO_DIR`, `BRANCH`, `COMPONENTS_DIR`, `SERVICE_TABLE`, `SERVICE_MATRIX`, `KIT_HOME`), and `{{#single}}…{{/single}}` / `{{#monorepo}}…{{/monorepo}}` blocks, on their own lines or within one line, for text that depends on the layout.

The scaffold copies the templates and the script into the repository's `docs/templates/`, and the check compares documents with **that copy**. A change to the kit therefore never breaks a repository's pull requests: it reaches the repository when the scaffold runs with `refresh`, as a pull request that shows the change. The check in CI runs this kit's script against the repository's templates and reports a notice when the repository's copy is out of date. A repository can tailor a template (for example to keep Asset Pipeline's own repository-level headings) by editing its copy; a refresh replaces the copy again, and the pull request's diff shows what to keep.

The scaffold never overwrites a document that exists. `refresh` replaces only the kit-managed files: `docs/templates/` and `docs/10-documentation-standards.md`.

## Changing the standard

Change the templates, `shared/10-documentation-standards.md` and `docs_kit.py` here, then run the tests:

```bash
python3 -m unittest discover -s .github/actions/docs-kit/tests -v
```

Try a change on a scratch repository with the script from this directory:

```bash
python3 .github/actions/docs-kit/docs_kit.py --root /path/to/repo scaffold
python3 .github/actions/docs-kit/docs_kit.py --root /path/to/repo check --allow-placeholders
```

Repositories pick the change up when it reaches `prod` and their Documentation workflow runs with `refresh`. Renaming or adding an H2 heading in `component/` or `platform/` makes every refreshed repository's documents fail the check until they follow, so say so in the pull request.
