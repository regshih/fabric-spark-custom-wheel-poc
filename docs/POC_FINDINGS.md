# Validation scope and limitations

This public repository contains no tenant-specific execution record. Each user
produces local, ignored evidence under `results/` and in the POC Lakehouse.

## Sanitized reference validation

On 2026-09-04, maintainers ran the sample path on Fabric Runtime 1.3 using a
paid F2 capacity. The pipeline completed with 10,000 input and output rows,
four logical executor partitions, successful driver/executor imports, and all
18 validation checks passing. The measured transformation duration was 11.89
seconds; this is functional evidence, not a portable performance benchmark.

A successful smoke run proves:

- the Environment published the configured wheel;
- the configured module imported on the Spark driver;
- the module imported in every executor probe partition;
- an optional callable ran on synthetic inputs when configured;
- distributed output and validation tables were written; and
- pipeline activities completed in dependency order.

It does not prove:

- package correctness beyond the configured test hook;
- security, privacy, encryption, or regulatory properties;
- compatibility with untested inputs or scale;
- multi-host execution merely because multiple logical partitions ran;
- production throughput or cost; or
- licensing rights for a third-party wheel.

Run the benchmark profile only with explicit approval and an agreed capacity,
dataset, success threshold, and cost limit.
