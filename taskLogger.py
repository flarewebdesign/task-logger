# taskLogger.py

import json
import os
import shutil
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd
import pytz

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


TASK_COLUMNS = [
    "ID",
    "Task",
    "Client",
    "Category",
    "Start Date",
    "Start Time",
    "Start AM/PM",
    "End Date",
    "End Time",
    "End AM/PM",
    "Timezone",
    "Decimal Hours",
    "Billable",
    "Event ID",
    "Dashboard Entry ID",
    "Attendees",
    "Google Sync Status",
    "Dashboard Sync Status",
    "Google Sync Error",
    "Dashboard Sync Error",
    "Last Modified",
]

DEFAULT_CLIENT = "Unassigned"
DEFAULT_CATEGORY = "Uncategorized"

SYNC_NOT_CONFIGURED = "not_configured"
SYNC_PENDING = "pending"
SYNCED = "synced"
SYNC_ERROR = "error"
SYNC_DELETE_PENDING = "delete_pending"

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class TaskLogError(RuntimeError):
    """Base error for local workbook access problems."""


class TaskLogRecoveryError(TaskLogError):
    def __init__(self, task_log, recovery_path):
        self.task_log = str(task_log)
        self.recovery_path = str(recovery_path)
        super().__init__(
            f"Could not read {self.task_log}. The original was preserved at "
            f"{self.recovery_path}. Restore or inspect that file before continuing."
        )


VALID_SYNC_STATUSES = {
    SYNC_NOT_CONFIGURED,
    SYNC_PENDING,
    SYNCED,
    SYNC_ERROR,
    SYNC_DELETE_PENDING,
}
ACTIONABLE_SYNC_STATUSES = {SYNC_PENDING, SYNC_ERROR, SYNC_DELETE_PENDING}
TASK_LOG_LOCK = threading.RLock()


def _serialized_task_log_operation(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with TASK_LOG_LOCK:
            return function(*args, **kwargs)

    return wrapper


def _normalize_sync_status(value, default=SYNC_NOT_CONFIGURED):
    normalized = _safe_cell(value).lower().replace(" ", "_")
    return normalized if normalized in VALID_SYNC_STATUSES else default


def _normalize_billable(value, default=True):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"0", "false", "no", "n", "non-billable", "non billable", "no charge", "not billable"}:
        return False
    if normalized in {"1", "true", "yes", "y", "billable", "billed"}:
        return True

    return default


def is_billable(value, default=True):
    return _normalize_billable(value, default=default)


def harden_file_permissions(file_path):
    try:
        if os.name == "posix":
            os.chmod(file_path, 0o600)
    except OSError:
        pass


def _backup_path(file_path):
    path = Path(file_path)
    return path.with_name(f"{path.stem}.backup{path.suffix}")


def _recovery_path(file_path):
    path = Path(file_path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}.recovery-{timestamp}{path.suffix}")


def _write_excel_atomic(dataframe, task_log, create_backup=True):
    destination = Path(task_log).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}-",
        suffix=destination.suffix,
        dir=destination.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        dataframe.to_excel(temporary_path, index=False)
        if create_backup and destination.exists():
            shutil.copy2(destination, _backup_path(destination))
        os.replace(temporary_path, destination)
        harden_file_permissions(destination)
    except PermissionError as exc:
        raise TaskLogError(f"Could not save {destination}. Close the workbook in Excel and try again.") from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_task_log_exists(task_log="task_log.xlsx"):
    if not os.path.exists(task_log):
        _write_excel_atomic(
            pd.DataFrame(columns=TASK_COLUMNS),
            task_log,
            create_backup=False,
        )


