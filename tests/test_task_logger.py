from pathlib import Path

import pandas as pd
import pytest

import taskLogger


def task_values(**overrides):
    values = {
        "task_name": "Test task",
        "client": "Test client",
        "category": "Development",
        "billable": True,
        "start_date": "2026-07-10",
        "start_time": "09:00",
        "start_period": "AM",
        "end_date": "2026-07-10",
        "end_time": "10:30",
        "end_period": "AM",
        "timezone": "America/Detroit",
        "attendees": ["test@example.com"],
    }
    values.update(overrides)
    return values


def test_excel_crud_preserves_sync_metadata_and_backup(tmp_path):
    workbook = tmp_path / "task_log.xlsx"

    created = taskLogger.add_task_to_log(task_log=workbook, **task_values())
    loaded = taskLogger.load_task_log(workbook)

    assert len(loaded) == 1
    assert loaded.iloc[0]["Google Sync Status"] == taskLogger.SYNC_NOT_CONFIGURED
    assert loaded.iloc[0]["Dashboard Sync Status"] == taskLogger.SYNC_NOT_CONFIGURED
    assert (tmp_path / "task_log.backup.xlsx").exists()

    updated = taskLogger.update_task_in_log(
        task_id=created["task_id"],
        task_log=workbook,
        **task_values(task_name="Updated task", end_time="11:00"),
    )
    assert updated["hours_worked"] == 2.0
    assert taskLogger.load_task_log(workbook).iloc[0]["Task"] == "Updated task"

    removed = taskLogger.remove_task_from_log(created["task_id"], task_log=workbook)
    assert removed["deleted"] is True
    assert taskLogger.load_task_log(workbook).empty


def test_corrupt_workbook_is_preserved_and_not_overwritten(tmp_path):
    workbook = tmp_path / "task_log.xlsx"
    original = b"not an excel workbook"
    workbook.write_bytes(original)

    with pytest.raises(taskLogger.TaskLogRecoveryError) as error:
        taskLogger.load_task_log(workbook)

    recovery = Path(error.value.recovery_path)
    assert workbook.read_bytes() == original
    assert recovery.read_bytes() == original


def test_dashboard_failure_is_durable_and_retryable(tmp_path, monkeypatch):
    workbook = tmp_path / "task_log.xlsx"

    def fail_sync(**_kwargs):
        raise RuntimeError("dashboard unavailable")

    monkeypatch.setattr(taskLogger, "sync_task_to_dashboard", fail_sync)
    created = taskLogger.add_task_to_log(
        task_log=workbook,
        sync_to_dashboard=True,
        dashboard_api_url="https://example.test",
        dashboard_api_token="token",
        **task_values(),
    )

    failed_row = taskLogger.load_task_log(workbook).iloc[0]
    assert created["sync_pending"] is True
    assert failed_row["Dashboard Sync Status"] == taskLogger.SYNC_ERROR
    assert "dashboard unavailable" in failed_row["Dashboard Sync Error"]

    monkeypatch.setattr(taskLogger, "sync_task_to_dashboard", lambda **_kwargs: "dashboard-entry")
    retried = taskLogger.retry_task_sync(
        created["task_id"],
        task_log=workbook,
        sync_to_dashboard=False,
        dashboard_api_url="https://example.test",
        dashboard_api_token="token",
    )

    synced_row = taskLogger.load_task_log(workbook).iloc[0]
    assert retried["dashboard_synced"] is True
    assert synced_row["Dashboard Sync Status"] == taskLogger.SYNCED
    assert synced_row["Dashboard Sync Error"] == ""


@pytest.mark.parametrize(
    ("google_status", "dashboard_status"),
    [
        (taskLogger.SYNC_NOT_CONFIGURED, taskLogger.SYNC_NOT_CONFIGURED),
        (taskLogger.SYNCED, taskLogger.SYNCED),
        (taskLogger.SYNCED, taskLogger.SYNC_NOT_CONFIGURED),
    ],
)
def test_sync_retry_action_is_hidden_without_actionable_sync_state(google_status, dashboard_status):
    action = taskLogger.sync_retry_action(
        {
            "Google Sync Status": google_status,
            "Dashboard Sync Status": dashboard_status,
        }
    )

    assert action is None


