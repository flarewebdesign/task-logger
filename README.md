# Task Logger

Python 3.9+ | Local-first desktop app | Excel persistence | Optional Google Calendar sync | Optional dashboard API sync

Local-first Python desktop time tracker for client work, billable hours, categories, and optional sync targets.

Task Logger is built so the public repository is useful without any private infrastructure. It works as a standalone desktop app that stores settings in `config.json` and tasks in `task_log.xlsx`. If you have your own dashboard, you can opt into token-authenticated API sync without making the dashboard required for local users.

## What It Does

- Logs client work with task name, client, category, date, time, timezone, attendees, and billable state.
- Calculates decimal hours from timezone-aware start and end times.
- Stores all task records locally in `task_log.xlsx`.
- Stores local preferences, clients, categories, and optional sync settings in `config.json`.
- Supports editing and deleting existing tasks from the desktop table.
- Optionally syncs tasks to Google Calendar.
- Optionally upserts and deletes time entries through a private dashboard API.
- Optionally imports dashboard client names into the local client list.

## Local-First Model

The desktop app does not require Google, a dashboard, Neon, Vercel, or any hosted service.

Runtime files:

- `config.json`: local settings created by the app when it first runs.
- `task_log.xlsx`: local task database created by the app when it first runs.
- Google token and credential files: only used if Google Calendar sync is enabled.

These files are intentionally ignored by Git because they can contain private client, billing, and credential data.

## Where Local Clients Come From

Local clients are loaded from the `clients` array in `config.json`.

Startup behavior:

1. `taskLoggerGUI.py` calls `load_config()`.
2. If `config.json` does not exist, the app creates it from `DEFAULT_CONFIG`.
3. The default client list is `["Unassigned"]`.
4. The Log Task and Edit Task client dropdowns read from `config["clients"]`.
5. Saving Settings normalizes the comma-separated Clients field and writes it back to `config.json`.

Dashboard import is optional:

- `Import From Dashboard` calls `GET /api/clients`.
- The returned names are copied into the same local `config.json` `clients` array.
- Importing clients does not enable task sync by itself.
- If dashboard sync is disabled, the app still uses the local client list normally.

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

Install the local-only dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python taskLoggerGUI.py
```

## Configuration

The app writes `config.json` in the project root.

Example:

```json
{
  "timezone": "UTC",
  "categories": ["Development", "Design", "Admin", "Support", "Meetings"],
  "clients": ["Unassigned", "Acme Studio"],
  "google_sync_enabled": false,
  "google_credentials_path": "credentials.json",
  "google_token_path": "C:/Users/<you>/.task_logger/token.json",
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
- `dashboard_api_token`: dashboard bearer token.

## Google Calendar Sync

Google Calendar sync is disabled by default.

Install the optional Google dependencies:

```bash
pip install -r requirements-google.txt
```

Setup:

1. Create OAuth client credentials in Google Cloud.
2. Download the OAuth JSON file.
3. Open Task Logger and go to `Settings`.
4. Enable `Google Calendar Sync`.
5. Set `Credentials File`, `Token Storage File`, and `Calendar ID`.
6. Click `Connect Google` and complete browser authorization.

If Calendar sync fails during add, edit, or delete, the local Excel task still saves and the app shows a warning.

## Dashboard API Sync

Dashboard sync is disabled by default. Enable it only when you have a compatible private API.

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

Used only when the user clicks `Import From Dashboard`.

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

The imported names replace the local Clients field and are saved to `config.json`.

### Upsert Time Entry

Called when adding or editing a task while dashboard sync is enabled.

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

Called when deleting a local task while dashboard sync is enabled.

```text
DELETE /api/time-entries/{external_id_or_id}
```

The current desktop app sends the local task UUID, so the dashboard should delete by either `external_id` or native dashboard `id`.

Valid responses:

- `204 No Content`
- `200 OK` with an empty or JSON body

### Failure Behavior

Task Logger is local-first. If a dashboard request fails:

- The local add, edit, or delete still completes.
- The app shows a warning with the sync error.
- The user can fix settings and retry with a future edit/save.

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

Older task logs are repaired automatically when loaded. Missing `Client`, `Category`, `Billable`, or sync columns are added with safe defaults.

## Project Structure

```text
task-logger/
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
  Makefile
  requirements.txt
  requirements-google.txt
  scripts/
    tasks.ps1
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
- `ui_date_picker.py`: date picker UI helper.

## Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run syntax checks:

```bash
python -m py_compile taskLogger.py taskListGUI.py taskLoggerGUI.py ui_date_picker.py
```

Run the local-only backend smoke test:

```bash
make smoke
```

Windows task shortcuts:

```powershell
.\scripts\tasks.ps1 setup
.\scripts\tasks.ps1 check
.\scripts\tasks.ps1 smoke
.\scripts\tasks.ps1 run
```

## Public Repo Safety

This repository is intended to stay public. Keep private runtime files out of source control.

Do not commit:

- `config.json`
- `task_log.xlsx`
- `.env` files
- Google OAuth credentials
- Google token files
- Dashboard API tokens

The existing `.gitignore` excludes the local runtime files used by the app. Review it before adding new generated files or deployment-specific credentials.

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

Date or time validation errors:

- Dates must use `YYYY-MM-DD`.
- Times must use 12-hour `HH:MM`.
- Start/end periods must be `AM` or `PM`.

## Security

Task logs and client names can be sensitive billing data. Protect `task_log.xlsx` and `config.json` according to your local security requirements.

For reporting security issues, see `SECURITY.md`.

## Contributing

See `CONTRIBUTING.md` for setup, standards, and pull request expectations.