def load_task_log(task_log="task_log.xlsx"):
    ensure_task_log_exists(task_log)
    try:
        df = pd.read_excel(task_log)
    except PermissionError as exc:
        raise TaskLogError(f"Could not open {task_log}. Close the workbook in Excel and try again.") from exc
    except Exception as exc:
        recovery_path = _recovery_path(task_log)
        shutil.copy2(task_log, recovery_path)
        raise TaskLogRecoveryError(task_log, recovery_path) from exc

    migration_required = False
    if list(df.columns) != TASK_COLUMNS:
        repaired = pd.DataFrame(index=df.index, columns=TASK_COLUMNS)
        for column in TASK_COLUMNS:
            if column in df.columns:
                repaired[column] = df[column]
        df = repaired
        migration_required = True

    df["Client"] = df["Client"].apply(_normalize_client)
    df["Category"] = df["Category"].apply(_normalize_category)
    df["Billable"] = df["Billable"].apply(_normalize_billable)
    for status_column in ["Google Sync Status", "Dashboard Sync Status"]:
        df[status_column] = df[status_column].apply(_normalize_sync_status)
    for error_column in ["Google Sync Error", "Dashboard Sync Error"]:
        df[error_column] = df[error_column].apply(_safe_cell).astype(object)

    sync_id_pairs = [
        ("Event ID", "Google Sync Status"),
        ("Dashboard Entry ID", "Dashboard Sync Status"),
    ]
    for id_column, status_column in sync_id_pairs:
        has_external_id = df[id_column].apply(_safe_cell).astype(bool)
        missing_status = df[status_column] == SYNC_NOT_CONFIGURED
        backfill_rows = has_external_id & missing_status
        if backfill_rows.any():
            df.loc[backfill_rows, status_column] = SYNCED
            migration_required = True

    if migration_required:
        save_task_log(df, task_log)

    return df


def save_task_log(df, task_log="task_log.xlsx"):
    output = df.copy()
    for column in TASK_COLUMNS:
        if column not in output.columns:
            output[column] = None

    output = output[TASK_COLUMNS]
    if "Client" in output.columns:
        output["Client"] = output["Client"].apply(_normalize_client)
    if "Category" in output.columns:
        output["Category"] = output["Category"].apply(_normalize_category)
    if "Billable" in output.columns:
        output["Billable"] = output["Billable"].apply(_normalize_billable)
    for status_column in ["Google Sync Status", "Dashboard Sync Status"]:
        output[status_column] = output[status_column].apply(_normalize_sync_status)
    for error_column in ["Google Sync Error", "Dashboard Sync Error"]:
        output[error_column] = output[error_column].apply(_safe_cell)
    output["Last Modified"] = output["Last Modified"].apply(
        lambda value: _safe_cell(value) or datetime.now().isoformat(timespec="seconds")
    )

    _write_excel_atomic(output, task_log)


def _parse_time_input(time_value):
    parts = time_value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("Time must use HH:MM format.")

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError("Time must contain numeric hours and minutes.") from exc

    if hour < 1 or hour > 12:
        raise ValueError("Hour must be between 1 and 12 for AM/PM time.")
    if minute < 0 or minute > 59:
        raise ValueError("Minute must be between 00 and 59.")

    return hour, minute


def normalize_12hour_time(time_value):
    hour, minute = _parse_time_input(time_value)
    return f"{hour:02d}:{minute:02d}"


