# .github
This repo contains the reusable workflows and templates

## Documentation kit

The standard documentation set for WanAware repositories (overview, architecture, data model, messaging, authentication, API, configuration, operations and development guides, a glossary and the documentation standards) is **the one used in [Asset Pipeline](https://github.com/wanaware/asset-pipeline/tree/6241560553e4f30849ec018607f003ca6d320294/docs)**. Its templates, rules and checker are packaged in [`.github/actions/docs-kit`](.github/actions/docs-kit/README.md) so that any repository can deploy the same documentation; [what comes from Asset Pipeline](.github/actions/docs-kit/README.md#based-on-asset-pipeline) lists the source of each file. The kit comes with:

- [`docs-scaffold.yaml`](.github/workflows/docs-scaffold.yaml): deploys the documentation into a repository through a pull request;
- [`docs-check.yaml`](.github/workflows/docs-check.yaml): checks it on every pull request;
- [`workflow-templates/documentation.yml`](workflow-templates/documentation.yml): the starter workflow a repository adds to use both.
