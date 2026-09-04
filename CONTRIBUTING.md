# Contributing

Contributions that improve portability, validation, documentation, or safety
are welcome.

1. Fork the repository and create a focused branch.
2. Never add real credentials, tenant IDs, customer data, proprietary wheels, or
   generated run evidence.
3. Keep Fabric mutations opt-in and cleanup scoped to exact POC item IDs.
4. Add or update tests for behavior changes.
5. Run:

   ```powershell
   python -m ruff check .
   python -m pytest
   python scripts/build_sample_wheel.py
   git diff --check
   ```

6. Explain API-contract or runtime changes and link authoritative Microsoft
   documentation in the pull request.

By contributing, you agree that your contribution is licensed under MIT.
