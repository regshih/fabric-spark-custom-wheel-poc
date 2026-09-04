# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# PARAMETERS CELL ********************

target_notebook_ids = ""
workspace_id = ""
lakehouse_name = ""
environment_id = ""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

targets = [value.strip() for value in target_notebook_ids.split(",") if value.strip()]
if not all([targets, workspace_id, lakehouse_name, environment_id]):
    raise ValueError("target_notebook_ids, workspace_id, lakehouse_name, and environment_id are required")

results = {}
for notebook_id in targets:
    results[notebook_id] = notebookutils.notebook.updateDefinition(
        name=notebook_id,
        defaultLakehouse=lakehouse_name,
        defaultLakehouseWorkspace=workspace_id,
        workspaceId=workspace_id,
        environmentId=environment_id,
        environmentWorkspaceId=workspace_id,
    )

if not all(results.values()):
    raise RuntimeError(f"One or more notebook dependency updates failed: {results}")
print(results)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
