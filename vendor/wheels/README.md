# Local wheel staging

Put third-party or proprietary `.whl` files in this directory. They are ignored
by Git and must not be committed.

Before using a wheel, confirm you are authorized to possess and execute it, then
inspect its metadata:

```powershell
python scripts/inspect_wheel.py vendor/wheels/<filename>.whl
```

Configure `WHEEL_SOURCE=custom`, `WHEEL_PATH`, `WHEEL_IMPORT_NAME`, and
optionally `WHEEL_DISTRIBUTION_NAME` and `WHEEL_TEST_CALLABLE` in the local
`.env`. See `docs/CUSTOM_WHEEL_GUIDE.md`.
