# Security Policy

## Supported Versions

Security fixes are applied to the latest state of the default branch.

## Reporting a Vulnerability

If you discover a security issue, please report it privately before opening a public issue.

Include:

- Description of the vulnerability
- Reproduction steps
- Potential impact
- Suggested remediation (if available)

Do not publish proof-of-concept exploit details publicly until a fix is available.

## Credential and Token Handling

Task Logger uses file-based credentials for optional Google Calendar integration.

- OAuth client credentials are loaded from the path configured in `Settings`.
- OAuth access/refresh tokens are stored in the configured token file.
- Token permissions are hardened on POSIX systems where possible.

Recommendations:

- Keep credential and token files outside source control.
- Use machine-level access controls for token paths.
- Use separate Google Cloud projects/accounts for non-production and production usage.
- Rotate credentials if compromise is suspected.

## Local Data

- Task data is stored in `task_log.xlsx`.
- App settings are stored in `config.json`.

Protect these files according to your organization policy if they contain sensitive client details.

## Dependency Hygiene

- Keep Python dependencies updated.
- Review transitive dependency risk before production rollout.
- Pin and scan dependencies in production environments.
