# Task Logger

Task Logger is a desktop time-tracking application for service work and billing. It lets you log tasks, calculates decimal hours, stores records in Excel, and optionally syncs events to Google Calendar.

The app is local-first: task logging works with no Google setup.

## Highlights

- Single-window UI with tabs: `Log Task`, `Task List`, and `Settings`
- Fast task capture with timezone-aware hour calculations
- Date input supports both manual typing (`YYYY-MM-DD`) and calendar picking
- Edit and delete workflows from a table view
- Local Excel persistence in `task_log.xlsx`
- Optional Google Calendar sync (opt-in, configurable)
- Graceful fallback: local saves continue even if Google sync fails

## Table of Contents

- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Google Calendar (Optional)](#google-calendar-optional)
- [Configuration](#configuration)
- [Data Model](#data-model)
- [Project Structure](#project-structure)
- [Development](#development)
- [Task Automation](#task-automation)
- [Release Management](#release-management)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

## Architecture

The codebase is intentionally small and split by responsibility:

- `taskLoggerGUI.py`
  - Main application window and tab layout
  - Form validation, settings management, and status feedback
- `taskListGUI.py`
  - Embedded task list panel (table, edit, delete interactions)
- `taskLogger.py`
  - Core domain logic: parsing, validation, hour calculation
  - Excel read/write operations
  - Optional Google Calendar API integration

## Requirements

- Python 3.9+
- Windows, macOS, or Linux with a desktop environment

Core dependencies:

- `pandas`
- `openpyxl`
- `customtkinter`
- `pytz`

Optional Google sync dependencies:

- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/flarewebdesign/task-logger.git
cd task-logger
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

3. Install core dependencies:

```bash
pip install -r requirements.txt
```

4. Run the desktop app:

```bash
python taskLoggerGUI.py
```

## Google Calendar (Optional)

Google sync is disabled by default. Enable it only if needed.

1. Install Google dependencies:

```bash
pip install -r requirements-google.txt
```

2. Create OAuth client credentials from Google Cloud and download `credentials.json`.
3. Open the app and go to `Settings`.
4. Enable `Google Calendar Sync`.
5. Set:
   - `Credentials File` (path to your OAuth JSON)
   - `Token Storage File` (local token path)
   - `Calendar ID` (default: `primary`)
6. Click `Connect Google` and finish authorization.

Notes:

- If sync fails during add/edit/delete, local task data is still saved.
- Token files are local and never uploaded by the app.

## Configuration

The app writes `config.json` in the project root.

Example:

```json
{
  "timezone": "UTC",
  "google_sync_enabled": false,
  "google_credentials_path": "credentials.json",
  "google_token_path": "C:/Users/<you>/.task_logger/token.json",
  "google_calendar_id": "primary"
}
```

Key settings:

- `timezone`: default timezone for new tasks
- `google_sync_enabled`: enables calendar sync calls
- `google_credentials_path`: OAuth client JSON path
- `google_token_path`: OAuth token output path
- `google_calendar_id`: Google Calendar target ID

## Data Model

Task records are stored in `task_log.xlsx` with these columns:

- `ID`: UUID for each task
- `Task`: task title
- `Start Date`: `YYYY-MM-DD`
- `Start Time`: `HH:MM` (12-hour input)
- `Start AM/PM`: `AM` or `PM`
- `End Date`: `YYYY-MM-DD`
- `End Time`: `HH:MM` (12-hour input)
- `End AM/PM`: `AM` or `PM`
- `Timezone`: IANA timezone string (for example `America/Detroit`)
- `Decimal Hours`: computed duration
- `Event ID`: Google event ID when synced
- `Attendees`: comma-separated email list

## Project Structure

```text
task-logger/
  .github/
    workflows/
      ci.yml
    ISSUE_TEMPLATE/
      bug_report.yml
      feature_request.yml
      config.yml
    pull_request_template.md
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
  Makefile
  requirements.txt
  requirements-google.txt
  scripts/
    tasks.ps1
  taskLoggerGUI.py
  taskListGUI.py
  taskLogger.py
  config.json            # generated at runtime
  task_log.xlsx          # generated at runtime
```

## Development

1. Create a virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

2. For Google integration development, install optional dependencies:

```bash
pip install -r requirements-google.txt
```

3. Run the app from source:

```bash
python taskLoggerGUI.py
```

4. Validate syntax before commits:

```bash
python -m py_compile taskLogger.py taskListGUI.py taskLoggerGUI.py
```

5. CI runs the same compile checks and a local-only backend smoke test on pull requests and pushes to `main`.

## Task Automation

Contributor shortcuts are available for both Unix-like and Windows environments.

Makefile targets:

```bash
make install
make check
make smoke
make run
```

PowerShell task runner:

```powershell
.\scripts\tasks.ps1 setup
.\scripts\tasks.ps1 check
.\scripts\tasks.ps1 smoke
.\scripts\tasks.ps1 run
```

For Google-enabled environments:

```bash
make install-google
```

```powershell
.\scripts\tasks.ps1 setup-google
```

## Release Management

- Release notes are tracked in `CHANGELOG.md`.
- Use the `Unreleased` section during active development.
- Create a versioned section when preparing a release.

## Troubleshooting

- `ModuleNotFoundError: pandas` (or similar):
  - Install missing dependencies in your active environment.
- `Google Calendar dependencies are not installed`:
  - Install the optional Google packages listed above.
- `Google credentials file not found`:
  - Verify `Credentials File` path in `Settings`.
- `Dates must use YYYY-MM-DD format` or time validation errors:
  - Use the exact input format shown in the form labels.
- Calendar failures while saving:
  - Data is still stored locally; inspect the warning message and retry after fixing Google auth/config.

## Security Notes

- Credentials and tokens are file-based and local to the machine.
- Keep OAuth credential and token files out of version control.
- Use a dedicated Google account/project for production usage.
- Review and rotate credentials if you suspect leakage.

For reporting security issues, see `SECURITY.md`.

## Contributing

See `CONTRIBUTING.md` for setup, standards, and pull request expectations.
