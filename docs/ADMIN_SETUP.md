# Administrator setup and cost guardrails

## Required access

- Azure CLI can obtain a token for `https://api.fabric.microsoft.com`.
- Contributor or higher on an existing target workspace.
- Workspace Admin when creating a workspace or assigning capacity.
- Workspace Admin if enabling a workspace-default Environment.

Use an existing active Fabric capacity. This repository never creates, resumes,
pauses, resizes, or deletes capacity. Confirm the capacity region matches the
workspace because Fabric items cannot be moved across regions through capacity
assignment.

## Authentication

Interactive development uses `AzureCliCredential` first, then the standard
Azure Identity credential chain. Do not put client secrets, access tokens,
connection strings, tenant-specific IDs, or credentials in tracked files.

For CI or service automation, prefer workload identity or managed identity. If
a service principal is required, inject its values through the CI secret store.

## Cost controls

Provisioning is separate from execution. Use `--provision-only` to inspect
items before starting Spark. The benchmark profile is blocked unless both
`SCALE_PROFILE=benchmark` and `ENABLE_SCALE_TEST=true` are explicit.

## Workspace default

Individual notebook attachment is the default. Set
`SET_WORKSPACE_DEFAULT_ENVIRONMENT=true` only in a dedicated workspace after
reviewing the workspace-wide effect. Microsoft notes that updating a default
Environment requires workspace admin permissions.