def convert_to_24hour(time_value, period):
    hour, minute = _parse_time_input(time_value)
    period = period.strip().upper()
    if period not in {"AM", "PM"}:
        raise ValueError("Period must be AM or PM.")

    if period == "PM" and hour != 12:
        hour += 12
    if period == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def build_task_datetimes(start_date, start_time, start_period, end_date, end_time, end_period, timezone):
    try:
        datetime.strptime(start_date.strip(), "%Y-%m-%d")
        datetime.strptime(end_date.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD format.") from exc

    start_time_24 = convert_to_24hour(start_time, start_period)
    end_time_24 = convert_to_24hour(end_time, end_period)

    start_naive = datetime.strptime(f"{start_date} {start_time_24}", "%Y-%m-%d %H:%M")
    end_naive = datetime.strptime(f"{end_date} {end_time_24}", "%Y-%m-%d %H:%M")

    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError as exc:
        raise ValueError(f"Unknown timezone: {timezone}") from exc

    try:
        start_datetime = tz.localize(start_naive, is_dst=None)
        end_datetime = tz.localize(end_naive, is_dst=None)
    except pytz.AmbiguousTimeError as exc:
        raise ValueError(
            "The selected time occurs twice because of daylight saving time. Choose another time."
        ) from exc
    except pytz.NonExistentTimeError as exc:
        raise ValueError(
            "The selected time does not exist because of daylight saving time. Choose another time."
        ) from exc

    if end_datetime < start_datetime:
        if end_naive.date() == start_naive.date():
            end_datetime += timedelta(days=1)
        else:
            raise ValueError("End date and time must be after the start date and time.")
    if end_datetime == start_datetime:
        raise ValueError("Task duration must be greater than zero.")

    hours_worked = round((end_datetime - start_datetime).total_seconds() / 3600, 4)
    return start_datetime, end_datetime, hours_worked


def _normalize_attendees(attendees):
    if attendees is None:
        return []

    if isinstance(attendees, str):
        raw_values = attendees.split(",")
    elif isinstance(attendees, Iterable):
        raw_values = list(attendees)
    else:
        raw_values = [attendees]

    cleaned = []
    seen = set()
    for value in raw_values:
        normalized = str(value).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
    return cleaned


def _normalize_category(category):
    try:
        if pd.isna(category):
            return DEFAULT_CATEGORY
    except (TypeError, ValueError):
        pass
    normalized = str(category or "").strip()
    return normalized if normalized and normalized.lower() != "nan" else DEFAULT_CATEGORY


def _normalize_client(client):
    try:
        if pd.isna(client):
            return DEFAULT_CLIENT
    except (TypeError, ValueError):
        pass
    normalized = str(client or "").strip()
    return normalized if normalized and normalized.lower() != "nan" else DEFAULT_CLIENT


def _safe_cell(value):
    if pd.isna(value):
        return ""
    text_value = str(value).strip()
    return "" if text_value.lower() == "nan" else text_value


def _get_task_row_index(df, task_id):
    matches = df.index[df["ID"].astype(str) == str(task_id)]
    if len(matches) == 0:
        raise KeyError(f"Task ID not found: {task_id}")
    return matches[0]


def authenticate_google_calendar(credentials_path="credentials.json", token_path="token.json"):
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError(
            "Google Calendar dependencies are not installed. Install: "
            "google-auth, google-auth-oauthlib, google-api-python-client."
        )

    if not credentials_path:
        raise ValueError("A Google credentials file path is required when sync is enabled.")

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")

    creds = None
    if token_path and os.path.exists(token_path):
        with open(token_path, encoding="utf-8") as token_file:
            creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        if token_path:
            token_dir = os.path.dirname(token_path)
            if token_dir:
                os.makedirs(token_dir, exist_ok=True)
            with open(token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
            harden_file_permissions(token_path)

    return build("calendar", "v3", credentials=creds)


def add_event_to_calendar(
    task_id,
    task_name,
    start_datetime,
    end_datetime,
    timezone,
    attendees=None,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
):
    return sync_event_to_calendar(
        task_id=task_id,
        task_name=task_name,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        timezone=timezone,
        attendees=attendees,
        credentials_path=credentials_path,
        token_path=token_path,
        calendar_id=calendar_id,
    )


def _google_event_body(task_id, task_name, start_datetime, end_datetime, timezone, attendees):
    event = {
        "summary": f"{task_name} - {task_id}",
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
    }

    normalized_attendees = _normalize_attendees(attendees)
    if normalized_attendees:
        event["attendees"] = [{"email": email} for email in normalized_attendees]
    return event


def _deterministic_google_event_id(task_id):
    normalized = "".join(character for character in str(task_id).lower() if character.isalnum())
    return f"tasklogger{normalized}"


def _http_error_status(error):
    return getattr(getattr(error, "resp", None), "status", None)


def sync_event_to_calendar(
    task_id,
    task_name,
    start_datetime,
    end_datetime,
    timezone,
    attendees=None,
    event_id="",
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
):
    service = authenticate_google_calendar(credentials_path=credentials_path, token_path=token_path)
    event = _google_event_body(
        task_id,
        task_name,
        start_datetime,
        end_datetime,
        timezone,
        attendees,
    )
    target_event_id = event_id or _deterministic_google_event_id(task_id)

    if event_id:
        try:
            updated_event = (
                service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=target_event_id,
                    body=event,
                )
                .execute()
            )
            return updated_event["id"]
        except HttpError as exc:
            if _http_error_status(exc) != 404:
                raise

    event["id"] = target_event_id
    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return created_event["id"]
    except HttpError as exc:
        if _http_error_status(exc) != 409:
            raise
        event.pop("id", None)
        updated_event = (
            service.events()
            .update(
                calendarId=calendar_id,
                eventId=target_event_id,
                body=event,
            )
            .execute()
        )
        return updated_event["id"]


def remove_event_from_calendar(
    event_id,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
):
    if not event_id:
        return

    service = authenticate_google_calendar(credentials_path=credentials_path, token_path=token_path)
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as exc:
        if _http_error_status(exc) != 404:
            raise


def _dashboard_request(api_url, api_token, method, path, payload=None, timeout=10):
    if not api_url:
        raise ValueError("Dashboard API URL is required when dashboard sync is enabled.")
    if not api_token:
        raise ValueError("Dashboard API token is required when dashboard sync is enabled.")

    endpoint = f"{api_url.rstrip('/')}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(endpoint, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dashboard API returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Dashboard API request failed: {exc.reason}") from exc

    if not body:
        return {}

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Dashboard API returned invalid JSON.") from exc


