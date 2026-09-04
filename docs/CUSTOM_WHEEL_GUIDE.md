# Use your own wheel

## Information you need

- Local path to the `.whl`.
- Distribution name from the wheel's `METADATA: Name` field.
- Top-level Python module used by `import`.
- Supported Python and platform tags.
- Dependency, license, network, and native-library requirements.
- Optional callable that accepts one string-compatible value.

Do not infer a vendor API from filenames or module names. Import-only validation
is a valid first milestone.

## Configure

Store the binary under the ignored `vendor/wheels/` directory or use another
local path. In the untracked `.env` file:

```dotenv
WHEEL_SOURCE=custom
WHEEL_PATH=vendor/wheels/example-1.0.0-py3-none-any.whl
WHEEL_IMPORT_NAME=example
WHEEL_DISTRIBUTION_NAME=example
WHEEL_TEST_CALLABLE=example:transform
```

Leave `WHEEL_TEST_CALLABLE` empty when the package requires complex
construction, credentials, network access, batch inputs, or a vendor-specific
lifecycle. Adapt Notebook 02 only from authoritative package documentation.

## Validate before upload

```powershell
python scripts/inspect_wheel.py vendor/wheels/example-1.0.0-py3-none-any.whl
python scripts/preflight.py
```

Confirm `Requires-Python`, wheel tags, dependencies, size, distribution name,
and top-level modules are compatible with the selected Fabric runtime. Metadata
inspection does not execute or decompile the wheel.

## Publish and test

```powershell
python scripts/run_poc.py --provision-only
python scripts/run_poc.py --run-smoke
python scripts/collect_results.py
```

Verify the Environment publish state, driver import, every executor probe,
Spark application ID, row counts, and validation table. Treat sample results as
infrastructure evidence—not proof of a package's security, correctness, or
production performance.
