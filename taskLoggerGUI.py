# taskLoggerGUI.py - Unified GUI for task logging and management

import datetime
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pytz

import taskLogger
from taskListGUI import TaskListPanel
from ui_date_picker import open_date_picker


CONFIG_FILE = "config.json"
TASK_LOG_FILE = "task_log.xlsx"
COMMON_TIMEZONES = pytz.common_timezones
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_CATEGORIES = ["Development", "Design", "Admin", "Support", "Meetings"]
DEFAULT_CLIENTS = [taskLogger.DEFAULT_CLIENT]


def _default_token_path():
    return os.path.join(os.path.expanduser("~"), ".task_logger", "token.json")


DEFAULT_CONFIG = {
    "timezone": "UTC",
    "categories": DEFAULT_CATEGORIES,
    "clients": DEFAULT_CLIENTS,
    "google_sync_enabled": False,
    "google_credentials_path": "credentials.json",
    "google_token_path": _default_token_path(),
    "google_calendar_id": "primary",
    "dashboard_sync_enabled": False,
    "dashboard_api_url": "http://localhost:3000",
    "dashboard_api_token": "",
}


def load_config():
    config = DEFAULT_CONFIG.copy()

    if not os.path.exists(CONFIG_FILE):
        save_config(config)
        return config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            user_config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        save_config(config)
        return config

    for key, default_value in DEFAULT_CONFIG.items():
        if key in user_config:
            config[key] = user_config[key]
        else:
            config[key] = default_value

    if config["timezone"] not in pytz.all_timezones:
        config["timezone"] = "UTC"
    config["categories"] = _normalize_categories(config.get("categories"))
    config["clients"] = _normalize_clients(config.get("clients"))
    config["google_sync_enabled"] = bool(config["google_sync_enabled"])
    config["dashboard_sync_enabled"] = bool(config["dashboard_sync_enabled"])
    if not str(config["google_token_path"]).strip():
        config["google_token_path"] = _default_token_path()
    if not str(config["google_calendar_id"]).strip():
        config["google_calendar_id"] = "primary"
    if not str(config["google_credentials_path"]).strip():
        config["google_credentials_path"] = "credentials.json"
    if not str(config["dashboard_api_url"]).strip():
        config["dashboard_api_url"] = "http://localhost:3000"

    return config


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)


def _normalize_categories(value):
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, list):
        raw_values = value
    else:
        raw_values = DEFAULT_CATEGORIES

    categories = []
    seen = set()
    for item in raw_values:
        category = str(item).strip()
        if not category:
            continue
        key = category.lower()
        if key in seen:
            continue
        seen.add(key)
        categories.append(category)

    return categories or DEFAULT_CATEGORIES.copy()


def _normalize_clients(value):
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, list):
        raw_values = value
    else:
        raw_values = DEFAULT_CLIENTS

    clients = []
    seen = set()
    for item in raw_values:
        client = str(item).strip()
        if not client:
            continue
        key = client.lower()
        if key in seen:
            continue
        seen.add(key)
        clients.append(client)

    return clients or DEFAULT_CLIENTS.copy()