@pytest.mark.parametrize(
    ("google_status", "dashboard_status", "label"),
    [
        (taskLogger.SYNC_ERROR, taskLogger.SYNCED, "Retry Calendar Sync"),
        (taskLogger.SYNC_PENDING, taskLogger.SYNC_NOT_CONFIGURED, "Retry Calendar Sync"),
        (taskLogger.SYNCED, taskLogger.SYNC_ERROR, "Retry Dashboard Sync"),
        (taskLogger.SYNC_NOT_CONFIGURED, taskLogger.SYNC_DELETE_PENDING, "Retry Dashboard Sync"),
        (taskLogger.SYNC_ERROR, taskLogger.SYNC_PENDING, "Retry Sync"),
    ],
)
def test_sync_retry_action_uses_provider_specific_label(google_status, dashboard_status, label):
    action = taskLogger.sync_retry_action(
        {
            "Google Sync Status": google_status,
            "Dashboard Sync Status": dashboard_status,
        }
    )

    assert action == label


def test_delete_failure_keeps_excel_row_for_retry(tmp_path, monkeypatch):
    workbook = tmp_path / "task_log.xlsx"
    created = taskLogger.add_task_to_log(task_log=workbook, **task_values())

    monkeypatch.setattr(
        taskLogger,
        "remove_task_from_dashboard",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("delete failed")),
    )
    result = taskLogger.remove_task_from_log(
        created["task_id"],
        task_log=workbook,
        sync_to_dashboard=True,
        dashboard_api_url="https://example.test",
        dashboard_api_token="token",
    )

    row = taskLogger.load_task_log(workbook).iloc[0]
    assert result["delete_pending"] is True
    assert row["Dashboard Sync Status"] == taskLogger.SYNC_DELETE_PENDING
    assert "delete failed" in row["Dashboard Sync Error"]

    delete_calls = []

    def successful_delete(*_args, **_kwargs):
        delete_calls.append(True)

    monkeypatch.setattr(taskLogger, "remove_task_from_dashboard", successful_delete)
    retried = taskLogger.retry_task_sync(
        created["task_id"],
        task_log=workbook,
        sync_to_dashboard=False,
        dashboard_api_url="https://example.test",
        dashboard_api_token="token",
    )

    assert retried["deleted"] is True
    assert delete_calls == [True]
    assert taskLogger.load_task_log(workbook).empty


@pytest.mark.parametrize(
    ("start_date", "start_time", "message"),
    [
        ("2026-03-08", "02:30", "does not exist"),
        ("2026-11-01", "01:30", "occurs twice"),
    ],
)
def test_dst_edge_cases_are_explained(start_date, start_time, message):
    with pytest.raises(ValueError, match=message):
        taskLogger.build_task_datetimes(
            start_date=start_date,
            start_time=start_time,
            start_period="AM",
            end_date=start_date,
            end_time="03:30" if "exist" in message else "02:30",
            end_period="AM",
            timezone="America/Detroit",
        )


def test_end_date_before_start_is_rejected():
    with pytest.raises(ValueError, match="must be after"):
        taskLogger.build_task_datetimes(
            start_date="2026-07-10",
            start_time="09:00",
            start_period="AM",
            end_date="2026-07-09",
            end_time="10:00",
            end_period="AM",
            timezone="America/Detroit",
        )


def test_existing_workbook_schema_is_migrated_with_backup(tmp_path):
    workbook = tmp_path / "task_log.xlsx"
    pd.DataFrame([{"ID": "legacy", "Task": "Legacy task"}]).to_excel(workbook, index=False)

    migrated = taskLogger.load_task_log(workbook)

    assert list(migrated.columns) == taskLogger.TASK_COLUMNS
    assert migrated.iloc[0]["Task"] == "Legacy task"
    assert (tmp_path / "task_log.backup.xlsx").exists()


def test_existing_external_ids_backfill_synced_statuses(tmp_path):
    workbook = tmp_path / "task_log.xlsx"
    legacy = pd.DataFrame(
        [
            {
                "ID": "dashboard-task",
                "Task": "Dashboard task",
                "Dashboard Entry ID": "tl_dashboard",
                "Dashboard Sync Status": taskLogger.SYNC_NOT_CONFIGURED,
            },
            {
                "ID": "calendar-task",
                "Task": "Calendar task",
                "Event ID": "calendar-event",
                "Google Sync Status": taskLogger.SYNC_NOT_CONFIGURED,
            },
        ],
        columns=taskLogger.TASK_COLUMNS,
    )
    legacy.to_excel(workbook, index=False)

    migrated = taskLogger.load_task_log(workbook)

    assert migrated.iloc[0]["Dashboard Sync Status"] == taskLogger.SYNCED
    assert migrated.iloc[1]["Google Sync Status"] == taskLogger.SYNCED
    assert (tmp_path / "task_log.backup.xlsx").exists()
