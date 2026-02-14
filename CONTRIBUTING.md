# Contributing Guide

Thanks for your interest in improving Task Logger.

This document defines the expected workflow for code, documentation, and review quality.

## Development Setup

1. Fork the repository.
2. Clone your fork.
3. Create and activate a virtual environment.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

Optional Google integration dependencies:

```bash
pip install -r requirements-google.txt
```

Optional one-command setup helpers:

```bash
make install
make install-google
```

```powershell
.\scripts\tasks.ps1 setup
.\scripts\tasks.ps1 setup-google
```

## Branching

- Create a feature branch per change:
  - `feature/<short-description>`
  - `fix/<short-description>`
  - `docs/<short-description>`

Example:

```bash
git checkout -b feature/single-window-ux
```

## Code Standards

- Keep modules focused and cohesive.
- Prefer explicit validation and user-facing error messages.
- Avoid introducing breaking behavior without documenting migration impact.
- Maintain local-first behavior (Google sync must remain optional).

## Documentation Standards

- Update `README.md` when user flows or configuration changes.
- Update `CHANGELOG.md` (`Unreleased`) for user-visible changes.
- Update `SECURITY.md` for credential/token handling changes.
- Keep examples runnable and aligned with the current code.

## Testing and Validation

Before opening a pull request:

1. Run syntax checks:

```bash
python -m py_compile taskLogger.py taskListGUI.py taskLoggerGUI.py
```

Or use project automation:

```bash
make check
```

```powershell
.\scripts\tasks.ps1 check
```

2. Confirm CI workflow passes:

- GitHub Actions `CI` workflow

3. Manually validate critical flows:

- Add task
- Edit task
- Delete task
- Save settings
- Optional: Google connect + sync path

## Commit Guidelines

- Use clear, imperative commit messages.
- Keep commits focused (one concern per commit when practical).

Examples:

- `Refactor GUI into single-window tabbed layout`
- `Make Google Calendar sync optional and local-first`
- `Improve README with architecture and security guidance`

## Pull Request Expectations

Each PR should include:

- Problem statement
- Summary of changes
- Risk/impact notes
- Validation steps performed
- Screenshots for UI changes (if relevant)
- A changelog entry in `CHANGELOG.md` when applicable

Use `.github/pull_request_template.md` when opening PRs.

## Issue Reporting

When filing an issue, include:

- OS and Python version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs or error messages

## Code of Conduct

Be professional and respectful in all project discussions and reviews.