class TaskLoggerApp:
    def __init__(self):
        ctk.set_appearance_mode("system")

        self.config = load_config()
        taskLogger.ensure_task_log_exists(TASK_LOG_FILE)

        self.root = ctk.CTk()
        self.root.title("Task Logger")
        self.root.geometry("1120x700")
        self.root.minsize(980, 620)

        self.status_var = tk.StringVar(value="Ready.")
        self._build_ui()
        self._clear_form()

    def _build_ui(self):
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 10))

        title = ctk.CTkLabel(header, text="Task Logger", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Track local time, billable state, clients, and optional sync targets.",
            text_color=("gray35", "gray70"),
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.log_tab = self.tabview.add("Log Task")
        self.tasks_tab = self.tabview.add("Task List")
        self.settings_tab = self.tabview.add("Settings")

        self._build_log_tab()
        self._build_tasks_tab()
        self._build_settings_tab()

        status_bar = ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            fg_color=("gray88", "gray18"),
            corner_radius=8,
            padx=10,
            pady=6,
        )
        status_bar.pack(fill="x", padx=20, pady=(0, 14))

    def _build_log_tab(self):
        form = ctk.CTkFrame(self.log_tab)
        form.pack(fill="both", expand=True, padx=12, pady=12)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)

        self.task_name_entry = ctk.CTkEntry(form, placeholder_text="Task name")
        self._place_field(form, 0, "Task Name", self.task_name_entry, column=0)

        self.client_combobox = ctk.CTkComboBox(form, values=self._client_values())
        self._place_field(form, 0, "Client", self.client_combobox, column=2)

        self.start_date_entry = self._create_date_field(
            parent=form,
            row=1,
            label_text="Start Date",
            column=0,
            picker_title="Pick Start Date",
        )

        self.start_time_entry = ctk.CTkEntry(form, placeholder_text="HH:MM")
        self._place_field(form, 2, "Start Time", self.start_time_entry, column=0)

        self.start_period_menu = ctk.CTkOptionMenu(form, values=["AM", "PM"])
        self._place_field(form, 3, "Start AM/PM", self.start_period_menu, column=0)

        self.end_date_entry = self._create_date_field(
            parent=form,
            row=1,
            label_text="End Date",
            column=2,
            picker_title="Pick End Date",
        )

        self.end_time_entry = ctk.CTkEntry(form, placeholder_text="HH:MM")
        self._place_field(form, 2, "End Time", self.end_time_entry, column=2)

        self.end_period_menu = ctk.CTkOptionMenu(form, values=["AM", "PM"])
        self._place_field(form, 3, "End AM/PM", self.end_period_menu, column=2)

        self.timezone_combobox = ctk.CTkComboBox(form, values=COMMON_TIMEZONES)
        self._place_field(form, 4, "Timezone", self.timezone_combobox, column=0)

        self.attendees_entry = ctk.CTkEntry(form, placeholder_text="name@example.com, another@example.com")
        self._place_field(form, 4, "Attendees", self.attendees_entry, column=2)

        self.category_combobox = ctk.CTkComboBox(form, values=self._category_values())
        self._place_field(form, 5, "Category", self.category_combobox, column=0)

        self.billable_var = tk.BooleanVar(value=True)
        self.billable_checkbox = ctk.CTkCheckBox(
            form,
            text="Billable",
            variable=self.billable_var,
            onvalue=True,
            offvalue=False,
        )
        self._place_field(form, 5, "Billing", self.billable_checkbox, column=2)

        hint = ctk.CTkLabel(
            form,
            text="Tip: Use 12-hour time (HH:MM) with AM/PM. Calendar and dashboard sync are optional in Settings.",
            text_color=("gray35", "gray70"),
        )
        hint.grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 0))

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=7, column=0, columnspan=4, sticky="w", pady=(16, 0))

        self.add_task_button = ctk.CTkButton(
            button_row,
            text="Save Task",
            command=self._add_task,
            fg_color="#2F8A42",
            hover_color="#246A32",
            width=130,
        )
        self.add_task_button.pack(side="left", padx=(0, 10))

        clear_button = ctk.CTkButton(
            button_row,
            text="Clear Form",
            command=self._clear_form,
            fg_color=("gray78", "gray25"),
            text_color=("black", "white"),
            hover_color=("gray70", "gray30"),
            width=130,
        )
        clear_button.pack(side="left")

    def _build_tasks_tab(self):
        self.task_list_panel = TaskListPanel(
            self.tasks_tab,
            get_config=self.get_runtime_config,
            task_log=TASK_LOG_FILE,
            on_task_changed=self._on_tasks_changed,
        )
        self.task_list_panel.pack(fill="both", expand=True)

    def _build_settings_tab(self):
        settings = ctk.CTkScrollableFrame(self.settings_tab)
        settings.pack(fill="both", expand=True, padx=12, pady=12)
        settings.grid_columnconfigure(1, weight=1)

        self.default_timezone_combo = ctk.CTkComboBox(settings, values=COMMON_TIMEZONES)
        self.default_timezone_combo.set(self.config["timezone"])
        self._place_settings_field(settings, 0, "Default Timezone", self.default_timezone_combo)

        self.categories_entry = ctk.CTkEntry(settings)
        self.categories_entry.insert(0, ", ".join(self.config["categories"]))
        self._place_settings_field(settings, 1, "Categories", self.categories_entry)

        clients_row = ctk.CTkFrame(settings, fg_color="transparent")
        clients_row.grid(row=2, column=1, sticky="ew", pady=(0, 10))
        clients_row.grid_columnconfigure(0, weight=1)
        self.clients_entry = ctk.CTkEntry(clients_row)
        self.clients_entry.insert(0, ", ".join(self.config["clients"]))
        self.clients_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        load_clients_button = ctk.CTkButton(
            clients_row,
            text="Import From Dashboard",
            width=160,
            command=self._load_clients_from_dashboard,
        )
        load_clients_button.grid(row=0, column=1)
        clients_note = ctk.CTkLabel(
            clients_row,
            text="Local clients are used by default. Dashboard import only copies names into this list.",
            text_color=("gray35", "gray70"),
            justify="left",
        )
        clients_note.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        clients_label = ctk.CTkLabel(settings, text="Clients")
        clients_label.grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 10))

        self.google_sync_var = tk.BooleanVar(value=bool(self.config["google_sync_enabled"]))
        self.google_sync_switch = ctk.CTkSwitch(
            settings,
            text="Enable Google Calendar Sync",
            variable=self.google_sync_var,
            onvalue=True,
            offvalue=False,
        )
        self.google_sync_switch.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 12))

        creds_row = ctk.CTkFrame(settings, fg_color="transparent")
        creds_row.grid(row=4, column=1, sticky="ew", pady=(0, 10))
        creds_row.grid_columnconfigure(0, weight=1)
        self.credentials_entry = ctk.CTkEntry(creds_row)
        self.credentials_entry.insert(0, self.config["google_credentials_path"])
        self.credentials_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        creds_browse = ctk.CTkButton(creds_row, text="Browse", width=90, command=self._browse_credentials)
        creds_browse.grid(row=0, column=1)
        creds_label = ctk.CTkLabel(settings, text="Credentials File")
        creds_label.grid(row=4, column=0, sticky="w", padx=(0, 10), pady=(0, 10))

        token_row = ctk.CTkFrame(settings, fg_color="transparent")
        token_row.grid(row=5, column=1, sticky="ew", pady=(0, 10))
        token_row.grid_columnconfigure(0, weight=1)
        self.token_entry = ctk.CTkEntry(token_row)
        self.token_entry.insert(0, self.config["google_token_path"])
        self.token_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        token_browse = ctk.CTkButton(token_row, text="Browse", width=90, command=self._browse_token)
        token_browse.grid(row=0, column=1)
        token_label = ctk.CTkLabel(settings, text="Token Storage File")
        token_label.grid(row=5, column=0, sticky="w", padx=(0, 10), pady=(0, 10))

        self.calendar_id_entry = ctk.CTkEntry(settings)
        self.calendar_id_entry.insert(0, self.config["google_calendar_id"])
        self._place_settings_field(settings, 6, "Calendar ID", self.calendar_id_entry)

        self.dashboard_sync_var = tk.BooleanVar(value=bool(self.config["dashboard_sync_enabled"]))
        self.dashboard_sync_switch = ctk.CTkSwitch(
            settings,
            text="Enable Dashboard Sync",
            variable=self.dashboard_sync_var,
            onvalue=True,
            offvalue=False,
        )
        self.dashboard_sync_switch.grid(row=7, column=0, columnspan=2, sticky="w", pady=(14, 12))

        self.dashboard_url_entry = ctk.CTkEntry(settings)
        self.dashboard_url_entry.insert(0, self.config["dashboard_api_url"])
        self._place_settings_field(settings, 8, "Dashboard URL", self.dashboard_url_entry)

        self.dashboard_token_entry = ctk.CTkEntry(settings, show="*")
        self.dashboard_token_entry.insert(0, self.config["dashboard_api_token"])
        self._place_settings_field(settings, 9, "Dashboard API Token", self.dashboard_token_entry)

        security_note = ctk.CTkLabel(
            settings,
            text=(
                "Security note: credentials, OAuth tokens, and dashboard API tokens are stored locally. "
                "Do not commit config.json or token files."
            ),
            text_color=("gray35", "gray70"),
            wraplength=760,
            justify="left",
        )
        security_note.grid(row=10, column=0, columnspan=2, sticky="w", pady=(6, 0))

        actions = ctk.CTkFrame(settings, fg_color="transparent")
        actions.grid(row=11, column=0, columnspan=2, sticky="w", pady=(16, 0))

        save_button = ctk.CTkButton(actions, text="Save Settings", command=self._save_settings_clicked, width=130)
        save_button.pack(side="left", padx=(0, 10))

        connect_button = ctk.CTkButton(
            actions,
            text="Connect Google",
            command=self._connect_google,
            fg_color="#1F6AA5",
            hover_color="#17517E",
            width=130,
        )
        connect_button.pack(side="left")

    def _place_field(self, parent, row, label_text, widget, column):
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row, column=column, sticky="w", pady=(0, 6), padx=(0, 10))
        widget.grid(row=row, column=column + 1, sticky="ew", pady=(0, 6), padx=(0, 16))

    def _create_date_field(self, parent, row, label_text, column, picker_title):
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row, column=column, sticky="w", pady=(0, 6), padx=(0, 10))

        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=column + 1, sticky="ew", pady=(0, 6), padx=(0, 16))
        container.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(container, placeholder_text="YYYY-MM-DD")
        entry.grid(row=0, column=0, sticky="ew")

        pick_button = ctk.CTkButton(
            container,
            text="Pick",
            width=72,
            command=lambda: open_date_picker(self.root, entry, title=picker_title),
        )
        pick_button.grid(row=0, column=1, padx=(8, 0))

        return entry

    def _place_settings_field(self, parent, row, label_text, widget):
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=(0, 10))
        widget.grid(row=row, column=1, sticky="ew", pady=(0, 10))

    def _browse_credentials(self):
        selected = filedialog.askopenfilename(
            title="Select Google credentials JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.credentials_entry.delete(0, "end")
            self.credentials_entry.insert(0, selected)

    def _browse_token(self):
        selected = filedialog.asksaveasfilename(
            title="Select token storage file",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.token_entry.delete(0, "end")
            self.token_entry.insert(0, selected)

    def _parse_attendees(self, attendees_text):
        attendees = [item.strip() for item in attendees_text.split(",") if item.strip()]
        invalid = [email for email in attendees if not EMAIL_PATTERN.match(email)]
        if invalid:
            raise ValueError(f"Invalid attendee email(s): {', '.join(invalid)}")
        return attendees

    def _validate_form(self):
        task_name = self.task_name_entry.get().strip()
        if not task_name:
            raise ValueError("Task name is required.")

        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()
        start_time = self.start_time_entry.get().strip()
        end_time = self.end_time_entry.get().strip()
        start_period = self.start_period_menu.get().strip().upper()
        end_period = self.end_period_menu.get().strip().upper()
        timezone = self.timezone_combobox.get().strip()

        taskLogger.build_task_datetimes(
            start_date=start_date,
            start_time=start_time,
            start_period=start_period,
            end_date=end_date,
            end_time=end_time,
            end_period=end_period,
            timezone=timezone,
        )

        attendees = self._parse_attendees(self.attendees_entry.get())
        return {
            "task_name": task_name,
            "client": self.client_combobox.get().strip() or taskLogger.DEFAULT_CLIENT,
            "category": self.category_combobox.get().strip() or taskLogger.DEFAULT_CATEGORY,
            "billable": bool(self.billable_var.get()),
            "start_date": start_date,
            "start_time": start_time,
            "start_period": start_period,
            "end_date": end_date,
            "end_time": end_time,
            "end_period": end_period,
            "timezone": timezone,
            "attendees": attendees,
        }

    def _add_task(self):
        self.add_task_button.configure(state="disabled")
        try:
            data = self._validate_form()
            runtime_config = self.get_runtime_config()

            result = taskLogger.add_task_to_log(
                task_name=data["task_name"],
                client=data["client"],
                category=data["category"],
                billable=data["billable"],
                start_date=data["start_date"],
                start_time=data["start_time"],
                start_period=data["start_period"],
                end_date=data["end_date"],
                end_time=data["end_time"],
                end_period=data["end_period"],
                timezone=data["timezone"],
                task_log=TASK_LOG_FILE,
                attendees=data["attendees"],
                sync_to_google=runtime_config["google_sync_enabled"],
                credentials_path=runtime_config["google_credentials_path"],
                token_path=runtime_config["google_token_path"],
                calendar_id=runtime_config["google_calendar_id"],
                sync_to_dashboard=runtime_config["dashboard_sync_enabled"],
                dashboard_api_url=runtime_config["dashboard_api_url"],
                dashboard_api_token=runtime_config["dashboard_api_token"],
            )

            self.task_list_panel.refresh()
            self.status_var.set(f"Saved task ({result['hours_worked']:.2f} hours).")
            self._clear_form()

            sync_warnings = []
            if result.get("calendar_error"):
                sync_warnings.append(f"Calendar sync failed:\n\n{result['calendar_error']}")
            if result.get("dashboard_error"):
                sync_warnings.append(f"Dashboard sync failed:\n\n{result['dashboard_error']}")
            if sync_warnings:
                messagebox.showwarning(
                    "Saved locally",
                    "Task was saved locally, but one or more syncs failed:\n\n"
                    + "\n\n".join(sync_warnings),
                )
        except Exception as exc:
            self.status_var.set("Save failed.")
            messagebox.showerror("Could not save task", str(exc))
        finally:
            self.add_task_button.configure(state="normal")

    def _clear_form(self):
        now = datetime.datetime.now()
        one_hour_later = now + datetime.timedelta(hours=1)
        today = now.strftime("%Y-%m-%d")

        start_time, start_period = self._to_12_hour(now)
        end_time, end_period = self._to_12_hour(one_hour_later)

        self.task_name_entry.delete(0, "end")

        self.start_date_entry.delete(0, "end")
        self.start_date_entry.insert(0, today)
        self.start_time_entry.delete(0, "end")
        self.start_time_entry.insert(0, start_time)
        self.start_period_menu.set(start_period)

        self.end_date_entry.delete(0, "end")
        self.end_date_entry.insert(0, one_hour_later.strftime("%Y-%m-%d"))
        self.end_time_entry.delete(0, "end")
        self.end_time_entry.insert(0, end_time)
        self.end_period_menu.set(end_period)

        self.timezone_combobox.set(self.config["timezone"])
        self.client_combobox.configure(values=self._client_values())
        self.client_combobox.set(self._client_values()[0])
        self.category_combobox.configure(values=self._category_values())
        self.category_combobox.set(self._category_values()[0])
        self.billable_var.set(True)
        self.attendees_entry.delete(0, "end")
        self.task_name_entry.focus()

    def _save_settings(self):
        timezone = self.default_timezone_combo.get().strip()
        if timezone not in pytz.all_timezones:
            raise ValueError("Select a valid timezone.")

        credentials_path = self.credentials_entry.get().strip()
        token_path = self.token_entry.get().strip()
        calendar_id = self.calendar_id_entry.get().strip() or "primary"
        categories = _normalize_categories(self.categories_entry.get())
        clients = _normalize_clients(self.clients_entry.get())
        dashboard_api_url = self.dashboard_url_entry.get().strip()
        dashboard_api_token = self.dashboard_token_entry.get().strip()

        if self.google_sync_var.get() and not credentials_path:
            raise ValueError("Credentials file is required when Google sync is enabled.")
        if not token_path:
            raise ValueError("Token storage file is required.")
        if self.dashboard_sync_var.get() and not dashboard_api_url:
            raise ValueError("Dashboard URL is required when dashboard sync is enabled.")
        if self.dashboard_sync_var.get() and not dashboard_api_token:
            raise ValueError("Dashboard API token is required when dashboard sync is enabled.")

        self.config["timezone"] = timezone
        self.config["categories"] = categories
        self.config["clients"] = clients
        self.config["google_sync_enabled"] = bool(self.google_sync_var.get())
        self.config["google_credentials_path"] = credentials_path
        self.config["google_token_path"] = token_path
        self.config["google_calendar_id"] = calendar_id
        self.config["dashboard_sync_enabled"] = bool(self.dashboard_sync_var.get())
        self.config["dashboard_api_url"] = dashboard_api_url
        self.config["dashboard_api_token"] = dashboard_api_token
        save_config(self.config)

        self.timezone_combobox.set(timezone)
        self.client_combobox.configure(values=self._client_values())
        self.category_combobox.configure(values=self._category_values())
        self.status_var.set("Settings saved.")

    def _save_settings_clicked(self):
        try:
            self._save_settings()
        except Exception as exc:
            messagebox.showerror("Could not save settings", str(exc))

    def _connect_google(self):
        try:
            self._save_settings()
            if not self.config["google_sync_enabled"]:
                messagebox.showinfo("Google sync disabled", "Enable Google sync first in Settings.")
                return

            taskLogger.authenticate_google_calendar(
                credentials_path=self.config["google_credentials_path"],
                token_path=self.config["google_token_path"],
            )
            self.status_var.set("Google Calendar connected.")
            messagebox.showinfo("Connected", "Google Calendar authorization completed.")
        except Exception as exc:
            self.status_var.set("Google connection failed.")
            messagebox.showerror("Connection failed", str(exc))

    def _load_clients_from_dashboard(self):
        try:
            dashboard_api_url = self.dashboard_url_entry.get().strip()
            dashboard_api_token = self.dashboard_token_entry.get().strip()

            if not dashboard_api_url:
                raise ValueError("Dashboard URL is required to load clients.")
            if not dashboard_api_token:
                raise ValueError("Dashboard API token is required to load clients.")

            clients = taskLogger.fetch_dashboard_clients(
                api_url=dashboard_api_url,
                api_token=dashboard_api_token,
            )
            if not clients:
                raise ValueError("Dashboard returned no clients. Your local client list was not changed.")
            clients = _normalize_clients(clients)
            self.clients_entry.delete(0, "end")
            self.clients_entry.insert(0, ", ".join(clients))
            self.config["clients"] = clients
            self.config["dashboard_api_url"] = dashboard_api_url
            self.config["dashboard_api_token"] = dashboard_api_token
            save_config(self.config)
            self.client_combobox.configure(values=self._client_values())
            if self.client_combobox.get().strip() not in clients:
                self.client_combobox.set(clients[0])
            self.status_var.set(f"Imported {len(clients)} dashboard client(s) into the local list.")
            messagebox.showinfo(
                "Clients imported",
                f"Imported {len(clients)} dashboard client(s). Dashboard task sync remains controlled by the sync toggle.",
            )
        except Exception as exc:
            self.status_var.set("Client load failed.")
            messagebox.showerror("Could not load clients", str(exc))

    def get_runtime_config(self):
        return {
            "google_sync_enabled": bool(self.config.get("google_sync_enabled", False)),
            "google_credentials_path": self.config.get("google_credentials_path", "credentials.json"),
            "google_token_path": self.config.get("google_token_path", _default_token_path()),
            "google_calendar_id": self.config.get("google_calendar_id", "primary") or "primary",
            "dashboard_sync_enabled": bool(self.config.get("dashboard_sync_enabled", False)),
            "dashboard_api_url": self.config.get("dashboard_api_url", "http://localhost:3000"),
            "dashboard_api_token": self.config.get("dashboard_api_token", ""),
            "categories": _normalize_categories(self.config.get("categories")),
            "clients": _normalize_clients(self.config.get("clients")),
        }

    def _on_tasks_changed(self):
        self.status_var.set("Task list updated.")

    def _category_values(self):
        return _normalize_categories(self.config.get("categories"))

    def _client_values(self):
        return _normalize_clients(self.config.get("clients"))

    @staticmethod
    def _to_12_hour(dt_value):
        hour = dt_value.hour % 12
        hour = 12 if hour == 0 else hour
        period = "AM" if dt_value.hour < 12 else "PM"
        return f"{hour:02d}:{dt_value.minute:02d}", period

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TaskLoggerApp()
    app.run()
