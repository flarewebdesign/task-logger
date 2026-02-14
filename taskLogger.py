# taskLogger.py

from datetime import datetime, timedelta
import json
import os
import uuid
from typing import Iterable

import pandas as pd
import pytz

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


TASK_COLUMNS = [
    "ID",
    "Task",
    "Start Date",
    "Start Time",
    "Start AM/PM",
    "End Date",
    "End Time",
    "End AM/PM",
    "Timezone",
    "Decimal Hours",
    "Event ID",
    "Attendees",
]

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


def _harden_file_permissions(file_path):
    try:
        if os.name == "posix":
            os.chmod(file_path, 0o600)
    except OSError:
        pass


def ensure_task_log_exists(task_log="task_log.xlsx"):
    if not os.path.exists(task_log):
        pd.DataFrame(columns=TASK_COLUMNS).to_excel(task_log, index=False)


def load_task_log(task_log="task_log.xlsx"):
    ensure_task_log_exists(task_log)
    try:
        df = pd.read_excel(task_log)
    except Exception:
        df = pd.DataFrame(columns=TASK_COLUMNS)
        save_task_log(df, task_log)
        return df

    if list(df.columns) != TASK_COLUMNS:
        repaired = pd.DataFrame(columns=TASK_COLUMNS)
        for column in TASK_COLUMNS:
            if column in df.columns:
                repaired[column] = df[column]
        df = repaired
        save_task_log(df, task_log)

    return df


def save_task_log(df, task_log="task_log.xlsx"):
    df.to_excel(task_log, index=False)


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

    start_datetime = tz.localize(start_naive)
    end_datetime = tz.localize(end_naive)

    if end_datetime < start_datetime:
        end_datetime += timedelta(days=1)

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
        with open(token_path, "r", encoding="utf-8") as token_file:
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
            _harden_file_permissions(token_path)

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
    service = authenticate_google_calendar(credentials_path=credentials_path, token_path=token_path)

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

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created_event["id"]


def remove_event_from_calendar(
    event_id,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
):
    if not event_id:
        return

    service = authenticate_google_calendar(credentials_path=credentials_path, token_path=token_path)
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


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

    task_id = str(uuid.uuid4())
    event_id = ""
    calendar_error = ""

    if sync_to_google:
        try:
            event_id = add_event_to_calendar(
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

    df = load_task_log(task_log)
    new_row = pd.DataFrame(
        [
            {
                "ID": task_id,
                "Task": task_name,
                "Start Date": start_date,
                "Start Time": start_time,
                "Start AM/PM": start_period,
                "End Date": end_date,
                "End Time": end_time,
                "End AM/PM": end_period,
                "Timezone": timezone,
                "Decimal Hours": hours_worked,
                "Event ID": event_id,
                "Attendees": ",".join(attendees_list),
            }
        ]
    )
    df = pd.concat([df, new_row], ignore_index=True)
    save_task_log(df, task_log)

    return {
        "task_id": task_id,
        "event_id": event_id,
        "hours_worked": hours_worked,
        "calendar_synced": bool(event_id),
        "calendar_error": calendar_error,
    }


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
    row_index = _get_task_row_index(df, task_id)
    existing_event_id = _safe_cell(df.at[row_index, "Event ID"])
    new_event_id = existing_event_id
    calendar_error = ""

    if sync_to_google:
        try:
            new_event_id = add_event_to_calendar(
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
            if existing_event_id and existing_event_id != new_event_id:
                try:
                    remove_event_from_calendar(
                        event_id=existing_event_id,
                        credentials_path=credentials_path,
                        token_path=token_path,
                        calendar_id=calendar_id,
                    )
                except Exception:
                    pass
        except Exception as exc:
            calendar_error = str(exc)

    df.loc[
        row_index,
        [
            "Task",
            "Start Date",
            "Start Time",
            "Start AM/PM",
            "End Date",
            "End Time",
            "End AM/PM",
            "Timezone",
            "Decimal Hours",
            "Event ID",
            "Attendees",
        ],
    ] = [
        task_name,
        start_date,
        start_time,
        start_period,
        end_date,
        end_time,
        end_period,
        timezone,
        hours_worked,
        new_event_id,
        ",".join(attendees_list),
    ]
    save_task_log(df, task_log)

    return {
        "task_id": str(task_id),
        "event_id": new_event_id,
        "hours_worked": hours_worked,
        "calendar_synced": bool(new_event_id) and sync_to_google,
        "calendar_error": calendar_error,
    }


def remove_task_from_log(
    task_id,
    task_log="task_log.xlsx",
    sync_to_google=False,
    credentials_path="credentials.json",
    token_path="token.json",
    calendar_id="primary",
):
    df = load_task_log(task_log)
    row_index = _get_task_row_index(df, task_id)
    event_id = _safe_cell(df.at[row_index, "Event ID"])
    calendar_error = ""

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

    df = df.drop(row_index).reset_index(drop=True)
    save_task_log(df, task_log)

    return {
        "task_id": str(task_id),
        "event_id": event_id,
        "calendar_error": calendar_error,
    }


def main():
    task_log = "task_log.xlsx"
    ensure_task_log_exists(task_log)

    while True:
        task_name = input("Enter task name: ").strip()
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
