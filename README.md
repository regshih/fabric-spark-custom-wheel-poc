# Microsoft Fabric Spark custom-wheel POC

[![CI](https://github.com/regshih/fabric-spark-custom-wheel-poc/actions/workflows/ci.yml/badge.svg)](https://github.com/regshih/fabric-spark-custom-wheel-poc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A vendor-neutral, reproducible proof of concept for publishing a Python `.whl`
file to a Microsoft Fabric Environment and proving that the package imports on
both the Spark driver and Spark executors.

The repository ships with a tiny, dependency-free sample wheel. You can replace
it with your own wheel without changing the deployment automation. No tenant
IDs, credentials, customer data, proprietary wheels, or executed run artifacts
are committed.

## What it creates

```text
Fabric workspace
├── Custom-Wheel-Spark-Env
│   └── published custom .whl
├── CustomWheelPOCLakehouse
├── 00_Attach_POC_Dependencies
├── 01_Generate_Synthetic_Data
├── 02_Validate_Custom_Wheel
├── 03_Validate_Results
└── PL_Custom_Wheel_POC
```

The pipeline generates synthetic data, imports the configured package on the
driver and executors, optionally calls one configured function, writes Delta
evidence, and validates the result. It does not use `%pip` or notebook-scoped
installation.

## Safety defaults

- Uses only generated synthetic data.
- Builds the open sample wheel unless `WHEEL_SOURCE=custom` is explicit.
- Never creates, resumes, pauses, resizes, or deletes Fabric capacity.
- Does not run Spark unless `--run-smoke` or `RUN_SMOKE_TEST=true` is explicit.
- Does not change the workspace-default Environment unless explicitly enabled.
- Cleanup is dry-run by default and targets only exact recorded POC item IDs.
- `.env`, wheels under `vendor/wheels/`, and run/deployment results are ignored.

## Prerequisites

- Python 3.11 or newer for the local automation.
- Azure CLI authenticated to the correct tenant: `az login`.
- Contributor or higher on the target Fabric workspace.
- An existing active Fabric capacity if the workspace must be created.
- Microsoft ODBC Driver 18 for SQL Server only when collecting Lakehouse SQL
  evidence after a run.

## Quick start with the sample wheel

```powershell
git clone https://github.com/regshih/fabric-spark-custom-wheel-poc.git
cd fabric-spark-custom-wheel-poc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set either an existing workspace ID or a workspace name and active capacity ID
in `.env`. Never commit `.env`.

```powershell
python scripts\preflight.py
python scripts\build_sample_wheel.py
python scripts\run_poc.py --provision-only
python scripts\run_poc.py --run-smoke
python scripts\collect_results.py
```

The first command is read-only. Provisioning is idempotent by configured item
name. The smoke command starts billable Fabric Spark work.

## Use your own wheel

Place the untracked wheel in `vendor/wheels/` or reference another local path:

```dotenv
WHEEL_SOURCE=custom
WHEEL_PATH=vendor/wheels/your_package-1.2.3-py3-none-any.whl
WHEEL_IMPORT_NAME=your_package
WHEEL_DISTRIBUTION_NAME=your-package
WHEEL_TEST_CALLABLE=your_package:transform
```

`WHEEL_IMPORT_NAME` is the Python name used by `import`. The distribution name
is the `Name` value from wheel metadata and is used with
`importlib.metadata.version`. `WHEEL_TEST_CALLABLE` is optional and must accept
one string-compatible value. Leave it empty for import-only validation.

Inspect metadata without importing or decompiling the package:

```powershell
python scripts\inspect_wheel.py vendor\wheels\your_package.whl
python scripts\preflight.py
```

Review [the custom-wheel guide](docs/CUSTOM_WHEEL_GUIDE.md) before publishing a
third-party wheel. Package compatibility, licenses, native binaries, network
requirements, and the vendor API remain the wheel owner's responsibility.

## Commands

| Command | Purpose | Mutates Fabric? |
|---|---|---:|
| `python scripts/preflight.py` | Validate auth, configuration, and wheel metadata | No |
| `python scripts/build_sample_wheel.py` | Build and inspect the sample wheel | No |
| `python scripts/deploy_environment.py` | Create/update and publish the Environment | Yes |
| `python scripts/deploy_fabric_items.py` | Provision all POC items | Yes |
| `python scripts/run_poc.py --provision-only` | Provision without starting Spark | Yes |
| `python scripts/run_poc.py --run-smoke` | Provision and execute the smoke pipeline | Yes |
| `python scripts/collect_results.py` | Refresh/query run evidence | Metadata refresh only |
| `python scripts/cleanup.py` | List exact cleanup targets | No |
| `python scripts/cleanup.py --execute` | Delete recorded POC items, not workspace/capacity | Yes |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Administrator setup](docs/ADMIN_SETUP.md)
- [Fabric API contracts](docs/API_CONTRACTS.md)
- [Using a custom wheel](docs/CUSTOM_WHEEL_GUIDE.md)
- [Validation and limitations](docs/POC_FINDINGS.md)
- [Prompt for an LLM code editor](PROMPT_FOR_LLM_CODE_EDITOR.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Tests

```powershell
python -m ruff check .
python -m pytest
python scripts\build_sample_wheel.py
```

## License

MIT. Third-party wheels retain their own licenses and are not covered by this
repository's license.