def fetch_dashboard_clients(api_url, api_token, timeout=10):
    response = _dashboard_request(
        api_url=api_url,
        api_token=api_token,
        method="GET",
        path="/api/clients",
        timeout=timeout,
    )
    clients = response.get("clients", [])
    names = []
    seen = set()
    for client in clients:
        if isinstance(client, dict):
            name = _normalize_client(client.get("name"))
        else:
            name = _normalize_client(client)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def sync_task_to_dashboard(
    task_id,
    task_name,
    client,
    category,
    billable,
    start_datetime,
    end_datetime,
    timezone,
    hours_worked,
    api_url,
    api_token,
    timeout=10,
):
    payload = {
        "external_id": str(task_id),
        "task": task_name,
        "client": _normalize_client(client),
        "category": _normalize_category(category),
        "start": start_datetime.isoformat(),
        "end": end_datetime.isoformat(),
        "timezone": timezone,
        "decimal_hours": hours_worked,
        "billable": _normalize_billable(billable),
        "source": "task-logger",
    }
    response = _dashboard_request(
        api_url=api_url,
        api_token=api_token,
        method="POST",
        path="/api/time-entries",
        payload=payload,
        timeout=timeout,
    )
    return _safe_cell(response.get("entry", {}).get("id"))


def remove_task_from_dashboard(task_id, api_url, api_token, timeout=10):
    encoded_id = urllib.parse.quote(str(task_id), safe="")
    try:
        _dashboard_request(
            api_url=api_url,
            api_token=api_token,
            method="DELETE",
            path=f"/api/time-entries/{encoded_id}",
            timeout=timeout,
        )
    except RuntimeError as exc:
        if "returned 404" not in str(exc):
            raise


def _configured_sync_status(enabled):
    return SYNC_PENDING if enabled else SYNC_NOT_CONFIGURED


def _sync_result_status(enabled, error):
    if not enabled:
        return SYNC_NOT_CONFIGURED
    return SYNC_ERROR if error else SYNCED


def _delete_result_status(enabled, error):
    if not enabled:
        return SYNC_NOT_CONFIGURED
    return SYNC_DELETE_PENDING if error else SYNCED


def _touch_row(df, row_index):
    df.at[row_index, "Last Modified"] = datetime.now().isoformat(timespec="seconds")


