# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {"name": "synapse_pyspark"},
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "__LAKEHOUSE_ID__",
# META       "default_lakehouse_name": "__LAKEHOUSE_NAME__",
# META       "default_lakehouse_workspace_id": "__WORKSPACE_ID__"
# META     },
# META     "environment": {
# META       "environmentId": "__ENVIRONMENT_ID__",
# META       "workspaceId": "__WORKSPACE_ID__"
# META     }
# META   }
# META }

# PARAMETERS CELL ********************

run_id = "manual"
scale_profile = "smoke"
wheel_source = "sample"
wheel_import_name = "fabric_custom_wheel_sample"
wheel_distribution_name = "fabric-custom-wheel-sample"
wheel_test_callable = "fabric_custom_wheel_sample:transform"
enable_scale_test = False

# METADATA ********************

# META {"language": "python", "language_group": "synapse_pyspark"}

# CELL ********************

import json
from datetime import datetime, timezone

from pyspark.sql import functions as F

input_df = spark.table("custom_wheel_input")
output_df = spark.table("custom_wheel_output")
latest_benchmark = (
    spark.table("custom_wheel_benchmark_results")
    .where(F.col("run_id") == run_id)
    .orderBy(F.col("timestamp_utc").desc())
    .limit(1)
    .collect()
)
checks = []


def record(name, passed, detail):
    checks.append({
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "check_name": name,
        "status": "PASS" if passed else "FAIL",
        "detail": str(detail),
    })


input_count = input_df.count()
output_count = output_df.count()
columns = ["ssn", "email", "phone", "account_number", "routing_number"]
record("row_count", input_count == output_count, f"input={input_count}, output={output_count}")
record("required_fields", all(f"{column}_result" in output_df.columns for column in columns), output_df.columns)

joined = input_df.alias("i").join(output_df.alias("o"), "transaction_id", "inner")
for column in columns:
    result_column = f"{column}_result"
    null_mismatches = joined.where(
        (F.col(f"i.{column}").isNull() & F.col(f"o.{result_column}").isNotNull())
        | (F.col(f"i.{column}").isNotNull() & F.col(f"o.{result_column}").isNull())
    ).limit(1).count()
    record(f"{column}_null_behavior", null_mismatches == 0, f"mismatches={null_mismatches}")

    inconsistent = (
        joined.where(F.col(f"i.{column}").isNotNull())
        .groupBy(F.col(f"i.{column}").alias("source"))
        .agg(F.countDistinct(F.col(f"o.{result_column}")).alias("result_count"))
        .where(F.col("result_count") != 1)
        .limit(1)
        .count()
    )
    record(f"{column}_deterministic", inconsistent == 0, f"inconsistent_sources={inconsistent}")

partition_count = output_df.select("_partition_id").distinct().count()
record(
    "distributed_partitions",
    partition_count >= min(2, max(1, input_df.rdd.getNumPartitions())),
    f"logical_partitions_executed={partition_count}",
)
record(
    "wheel_source",
    output_df.where(F.col("_wheel_source") != wheel_source).limit(1).count() == 0,
    wheel_source,
)

if latest_benchmark:
    evidence = latest_benchmark[0].asDict(recursive=True)
    record("driver_import", bool(evidence.get("package_version")), evidence.get("package_version"))
    record("executor_import", bool(evidence.get("executor_import_ok")), evidence.get("executor_probe_json"))
    record("spark_application_id", bool(evidence.get("spark_application_id")), evidence.get("spark_application_id"))
    if wheel_test_callable:
        record("callable_configured", bool(evidence.get("test_callable")), evidence.get("test_callable"))
else:
    record("driver_import", False, "no benchmark evidence row")
    record("executor_import", False, "no benchmark evidence row")
    record("spark_application_id", False, "no benchmark evidence row")

overall = all(check["status"] == "PASS" for check in checks)
spark.createDataFrame(checks).write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable("custom_wheel_validation")
result = {"run_id": run_id, "validation": "PASS" if overall else "FAIL", "checks": checks}
print(json.dumps(result, indent=2))
if not overall:
    raise RuntimeError(json.dumps(result))
try:
    notebookutils.notebook.exit(json.dumps(result))
except NameError:
    pass

# METADATA ********************

# META {"language": "python", "language_group": "synapse_pyspark"}
