# Fabric API contracts used

Verified against Microsoft documentation on 2026-09-03.

## Environment

- [Manage Environment through public APIs](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-public-api)
- [Create Environment](https://learn.microsoft.com/en-us/rest/api/fabric/environment/items/create-environment)
- [Upload custom library](https://learn.microsoft.com/en-us/rest/api/fabric/environment/staging/upload-custom-library)
- [Update staging Spark compute](https://learn.microsoft.com/en-us/rest/api/fabric/environment/staging/update-spark-compute)
- [Publish Environment](https://learn.microsoft.com/en-us/rest/api/fabric/environment/items/publish-environment)
- [Environment definition paths](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/environment-definition)

Release reads/updates/publish set `beta=false`. The older upload contract was
retired after 2026-08-31. The dedicated current upload endpoint sends raw wheel
bytes and avoids Base64 expansion.

## Workspace, Lakehouse, Notebook, Pipeline

- [Create workspace](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/create-workspace)
- [List items](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/list-items)
- [Create Lakehouse](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/items/create-lakehouse)
- [Notebook definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/notebook-definition)
- [Run notebook](https://learn.microsoft.com/en-us/rest/api/fabric/notebook/background-jobs/run-on-demand-notebook)
- [NotebookUtils management](https://learn.microsoft.com/en-us/fabric/data-engineering/notebookutils/notebookutils-notebook-management)
- [DataPipeline definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/datapipeline-definition)
- [Run DataPipeline](https://learn.microsoft.com/en-us/rest/api/fabric/datapipeline/background-jobs/run-on-demand-execute)
- [Long-running operations](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation)
- [Workspace Spark settings](https://learn.microsoft.com/en-us/rest/api/fabric/spark/workspace-settings/update-spark-settings)

Typed create/update endpoints are used for Lakehouse, Notebook, Environment, and
DataPipeline. Item listing is used for idempotent discovery. Schema-enabled
Lakehouse creation is not requested because that creation payload remains
Preview.

## Intentional gaps

The public Notebook REST definition article says attached Environment metadata
is retained in notebook source, but does not publish its authoring schema as a
standalone REST property. The POC therefore uses documented NotebookUtils for
persistent attachment and the stable run API for the setup notebook.

The DataPipeline definition lists `properties.activities` and `description`,
plus documented `TridentNotebook.typeProperties.parameters`; it does not list a
top-level pipeline parameter collection. The generated pipeline uses only the
documented activity parameter property.

For `@pipeline().RunId`, the activity parameter uses `type: string`. Testing
showed that `type: Expression` evaluates the expression but can be rejected by
the notebook workload parameter converter. The string form is retained for
portable pipeline execution.
