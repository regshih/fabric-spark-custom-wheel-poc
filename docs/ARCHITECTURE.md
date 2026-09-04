# Architecture

```text
Microsoft Fabric workspace
|
+-- Data Factory pipeline
|   +-- 01 generate synthetic Delta input
|   +-- 02 import and optionally invoke the wheel on Spark workers
|   `-- 03 validate and persist PASS/FAIL evidence
|
+-- Reusable Fabric Environment
|   `-- one configured custom Python wheel
|
`-- Lakehouse / OneLake
    +-- custom_wheel_input
    +-- custom_wheel_output
    +-- custom_wheel_validation
    `-- custom_wheel_benchmark_results
```

## Package boundary

The automation knows only four package facts: the wheel path, distribution
name, Python import name, and an optional `module:callable` test hook. It never
guesses a vendor API.

Notebook 02 imports the module on the driver and inside `mapPartitions`. When
a callable is configured, it is resolved once per partition and invoked against
synthetic string values. When it is empty, the data path is an identity pass
and the POC asserts import availability only.

## Reproducible dependency model

The wheel is uploaded to a Fabric Environment and published before execution.
The notebooks do not use `%pip`, `!pip`, or runtime downloads. The setup
notebook persists the Environment and Lakehouse bindings through supported
NotebookUtils management.

The workspace-default Environment option is off because it has workspace-wide
impact. Explicit notebook attachment is sufficient for this POC.