@_serialized_task_log_operation
def add_task_to_log(
    task_name,
    start_date,
    start_time,
    start_period,
    end_date,
    end_time,
    end_period,
    timezone,
    task_log="task_log.xlsx",
    attendees=None,
    sync_to_google=False,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
    client=DEFAULT_CLIENT,
    category=DEFAULT_CATEGORY,
    billable=True,
    sync_to_dashboard=False,
    dashboard_api_url="",
    dashboard_api_token="",
):
    task_name = task_name.strip()
    if not task_name:
        raise ValueError("Task name is required.")

    category = _normalize_category(category)
    client = _normalize_client(client)
    billable = _normalize_billable(billable)
    start_period = start_period.strip().upper()
    end_period = end_period.strip().upper()
    start_time = normalize_12hour_time(start_time)
    end_time = normalize_12hour_time(end_time)
    attendees_list = _normalize_attendees(attendees)

    start_datetime, end_datetime, hours_worked = build_task_datetimes(
        start_date=start_date,
        start_time=start_time,
        start_period=start_period,
        end_date=end_date,
        end_time=end_time,
        end_period=end_period,
        timezone=timezone,
    )

    task_id = str(uuid.uuid4())
    event_id = ""
    dashboard_entry_id = ""
    calendar_error = ""
    dashboard_error = ""

    df = load_task_log(task_log)
    new_row = pd.DataFrame(
        [
            {
                "ID": task_id,
                "Task": task_name,
                "Client": client,
                "Category": category,
                "Start Date": start_date,
                "Start Time": start_time,
                "Start AM/PM": start_period,
                "End Date": end_date,
                "End Time": end_time,
                "End AM/PM": end_period,
                "Timezone": timezone,
                "Decimal Hours": hours_worked,
                "Billable": billable,
                "Event ID": event_id,
                "Dashboard Entry ID": dashboard_entry_id,
                "Attendees": ",".join(attendees_list),
                "Google Sync Status": _configured_sync_status(sync_to_google),
                "Dashboard Sync Status": _configured_sync_status(sync_to_dashboard),
                "Google Sync Error": "",
                "Dashboard Sync Error": "",
                "Last Modified": datetime.now().isoformat(timespec="seconds"),
            }
        ]
    )
    df = new_row if df.empty else pd.concat([df, new_row], ignore_index=True)
    save_task_log(df, task_log)
    row_index = _get_task_row_index(df, task_id)

    if sync_to_google:
        try:
            event_id = sync_event_to_calendar(
                task_id=task_id,
                task_name=task_name,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timezone=timezone,
                attendees=attendees_list,
                credentials_path=credentials_path,
                token_path=token_path,
                calendar_id=calendar_id,
            )
        except Exception as exc:
            calendar_error = str(exc)

    if sync_to_dashboard:
        try:
            dashboard_entry_id = sync_task_to_dashboard(
                task_id=task_id,
                task_name=task_name,
                client=client,
                category=category,
                billable=billable,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timezone=timezone,
                hours_worked=hours_worked,
                api_url=dashboard_api_url,
                api_token=dashboard_api_token,
            )
        except Exception as exc:
            dashboard_error = str(exc)

    df.at[row_index, "Event ID"] = event_id
    df.at[row_index, "Dashboard Entry ID"] = dashboard_entry_id
    df.at[row_index, "Google Sync Status"] = _sync_result_status(sync_to_google, calendar_error)
    df.at[row_index, "Dashboard Sync Status"] = _sync_result_status(sync_to_dashboard, dashboard_error)
    df.at[row_index, "Google Sync Error"] = calendar_error
    df.at[row_index, "Dashboard Sync Error"] = dashboard_error
    _touch_row(df, row_index)
    save_task_log(df, task_log)

    return {
        "task_id": task_id,
        "event_id": event_id,
        "dashboard_entry_id": dashboard_entry_id,
        "hours_worked": hours_worked,
        "billable": billable,
        "calendar_synced": bool(event_id),
        "calendar_error": calendar_error,
        "dashboard_synced": bool(dashboard_entry_id) and sync_to_dashboard,
        "dashboard_error": dashboard_error,
        "sync_pending": bool(calendar_error or dashboard_error),
    }


