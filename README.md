# .github
This repo contains the reusable workflows and templates

## Documentation kit

The standard documentation set that every WanAware repository uses (overview, architecture, data model, messaging, authentication, API, configuration, operations and development guides, a glossary and the documentation standards) lives in [`.github/actions/docs-kit`](.github/actions/docs-kit/README.md), with:

- [`docs-scaffold.yaml`](.github/workflows/docs-scaffold.yaml): deploys the documentation into a repository through a pull request;
- [`docs-check.yaml`](.github/workflows/docs-check.yaml): checks it on every pull request;
- [`workflow-templates/documentation.yml`](workflow-templates/documentation.yml): the starter workflow a repository adds to use both.
