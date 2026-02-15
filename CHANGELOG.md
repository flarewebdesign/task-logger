# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Contributor task automation:
  - `Makefile` targets for install/check/run/smoke.
  - `scripts/tasks.ps1` for Windows setup/check/run/smoke commands.
- Calendar date picker support in add/edit flows while preserving manual `YYYY-MM-DD` entry.

## [0.3.0] - 2026-02-14

### Added
- Dependency manifests for reproducible installs:
  - `requirements.txt` (core/local mode)
  - `requirements-google.txt` (Google-enabled mode)
- Team-oriented repository standards:
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - GitHub issue templates and pull request template
- CI workflow to run syntax and smoke checks on pull requests and pushes.

### Changed
- Documentation upgraded to professional project format, including architecture, configuration, troubleshooting, and security guidance.
- User experience updated to a single-window tabbed interface.
- Google Calendar integration changed to opt-in behavior with local-first fallback.

## [0.2.0] - 2026-02-14

### Added
- Unified desktop UI with `Log Task`, `Task List`, and `Settings` tabs.
- Embedded task table with edit/delete flows.
- Optional Google Calendar configuration panel and connect flow.
- Local-first task logging with graceful calendar-sync failure handling.

### Changed
- Refactored task persistence and calendar sync logic to support optional integration and clearer validation errors.