@_serialized_task_log_operation
def update_task_in_log(
    task_id,
    task_name,
    start_date,
    start_time,
    start_period,
    end_date,
    end_time,
    end_period,
    timezone,
    task_log="task_log.xlsx",
    attendees=None,
    sync_to_google=False,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
    client=None,
    category=None,
    billable=None,
    sync_to_dashboard=False,
    dashboard_api_url="",
    dashboard_api_token="",
):
    task_name = task_name.strip()
    if not task_name:
        raise ValueError("Task name is required.")

    start_period = start_period.strip().upper()
    end_period = end_period.strip().upper()
    start_time = normalize_12hour_time(start_time)
    end_time = normalize_12hour_time(end_time)
    attendees_list = _normalize_attendees(attendees)

    start_datetime, end_datetime, hours_worked = build_task_datetimes(
        start_date=start_date,
        start_time=start_time,
        start_period=start_period,
        end_date=end_date,
        end_time=end_time,
        end_period=end_period,
        timezone=timezone,
    )

    df = load_task_log(task_log)
    df = df.astype("object")
    row_index = _get_task_row_index(df, task_id)
    client = _normalize_client(client if client is not None else df.at[row_index, "Client"])
    category = _normalize_category(category if category is not None else df.at[row_index, "Category"])
    billable = _normalize_billable(billable if billable is not None else df.at[row_index, "Billable"])
    existing_event_id = _safe_cell(df.at[row_index, "Event ID"])
    existing_dashboard_entry_id = _safe_cell(df.at[row_index, "Dashboard Entry ID"])
    new_event_id = existing_event_id
    new_dashboard_entry_id = existing_dashboard_entry_id
    calendar_error = ""
    dashboard_error = ""

    df.loc[
        row_index,
        [
            "Task",
            "Client",
            "Category",
            "Start Date",
            "Start Time",
            "Start AM/PM",
            "End Date",
            "End Time",
            "End AM/PM",
            "Timezone",
            "Decimal Hours",
            "Billable",
            "Event ID",
            "Dashboard Entry ID",
            "Attendees",
            "Google Sync Status",
            "Dashboard Sync Status",
            "Google Sync Error",
            "Dashboard Sync Error",
            "Last Modified",
        ],
    ] = [
        task_name,
        client,
        category,
        start_date,
        start_time,
        start_period,
        end_date,
        end_time,
        end_period,
        timezone,
        hours_worked,
        billable,
        existing_event_id,
        existing_dashboard_entry_id,
        ",".join(attendees_list),
        _configured_sync_status(sync_to_google),
        _configured_sync_status(sync_to_dashboard),
        "",
        "",
        datetime.now().isoformat(timespec="seconds"),
    ]
    save_task_log(df, task_log)

    if sync_to_google:
        try:
            new_event_id = sync_event_to_calendar(
                task_id=task_id,
                task_name=task_name,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timezone=timezone,
                attendees=attendees_list,
                event_id=existing_event_id,
                credentials_path=credentials_path,
                token_path=token_path,
                calendar_id=calendar_id,
            )
        except Exception as exc:
            calendar_error = str(exc)

    if sync_to_dashboard:
        try:
            synced_dashboard_entry_id = sync_task_to_dashboard(
                task_id=task_id,
                task_name=task_name,
                client=client,
                category=category,
                billable=billable,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timezone=timezone,
                hours_worked=hours_worked,
                api_url=dashboard_api_url,
                api_token=dashboard_api_token,
            )
            new_dashboard_entry_id = synced_dashboard_entry_id or existing_dashboard_entry_id
        except Exception as exc:
            dashboard_error = str(exc)

    df.at[row_index, "Event ID"] = new_event_id
    df.at[row_index, "Dashboard Entry ID"] = new_dashboard_entry_id
    df.at[row_index, "Google Sync Status"] = _sync_result_status(sync_to_google, calendar_error)
    df.at[row_index, "Dashboard Sync Status"] = _sync_result_status(sync_to_dashboard, dashboard_error)
    df.at[row_index, "Google Sync Error"] = calendar_error
    df.at[row_index, "Dashboard Sync Error"] = dashboard_error
    _touch_row(df, row_index)
    save_task_log(df, task_log)

    return {
        "task_id": str(task_id),
        "event_id": new_event_id,
        "dashboard_entry_id": new_dashboard_entry_id,
        "hours_worked": hours_worked,
        "billable": billable,
        "calendar_synced": bool(new_event_id) and sync_to_google,
        "calendar_error": calendar_error,
        "dashboard_synced": bool(new_dashboard_entry_id) and sync_to_dashboard,
        "dashboard_error": dashboard_error,
        "sync_pending": bool(calendar_error or dashboard_error),
    }


