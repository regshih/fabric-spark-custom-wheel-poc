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

import importlib
import json
import time
from datetime import datetime, timezone
from importlib.metadata import version

from pyspark.sql import types as T


def resolve_callable(spec):
    if not spec:
        return None
    module_name, separator, attribute_path = spec.partition(":")
    if not separator or not module_name or not attribute_path:
        raise ValueError("wheel_test_callable must use 'module:attribute' syntax")
    value = importlib.import_module(module_name)
    for attribute in attribute_path.split("."):
        value = getattr(value, attribute)
    if not callable(value):
        raise TypeError(f"Configured object is not callable: {spec}")
    return value


driver_module = importlib.import_module(wheel_import_name)
package_version = version(wheel_distribution_name)
driver_callable = resolve_callable(wheel_test_callable)
driver_sample = driver_callable("driver-probe") if driver_callable else None
print({
    "driver_import": True,
    "module": wheel_import_name,
    "module_file": getattr(driver_module, "__file__", None),
    "distribution": wheel_distribution_name,
    "version": package_version,
    "callable": wheel_test_callable or None,
    "sample": str(driver_sample) if driver_sample is not None else None,
})

input_df = spark.table("custom_wheel_input")
input_rows = input_df.count()
input_partitions = input_df.rdd.getNumPartitions()
probe_partitions = max(2, min(input_partitions, 16))


def probe_partition(_rows):
    import importlib as _importlib
    import os as _os
    import socket as _socket
    from importlib.metadata import version as _version
    from pyspark import TaskContext as _TaskContext

    context = _TaskContext.get()
    try:
        module = _importlib.import_module(wheel_import_name)
        test_callable = None
        sample = None
        if wheel_test_callable:
            module_name, _, attribute_path = wheel_test_callable.partition(":")
            test_callable = _importlib.import_module(module_name)
            for attribute in attribute_path.split("."):
                test_callable = getattr(test_callable, attribute)
            sample = test_callable("executor-probe")
        yield {
            "ok": True,
            "partition_id": context.partitionId(),
            "attempt": context.attemptNumber(),
            "host": _socket.gethostname(),
            "python_worker_pid": _os.getpid(),
            "version": _version(wheel_distribution_name),
            "module_file": getattr(module, "__file__", None),
            "sample": str(sample) if sample is not None else None,
            "error": None,
        }
    except Exception as exc:
        yield {
            "ok": False,
            "partition_id": context.partitionId(),
            "attempt": context.attemptNumber(),
            "host": _socket.gethostname(),
            "python_worker_pid": _os.getpid(),
            "version": None,
            "module_file": None,
            "sample": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


executor_probe = (
    spark.sparkContext.parallelize(range(probe_partitions), probe_partitions)
    .mapPartitions(probe_partition)
    .collect()
)
if len(executor_probe) != probe_partitions or not all(item["ok"] for item in executor_probe):
    raise RuntimeError(f"Custom wheel executor import failed: {executor_probe}")

transformed_columns = ["ssn", "email", "phone", "account_number", "routing_number"]
plain_columns = [name for name in input_df.columns if name not in transformed_columns]
output_schema = T.StructType(
    [input_df.schema[name] for name in plain_columns]
    + [T.StructField(f"{name}_result", T.StringType(), True) for name in transformed_columns]
    + [
        T.StructField("_wheel_source", T.StringType(), False),
        T.StructField("_partition_id", T.IntegerType(), False),
        T.StructField("_run_id", T.StringType(), False),
    ]
)


def transform_partition(rows):
    import importlib as _importlib
    from pyspark import TaskContext as _TaskContext

    test_callable = None
    if wheel_test_callable:
        module_name, _, attribute_path = wheel_test_callable.partition(":")
        test_callable = _importlib.import_module(module_name)
        for attribute in attribute_path.split("."):
            test_callable = getattr(test_callable, attribute)
    else:
        _importlib.import_module(wheel_import_name)
    partition_id = _TaskContext.get().partitionId()
    for row in rows:
        source = row.asDict(recursive=True)
        result = {name: source[name] for name in plain_columns}
        for name in transformed_columns:
            value = source[name]
            transformed = test_callable(value) if test_callable else value
            result[f"{name}_result"] = None if transformed is None else str(transformed)
        result["_wheel_source"] = wheel_source
        result["_partition_id"] = partition_id
        result["_run_id"] = run_id
        yield result


started = time.perf_counter()
output_df = spark.createDataFrame(input_df.rdd.mapPartitions(transform_partition), schema=output_schema)
output_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("custom_wheel_output")
output_rows = spark.table("custom_wheel_output").count()
duration_seconds = time.perf_counter() - started

runtime_context = {}
try:
    context = notebookutils.runtime.context
    for key in ["environmentId", "environmentWorkspaceId", "activityId", "clusterId", "poolName"]:
        runtime_context[key] = context.get(key)
except Exception as exc:
    runtime_context["context_error"] = f"{type(exc).__name__}: {exc}"

benchmark_record = {
    "run_id": run_id,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "wheel_source": wheel_source,
    "package_name": wheel_distribution_name,
    "package_version": package_version,
    "import_name": wheel_import_name,
    "test_callable": wheel_test_callable or None,
    "spark_application_id": spark.sparkContext.applicationId,
    "input_rows": input_rows,
    "output_rows": output_rows,
    "partitions": input_partitions,
    "duration_seconds": duration_seconds,
    "rows_per_second": output_rows / duration_seconds if duration_seconds else None,
    "executor_import_ok": all(item["ok"] for item in executor_probe),
    "executor_probe_json": json.dumps(executor_probe, default=str),
    "runtime_context_json": json.dumps(runtime_context, default=str),
}
spark.createDataFrame([benchmark_record]).write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable("custom_wheel_benchmark_results")
print(benchmark_record)

# METADATA ********************

# META {"language": "python", "language_group": "synapse_pyspark"}
