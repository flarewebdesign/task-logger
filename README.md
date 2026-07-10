# Task Logger

[![CI](https://github.com/flarewebdesign/task-logger/actions/workflows/ci.yml/badge.svg)](https://github.com/flarewebdesign/task-logger/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
![Local-first](https://img.shields.io/badge/Local--first-desktop-111827)
![Excel persistence](https://img.shields.io/badge/Storage-Excel-217346?logo=microsoftexcel&logoColor=white)
![Google Calendar optional](https://img.shields.io/badge/Google%20Calendar-optional-4285F4?logo=googlecalendar&logoColor=white)
![Dashboard API optional](https://img.shields.io/badge/Dashboard%20API-optional-0F172A)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Local-first Python desktop time ledger with Excel persistence and opt-in external synchronization.

Task Logger records client work, categories, billing state, and timezone-aware durations without requiring hosted infrastructure. Excel remains the local system of record. Google Calendar and private dashboard integrations extend the workflow without becoming runtime dependencies.

## Capabilities

- Logs client work with task name, client, category, date, time, timezone, attendees, and billable state.
- Calculates decimal hours from timezone-aware start and end times.
- Stores all task records locally in `task_log.xlsx`.
- Writes Excel changes atomically and keeps a rolling `task_log.backup.xlsx` recovery copy.
- Stores local preferences, clients, categories, and optional sync settings in `config.json`.
- Supports editing and deleting existing tasks from the desktop table.
- Tracks Calendar and dashboard sync state per row, with manual retry from the task list.
- Optionally syncs tasks to Google Calendar.
- Optionally upserts and deletes time entries through a private dashboard API.
- Optionally imports dashboard client names into the local client list.

## Architecture

Core operation is self-contained. Task creation, editing, deletion, filtering, and review remain available when every external integration is disabled or unreachable.

Runtime files:

- `config.json`: local settings created by the app when it first runs.
- `task_log.xlsx`: primary local task database created by the app when it first runs.
- `task_log.backup.xlsx`: previous valid workbook snapshot, refreshed before each replacement.
- Google token and credential files: present only when Google Calendar synchronization is configured.

Task and settings writes use same-directory temporary files followed by atomic replacement. An unreadable workbook is preserved and copied to a timestamped `task_log.recovery-*.xlsx` file; it is never replaced with an empty workbook during recovery.

Runtime data and credential files are excluded from version control.

## Clients and Categories

Clients and categories are local configuration values stored in `config.json`. New installations begin with an `Unassigned` client and a general-purpose category set. The Log Task and Edit Task controls read directly from these lists.

Dashboard client import remains optional:

- `Import From Dashboard` requests `GET /api/clients`.
- Returned names replace the local `clients` list after normalization.
- Client import does not enable time-entry synchronization.
- Locally configured clients remain available without a dashboard connection.

Example local client config:

```json
{
  "clients": ["Unassigned", "Acme Studio", "Northwind"],
  "categories": ["Development", "Design", "Admin", "Support", "Meetings"]
}
```

## Quick Start

Clone the repository:

```bash
git clone https://github.com/flarewebdesign/task-logger.git
cd task-logger
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the core dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python taskLoggerGUI.py
```

## Configuration

Runtime settings are stored in `config.json` at the project root.

Example:

```json
{
  "timezone": "UTC",
  "categories": ["Development", "Design", "Admin", "Support", "Meetings"],
  "clients": ["Unassigned", "Acme Studio"],
  "google_sync_enabled": false,
  "google_credentials_path": "credentials.json",
  "google_token_path": "C:/Users/example/.task_logger/token.json",
  "google_calendar_id": "primary",
  "dashboard_sync_enabled": false,
  "dashboard_api_url": "http://localhost:3000",
  "dashboard_api_token": ""
}
```

Settings:

- `timezone`: default timezone for new tasks.
- `categories`: category choices used by add/edit forms.
- `clients`: client choices used by add/edit forms.
- `google_sync_enabled`: enables Google Calendar sync calls.
- `google_credentials_path`: OAuth client JSON path.
- `google_token_path`: OAuth token output path.
- `google_calendar_id`: Google Calendar target ID.
- `dashboard_sync_enabled`: enables dashboard API sync calls.
- `dashboard_api_url`: private dashboard base URL.
- `dashboard_api_token`: compatibility fallback for the dashboard bearer token. Supported operating systems store the token in the native credential store and remove it from `config.json`.

## Google Calendar Sync

Google Calendar sync is disabled by default.

Install the optional Google dependencies:

```bash
pip install -r requirements-google.txt
```

OAuth setup:

1. Create OAuth client credentials in Google Cloud.
2. Download the OAuth JSON file.
3. Open Task Logger and go to `Settings`.
4. Enable `Google Calendar Sync`.
5. Set `Credentials File`, `Token Storage File`, and `Calendar ID`.
6. Click `Connect Google` and complete browser authorization.

Calendar failures do not roll back the local Excel record. The affected row retains its error state for a later retry.

## Dashboard API Sync

Dashboard synchronization is disabled by default and targets a compatible private API.

Settings required for sync:

- `Enable Dashboard Sync`
- `Dashboard URL`
- `Dashboard API Token`

The desktop app sends:

```text
Authorization: Bearer <dashboard token>
Accept: application/json
Content-Type: application/json
```

### Import Clients

Invoked by the `Import From Dashboard` command.

```text
GET /api/clients
```

Accepted response shapes:

```json
{
  "clients": ["Acme Studio", "Northwind"]
}
```

```json
{
  "clients": [
    { "name": "Acme Studio" },
    { "name": "Northwind" }
  ]
}
```

Imported names replace the local Clients field and are persisted to `config.json`.

### Upsert Time Entry

Invoked after a local add or edit when dashboard synchronization is enabled.

```text
POST /api/time-entries
```

Payload:

```json
{
  "external_id": "task UUID from desktop",
  "task": "Client work",
  "client": "Acme Studio",
  "category": "Development",
  "start": "2026-07-07T09:00:00+00:00",
  "end": "2026-07-07T10:30:00+00:00",
  "timezone": "UTC",
  "decimal_hours": 1.5,
  "billable": true,
  "source": "task-logger"
}
```

Expected response:

```json
{
  "entry": {
    "id": "dashboard-entry-id"
  }
}
```

Recommended dashboard behavior:

- Validate the bearer token.
- Upsert by `external_id` so repeated desktop syncs update the same row.
- Store `external_id` separately from the dashboard database ID.
- Treat missing `billable` as `true` for compatibility with older desktop clients.
- Return the dashboard entry ID in `entry.id`.

### Delete Time Entry

Invoked when deleting a task that has dashboard synchronization enabled.

```text
DELETE /api/time-entries/{external_id_or_id}
```

The path identifier is the local task UUID. Compatible APIs resolve it through `external_id` or the native dashboard ID.

Valid responses:

- `204 No Content`
- `200 OK` with an empty or JSON body

### Consistency and Retry Model

Excel commits precede external synchronization requests. This ordering provides the following guarantees:

- A local add or edit remains saved in Excel.
- A failed remote deletion remains in Excel as `delete_pending` until external cleanup succeeds.
- Calendar and dashboard status are tracked independently with their most recent errors.
- Retry controls appear only for actionable `pending`, `error`, or `delete_pending` states.
- Retry labels identify the affected provider: `Retry Calendar Sync`, `Retry Dashboard Sync`, or `Retry Sync` when both require attention.
- Persisted failures remain retryable even when the corresponding integration toggle is subsequently disabled.

## Data Model

Task records are stored in `task_log.xlsx`.

| Column | Description |
| --- | --- |
| `ID` | Local UUID for each task. |
| `Task` | Task title. |
| `Client` | Client name from local config. |
| `Category` | Work category from local config. |
| `Start Date` | Start date in `YYYY-MM-DD` format. |
| `Start Time` | Start time in 12-hour `HH:MM` format. |
| `Start AM/PM` | `AM` or `PM`. |
| `End Date` | End date in `YYYY-MM-DD` format. |
| `End Time` | End time in 12-hour `HH:MM` format. |
| `End AM/PM` | `AM` or `PM`. |
| `Timezone` | IANA timezone string, such as `America/New_York`. |
| `Decimal Hours` | Computed duration. |
| `Billable` | `true` for billable work, `false` for no-charge work. |
| `Event ID` | Google Calendar event ID when synced. |
| `Dashboard Entry ID` | Dashboard entry ID returned by the API when synced. |
| `Attendees` | Comma-separated attendee emails. |
| `Google Sync Status` | Calendar state: `not_configured`, `pending`, `synced`, `error`, or `delete_pending`. |
| `Dashboard Sync Status` | Dashboard state: `not_configured`, `pending`, `synced`, `error`, or `delete_pending`. |
| `Google Sync Error` | Most recent Calendar sync error, if any. |
| `Dashboard Sync Error` | Most recent dashboard sync error, if any. |
| `Last Modified` | Local timestamp for the most recent row change. |

Legacy workbooks are migrated automatically during load. Missing schema columns receive safe defaults, an existing `Event ID` backfills Calendar state to `synced`, and an existing `Dashboard Entry ID` backfills dashboard state to `synced`. Every migration creates `task_log.backup.xlsx` before replacing the workbook.

## Project Structure

```text
task-logger/
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
  Makefile
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  requirements-google.txt
  secret_store.py
  scripts/
    tasks.ps1
  tests/
  taskLogger.py
  taskLoggerGUI.py
  taskListGUI.py
  ui_date_picker.py
  config.json            # generated locally, ignored by Git
  task_log.xlsx          # generated locally, ignored by Git
```

Core modules:

- `taskLogger.py`: validation, time calculation, Excel persistence, Google sync, and dashboard API calls.
- `taskLoggerGUI.py`: main desktop window, form validation, settings, and add-task flow.
- `taskListGUI.py`: task table, edit flow, delete flow, and sync cleanup warnings.
- `secret_store.py`: operating system credential-store integration for the dashboard token.
- `ui_date_picker.py`: date picker UI helper.

## Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run lint and format checks:

```bash
ruff check .
ruff format --check .
```

Run the automated test suite:

```bash
pytest
```

Run the local-only CRUD smoke test:

```bash
make smoke
```

Windows task shortcuts:

```powershell
.\scripts\tasks.ps1 setup
.\scripts\tasks.ps1 setup-dev
.\scripts\tasks.ps1 check
.\scripts\tasks.ps1 test
.\scripts\tasks.ps1 smoke
.\scripts\tasks.ps1 run
```

## Repository Safety

Private runtime data is excluded from the public source tree.

Excluded artifacts include:

- `config.json`
- `task_log.xlsx`
- `.env` files
- Google OAuth credentials
- Google token files
- Dashboard API tokens

The project `.gitignore` covers local runtime files, backups, recovery copies, development environments, and common secret-file patterns.

## Troubleshooting

`ModuleNotFoundError: pandas` or similar:

Install dependencies in the active environment.

```bash
pip install -r requirements.txt
```

Google Calendar dependencies are not installed:

```bash
pip install -r requirements-google.txt
```

Dashboard client import fails:

- Confirm the dashboard is running.
- Confirm `Dashboard URL` points to the API base URL.
- Confirm `Dashboard API Token` matches the server-side bearer token.
- Confirm `GET /api/clients` returns one of the supported response shapes.

Dashboard task sync fails:

- Confirm `POST /api/time-entries` accepts the documented payload.
- Confirm `DELETE /api/time-entries/{id}` supports lookup by `external_id`.
- Inspect the warning text shown by the desktop app.
- Select the affected row in Task List and use the provider-specific retry action after correcting the settings.

Excel workbook cannot be opened:

- Close `task_log.xlsx` in Excel if it is open and retry the action.
- Do not delete the original workbook after a read error. Task Logger creates a timestamped `.recovery-*.xlsx` copy and leaves the original untouched.
- Use `task_log.backup.xlsx` to recover the previous valid workbook state when needed.

Date or time validation errors:

- Dates must use `YYYY-MM-DD`.
- Times must use 12-hour `HH:MM`.
- Start/end periods must be `AM` or `PM`.

## Security

Task logs, client names, and billing metadata are sensitive local data. File-system access controls should cover `task_log.xlsx`, its backups, recovery copies, and `config.json`. Dashboard API tokens use the operating-system credential store when available; the application reports when plaintext compatibility storage is required.

For reporting security issues, see `SECURITY.md`.

## Contributing

See `CONTRIBUTING.md` for setup, standards, and pull request expectations.

## License

Task Logger is released under the [MIT License](LICENSE).