@_serialized_task_log_operation
def remove_task_from_log(
    task_id,
    task_log="task_log.xlsx",
    sync_to_google=False,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
    sync_to_dashboard=False,
    dashboard_api_url="",
    dashboard_api_token="",
):
    df = load_task_log(task_log)
    row_index = _get_task_row_index(df, task_id)
    event_id = _safe_cell(df.at[row_index, "Event ID"])
    dashboard_entry_id = _safe_cell(df.at[row_index, "Dashboard Entry ID"])
    calendar_error = ""
    dashboard_error = ""

    if sync_to_google:
        df.at[row_index, "Google Sync Status"] = SYNC_DELETE_PENDING
        df.at[row_index, "Google Sync Error"] = ""
    if sync_to_dashboard:
        df.at[row_index, "Dashboard Sync Status"] = SYNC_DELETE_PENDING
        df.at[row_index, "Dashboard Sync Error"] = ""
    _touch_row(df, row_index)
    save_task_log(df, task_log)

    if sync_to_google and event_id:
        try:
            remove_event_from_calendar(
                event_id=event_id,
                credentials_path=credentials_path,
                token_path=token_path,
                calendar_id=calendar_id,
            )
        except Exception as exc:
            calendar_error = str(exc)

    if sync_to_dashboard:
        try:
            remove_task_from_dashboard(
                task_id=task_id,
                api_url=dashboard_api_url,
                api_token=dashboard_api_token,
            )
        except Exception as exc:
            dashboard_error = str(exc)

    if calendar_error or dashboard_error:
        df.at[row_index, "Google Sync Status"] = _delete_result_status(sync_to_google, calendar_error)
        df.at[row_index, "Dashboard Sync Status"] = _delete_result_status(sync_to_dashboard, dashboard_error)
        df.at[row_index, "Google Sync Error"] = calendar_error
        df.at[row_index, "Dashboard Sync Error"] = dashboard_error
        _touch_row(df, row_index)
        save_task_log(df, task_log)
        return {
            "task_id": str(task_id),
            "event_id": event_id,
            "dashboard_entry_id": dashboard_entry_id,
            "calendar_error": calendar_error,
            "dashboard_error": dashboard_error,
            "deleted": False,
            "delete_pending": True,
        }

    df = df.drop(row_index).reset_index(drop=True)
    save_task_log(df, task_log)

    return {
        "task_id": str(task_id),
        "event_id": event_id,
        "dashboard_entry_id": dashboard_entry_id,
        "calendar_error": calendar_error,
        "dashboard_error": dashboard_error,
        "deleted": True,
        "delete_pending": False,
    }


def task_sync_summary(row):
    google_status = _normalize_sync_status(row.get("Google Sync Status"))
    dashboard_status = _normalize_sync_status(row.get("Dashboard Sync Status"))
    statuses = {google_status, dashboard_status}

    if SYNC_DELETE_PENDING in statuses:
        return "Delete pending"
    if SYNC_ERROR in statuses:
        failed = []
        if google_status == SYNC_ERROR:
            failed.append("Calendar")
        if dashboard_status == SYNC_ERROR:
            failed.append("Dashboard")
        return f"{' + '.join(failed)} error"
    if SYNC_PENDING in statuses:
        return "Sync pending"
    if SYNCED in statuses:
        return "Synced"
    return "Local only"


def sync_retry_action(row):
    google_actionable = _normalize_sync_status(row.get("Google Sync Status")) in ACTIONABLE_SYNC_STATUSES
    dashboard_actionable = _normalize_sync_status(row.get("Dashboard Sync Status")) in ACTIONABLE_SYNC_STATUSES

    if google_actionable and dashboard_actionable:
        return "Retry Sync"
    if google_actionable:
        return "Retry Calendar Sync"
    if dashboard_actionable:
        return "Retry Dashboard Sync"
    return None


