# Docs kit

The WanAware standard documentation set, packaged so that any repository can adopt it through CI. It is the structure that [`wanaware/asset-pipeline`](https://github.com/wanaware/asset-pipeline/tree/dev/docs) introduced, generalized for every repository: the same documents, titles, numbered sections and diagram conventions everywhere, with a check that keeps them that way.

| Piece | Path | Role |
|---|---|---|
| Templates | [`component/`](component/), [`platform/`](platform/), [`shared/`](shared/) | The document set. `component/` is a service's set (the whole repository's, in a single-service repository); `platform/` is the repository-level set of a monorepo; `shared/` holds the glossary and the documentation standards. |
| Kit script | [`docs_kit.py`](docs_kit.py) | Scaffolds documents from the templates and checks them. Standard library only, Python 3.9+. |
| Action | [`action.yml`](action.yml) | Runs the script in CI (`command: check` or `scaffold`) and renders Mermaid diagrams. |
| Check workflow | [`docs-check.yaml`](../../workflows/docs-check.yaml) | Reusable pull-request gate. |
| Scaffold workflow | [`docs-scaffold.yaml`](../../workflows/docs-scaffold.yaml) | Reusable workflow that deploys the documentation into a repository through a pull request. |
| Starter workflow | [`workflow-templates/documentation.yml`](../../../workflow-templates/documentation.yml) | What a repository adds to use both. Offered under Actions → New workflow for organization repositories. |
| Tests | [`tests/`](tests/), [`docs-kit-tests.yaml`](../../workflows/docs-kit-tests.yaml) | Unit tests and an end-to-end run of the action on a sample monorepo. |

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
| `LINK`, `ANCHOR` | Relative links and `#anchors` in the standard documents resolve. |
| `MERMAID` | Diagrams use the allowed types, `sequenceDiagram` starts with `autonumber`, and there are no `%%{init}%%` directives, `click`, `style` or colours. In CI, diagrams in changed documents must also render with the Mermaid CLI. |
| `UNLINKED` | In a monorepo, `docs/README.md` links every service's `docs/README.md`. |
| `README`, `STALE`, `KIT` | Warnings and notices: a README that does not link its documentation, a hand-edited generated file, a repository copy of the kit that is older than this one. |

On the asset-pipeline monorepo (83 documents, 3,252 links) the check reports only the headings this kit generalized: "Position in the pipeline" became "Position in the platform", and a few repository-level section names became generic. Asset-pipeline can rename those headings or keep its own by editing its copy of the templates.

## How the pieces fit

Templates are Markdown with a front-matter comment (`<!-- docs-kit: nav="Data model" -->`; `managed` for generated documents, `free-headings` for documents without a fixed H2 list), `{{TOKENS}}` that the kit fills in (`NAME`, `NAV`, `META`, `ROOT`, `DOCS_ROOT`, `DOCS_PATH`, `SET_DIR`, `REPO`, `REPO_DIR`, `BRANCH`, `COMPONENTS_DIR`, `SERVICE_TABLE`, `SERVICE_MATRIX`, `KIT_HOME`), and `{{#single}}…{{/single}}` / `{{#monorepo}}…{{/monorepo}}` blocks, on their own lines or within one line, for text that depends on the layout.

The scaffold copies the templates and the script into the repository's `docs/templates/`, and the check compares documents with **that copy**. A change to the kit therefore never breaks a repository's pull requests: it reaches the repository when the scaffold runs with `refresh`, as a pull request that shows the change. The check in CI runs this kit's script against the repository's templates and reports a notice when the repository's copy is out of date. A repository can tailor a template (for example asset-pipeline's platform headings) by editing its copy; a refresh replaces the copy again, and the pull request's diff shows what to keep.

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
