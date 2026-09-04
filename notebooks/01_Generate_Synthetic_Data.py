# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
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

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

PROFILES = {
    "smoke": {"rows": 10_000, "partitions": 4},
    "medium": {"rows": 1_000_000, "partitions": 32},
    "benchmark": {"rows": 100_000_000, "partitions": 256},
}

if scale_profile not in PROFILES:
    raise ValueError(f"Unknown scale_profile {scale_profile!r}")
if scale_profile == "benchmark" and not enable_scale_test:
    raise RuntimeError("benchmark requires enable_scale_test=true and explicit customer approval")

profile = PROFILES[scale_profile]
rows = profile["rows"]
partitions = profile["partitions"]

# Synthetic values deliberately repeat via modulo operations. No customer data
# or external source is used.
df = (
    spark.range(0, rows, numPartitions=partitions)
    .withColumnRenamed("id", "row_id")
    .withColumn("customer_id", F.concat(F.lit("C"), F.lpad((F.col("row_id") % 1000).cast("string"), 6, "0")))
    .withColumn("account_id", F.concat(F.lit("A"), F.lpad((F.col("row_id") % 2500).cast("string"), 8, "0")))
    .withColumn("ssn", F.when(F.col("row_id") % 17 == 0, F.lit(None)).otherwise(F.format_string("%03d-%02d-%04d", F.col("row_id") % 900 + 100, F.col("row_id") % 90 + 10, F.col("row_id") % 1000)))
    .withColumn("email", F.when(F.col("row_id") % 23 == 0, F.lit(None)).otherwise(F.concat(F.lit("customer"), (F.col("row_id") % 1000), F.lit("@example.test"))))
    .withColumn("phone", F.format_string("+1-555-%03d-%04d", F.col("row_id") % 200, F.col("row_id") % 1000))
    .withColumn("first_name", F.concat(F.lit("First"), (F.col("row_id") % 200).cast("string")))
    .withColumn("last_name", F.concat(F.lit("Last"), (F.col("row_id") % 300).cast("string")))
    .withColumn("street_address", F.concat((F.col("row_id") % 5000 + 1).cast("string"), F.lit(" Synthetic Ave")))
    .withColumn("account_number", F.format_string("%012d", F.col("row_id") % 2500))
    .withColumn("routing_number", F.format_string("%09d", F.col("row_id") % 20 + 100000000))
    .withColumn("transaction_id", F.concat(F.lit("TX"), F.lpad(F.col("row_id").cast("string"), 14, "0")))
    .withColumn("transaction_amount", ((F.col("row_id") % 250000) / F.lit(100.0)).cast("decimal(18,2)"))
    .withColumn("merchant", F.concat(F.lit("Merchant-"), (F.col("row_id") % 50).cast("string")))
    .withColumn("event_timestamp", F.to_timestamp(F.from_unixtime(F.lit(1767225600) + (F.col("row_id") % 86400))))
    .drop("row_id")
)

df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("custom_wheel_input")
actual_rows = spark.table("custom_wheel_input").count()
actual_partitions = spark.table("custom_wheel_input").rdd.getNumPartitions()
summary = {"run_id": run_id, "profile": scale_profile, "rows": actual_rows, "partitions": actual_partitions}
print(summary)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