def _date_input_text(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return _safe_cell(value)[:10]


@_serialized_task_log_operation
def retry_task_sync(
    task_id,
    task_log="task_log.xlsx",
    sync_to_google=False,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
    sync_to_dashboard=False,
    dashboard_api_url="",
    dashboard_api_token="",
):
    df = load_task_log(task_log)
    row_index = _get_task_row_index(df, task_id)
    row = df.loc[row_index]
    google_status = _normalize_sync_status(row.get("Google Sync Status"))
    dashboard_status = _normalize_sync_status(row.get("Dashboard Sync Status"))
    statuses = {google_status, dashboard_status}

    if SYNC_DELETE_PENDING in statuses:
        return remove_task_from_log(
            task_id=task_id,
            task_log=task_log,
            sync_to_google=google_status == SYNC_DELETE_PENDING,
            credentials_path=credentials_path,
            token_path=token_path,
            calendar_id=calendar_id,
            sync_to_dashboard=dashboard_status == SYNC_DELETE_PENDING,
            dashboard_api_url=dashboard_api_url,
            dashboard_api_token=dashboard_api_token,
        )

    retry_google = sync_to_google or google_status in ACTIONABLE_SYNC_STATUSES
    retry_dashboard = sync_to_dashboard or dashboard_status in ACTIONABLE_SYNC_STATUSES

    return update_task_in_log(
        task_id=task_id,
        task_name=_safe_cell(row.get("Task")),
        client=_safe_cell(row.get("Client")),
        category=_safe_cell(row.get("Category")),
        billable=_normalize_billable(row.get("Billable")),
        start_date=_date_input_text(row.get("Start Date")),
        start_time=_safe_cell(row.get("Start Time")),
        start_period=_safe_cell(row.get("Start AM/PM")),
        end_date=_date_input_text(row.get("End Date")),
        end_time=_safe_cell(row.get("End Time")),
        end_period=_safe_cell(row.get("End AM/PM")),
        timezone=_safe_cell(row.get("Timezone")),
        task_log=task_log,
        attendees=_safe_cell(row.get("Attendees")),
        sync_to_google=retry_google,
        credentials_path=credentials_path,
        token_path=token_path,
        calendar_id=calendar_id,
        sync_to_dashboard=retry_dashboard,
        dashboard_api_url=dashboard_api_url,
        dashboard_api_token=dashboard_api_token,
    )


def main():
    task_log = "task_log.xlsx"
    ensure_task_log_exists(task_log)

    while True:
        task_name = input("Enter task name: ").strip()
        client = input(f"Enter client (default {DEFAULT_CLIENT}): ").strip() or DEFAULT_CLIENT
        category = input(f"Enter category (default {DEFAULT_CATEGORY}): ").strip() or DEFAULT_CATEGORY
        billable_input = input("Billable? (Y/n): ").strip().lower()
        billable = billable_input not in {"n", "no", "false", "0"}
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        start_time = input("Enter start time (HH:MM): ").strip()
        start_period = input("Enter start time period (AM/PM): ").strip().upper()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()
        end_time = input("Enter end time (HH:MM): ").strip()
        end_period = input("Enter end time period (AM/PM): ").strip().upper()
        timezone = input("Enter timezone (e.g., America/Detroit): ").strip()
        attendees_input = input("Enter attendees (comma separated emails, optional): ").strip()

        attendees = attendees_input.split(",") if attendees_input else []
        result = add_task_to_log(
            task_name=task_name,
            client=client,
            category=category,
            billable=billable,
            start_date=start_date,
            start_time=start_time,
            start_period=start_period,
            end_date=end_date,
            end_time=end_time,
            end_period=end_period,
            timezone=timezone,
            task_log=task_log,
            attendees=attendees,
            sync_to_google=False,
        )
        print(f"Task added. Hours: {result['hours_worked']}")


if __name__ == "__main__":
    main()
