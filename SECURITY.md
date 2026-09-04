# Security policy

## Supported versions

Security fixes are applied to the default branch.

## Reporting a vulnerability

Do not open a public issue for a vulnerability or exposed credential. Use the
repository's **Security → Report a vulnerability** private reporting workflow.

Include affected files, impact, reproduction steps, and suggested mitigation.
Do not include live access tokens, secrets, proprietary wheels, or customer
data in the report.

## Repository data policy

Tracked content must not contain credentials, connection strings, tenant or
resource identifiers from executed runs, customer data, or third-party wheel
binaries. Local configuration belongs in `.env`; wheels belong under the
ignored `vendor/wheels/` path; execution evidence belongs under ignored
`results/` files.

This project demonstrates package distribution. It does not provide a security,
privacy, encryption, or sandbox boundary for third-party code. Review a wheel's
source, provenance, license, and behavior before executing it.
