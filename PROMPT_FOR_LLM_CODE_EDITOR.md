# Prompt for an LLM code editor

Copy the prompt below, replace the bracketed values, and give it to an LLM code
editor that has access to a clone of this repository.

---

You are working in a clone of:

https://github.com/regshih/fabric-spark-custom-wheel-poc

Your goal is to use this repository to implement and validate a Microsoft Fabric
Spark proof of concept for the following Python wheel:

- Wheel path: `[LOCAL_WHEEL_PATH]`
- Python import name: `[IMPORT_NAME]`
- Distribution name from wheel metadata: `[DISTRIBUTION_NAME]`
- Optional test callable in `module:attribute` form: `[CALLABLE_OR_EMPTY]`
- Existing Fabric workspace name or desired isolated name: `[WORKSPACE_NAME]`
- Existing workspace ID, if known: `[WORKSPACE_ID_OR_EMPTY]`
- Existing active Fabric capacity ID, required only when creating a workspace:
  `[CAPACITY_ID_OR_EMPTY]`
- Desired Spark runtime: `[RUNTIME_VERSION]`

Work autonomously, but preserve these guardrails:

1. Read `README.md`, `docs/ARCHITECTURE.md`,
   `docs/CUSTOM_WHEEL_GUIDE.md`, `docs/API_CONTRACTS.md`, and
   `SECURITY.md` before changing code.
2. Do not commit or print credentials, access tokens, connection strings,
   tenant-specific identifiers, customer data, proprietary source, or the wheel.
3. Keep the wheel under the Git-ignored `vendor/wheels/` directory or reference
   an external local path.
4. Do not invent package APIs. Inspect wheel metadata first. Use import-only
   validation if authoritative documentation for a callable is unavailable.
5. Use current stable Microsoft Fabric APIs. Verify any contract that may have
   changed against official Microsoft documentation.
6. Do not create, resume, pause, resize, reassign, or delete capacity without my
   explicit approval. Do not enable workspace-default Environment settings
   without approval.
7. Use synthetic data only. Start with the smoke profile. Do not run the medium
   or benchmark profile without explicit approval.
8. Preserve idempotency and dry-run cleanup behavior. Do not delete the workspace
   or capacity.
9. Use Fabric Environment publishing for dependencies. Do not add `%pip`,
   `!pip`, or runtime package downloads to workload notebooks.
10. Keep all public-repository checks passing.

Implementation workflow:

1. Confirm Azure CLI authentication and target tenant/subscription without
   exposing tokens.
2. Copy `.env.example` to the ignored `.env` and configure:
   `WHEEL_SOURCE=custom`, `WHEEL_PATH`, `WHEEL_IMPORT_NAME`,
   `WHEEL_DISTRIBUTION_NAME`, and `WHEEL_TEST_CALLABLE`.
3. Run metadata inspection and preflight. Check filename, size, SHA-256,
   `Requires-Python`, dependencies, platform tags, distribution name, and
   top-level modules against the selected Fabric runtime.
4. If the package requires a more complex API than the optional scalar callable,
   modify only the package-specific portion of
   `notebooks/02_Validate_Custom_Wheel.py`, based on authoritative docs. Keep
   driver and executor probes, bounded evidence collection, null behavior, and
   partition-local initialization.
5. Run local lint, unit tests, compilation, and sample-wheel build.
6. Provision the Environment and Fabric items without starting Spark. Review the
   created/updated item list.
7. With explicit execution authorization, run the smoke pipeline and collect
   Lakehouse evidence.
8. Verify published library state, driver import, executor imports, Spark
   application ID, row counts, validation checks, and pipeline activity order.
9. Redact tenant, capacity, workspace, item, host, application, and run IDs from
   anything intended for source control or external sharing.
10. Update public-safe documentation with what was tested, limitations, and exact
    reproduction commands. Never claim more than the evidence supports.

Definition of done:

- The configured wheel is published in the target Fabric Environment.
- The configured import succeeds on the driver and all executor probe
  partitions.
- The optional callable succeeds on synthetic inputs, or the result is clearly
  labeled import-only.
- The smoke pipeline completes and validation passes.
- Local tests and lint pass.
- `git diff --check` passes.
- Secret/sensitive-data scans find no credentials or tenant-specific run
  artifacts in tracked files.
- The final report names remaining compatibility, licensing, networking,
  performance, and security limitations.

Before executing any billable Spark work, summarize the target workspace,
capacity, runtime, wheel metadata, and expected scope, then proceed only within
the authorization above.

---
