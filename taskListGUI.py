# taskListGUI.py

from datetime import datetime
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd
import pytz

import taskLogger
from ui_date_picker import open_date_picker


class TaskListPanel(ctk.CTkFrame):
    def __init__(self, master, get_config, task_log="task_log.xlsx", on_task_changed=None):
        super().__init__(master, fg_color="transparent")
        self.get_config = get_config
        self.task_log = task_log
        self.on_task_changed = on_task_changed
        self.timezones = pytz.common_timezones

        self._setup_treeview()
        self._setup_buttons()
        self.refresh()

    def _setup_treeview(self):
        tree_container = ctk.CTkFrame(self, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        columns = (
            "id",
            "task",
            "client",
            "category",
            "start",
            "end",
            "timezone",
            "hours",
            "billing",
            "attendees",
            "event_id",
        )
        self.task_tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")

        column_specs = {
            "id": {"text": "ID", "width": 0, "anchor": "w", "stretch": False},
            "task": {"text": "Task", "width": 200, "anchor": "w", "stretch": True},
            "client": {"text": "Client", "width": 140, "anchor": "w", "stretch": False},
            "category": {"text": "Category", "width": 130, "anchor": "w", "stretch": False},
            "start": {"text": "Start", "width": 170, "anchor": "w", "stretch": True},
            "end": {"text": "End", "width": 170, "anchor": "w", "stretch": True},
            "timezone": {"text": "Timezone", "width": 130, "anchor": "w", "stretch": True},
            "hours": {"text": "Hours", "width": 80, "anchor": "e", "stretch": False},
            "billing": {"text": "Billing", "width": 95, "anchor": "w", "stretch": False},
            "attendees": {"text": "Attendees", "width": 280, "anchor": "w", "stretch": True},
            "event_id": {"text": "Event ID", "width": 0, "anchor": "w", "stretch": False},
        }

        for column, spec in column_specs.items():
            self.task_tree.heading(column, text=spec["text"])
            self.task_tree.column(
                column,
                anchor=spec["anchor"],
                width=spec["width"],
                stretch=spec["stretch"],
            )

        y_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=y_scrollbar.set)

        self.task_tree.pack(side="left", fill="both", expand=True)
        y_scrollbar.pack(side="right", fill="y")

        self.task_tree.bind("<Double-1>", lambda _event: self.modify_task())

    def _setup_buttons(self):
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=10)

        refresh_button = ctk.CTkButton(controls, text="Refresh", command=self.refresh)
        refresh_button.pack(side="left", padx=(0, 10))

        modify_button = ctk.CTkButton(controls, text="Edit Selected", command=self.modify_task)
        modify_button.pack(side="left", padx=(0, 10))

        remove_button = ctk.CTkButton(
            controls,
            text="Delete Selected",
            command=self.remove_task,
            fg_color="#B93838",
            hover_color="#992E2E",
        )
        remove_button.pack(side="left")

    def _selected_task_id(self):
        selected_item = self.task_tree.focus()
        if not selected_item:
            return ""
        values = self.task_tree.item(selected_item).get("values", [])
        return str(values[0]) if values else ""

    def refresh(self):
        self.task_tree.delete(*self.task_tree.get_children())
        df = taskLogger.load_task_log(self.task_log)

        for _, row in df.iterrows():
            task_id = self._safe_text(row.get("ID"))
            task_name = self._safe_text(row.get("Task"))
            client = self._safe_text(row.get("Client")) or taskLogger.DEFAULT_CLIENT
            category = self._safe_text(row.get("Category")) or taskLogger.DEFAULT_CATEGORY
            start = self._format_datetime_display(row, "Start Date", "Start Time", "Start AM/PM")
            end = self._format_datetime_display(row, "End Date", "End Time", "End AM/PM")
            timezone = self._safe_text(row.get("Timezone"))
            attendees = self._safe_text(row.get("Attendees"))
            event_id = self._safe_text(row.get("Event ID"))
            billing_text = "Billable" if taskLogger.is_billable(row.get("Billable")) else "No charge"

            hours_value = row.get("Decimal Hours")
            hours_text = ""
            if not pd.isna(hours_value):
                try:
                    hours_text = f"{float(hours_value):.2f}"
                except (TypeError, ValueError):
                    hours_text = self._safe_text(hours_value)

            self.task_tree.insert(
                "",
                "end",
                values=(
                    task_id,
                    task_name,
                    client,
                    category,
                    start,
                    end,
                    timezone,
                    hours_text,
                    billing_text,
                    attendees,
                    event_id,
                ),
            )

    def remove_task(self):
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("No selection", "Select a task first.")
            return

        confirmed = messagebox.askyesno("Delete Task", "Delete the selected task?")
        if not confirmed:
            return

        try:
            config = self.get_config()
            result = taskLogger.remove_task_from_log(
                task_id=task_id,
                task_log=self.task_log,
                sync_to_google=bool(config.get("google_sync_enabled")),
                credentials_path=config.get("google_credentials_path", "credentials.json"),
                token_path=config.get("google_token_path", "token.json"),
                calendar_id=config.get("google_calendar_id", "primary"),
                sync_to_dashboard=bool(config.get("dashboard_sync_enabled")),
                dashboard_api_url=config.get("dashboard_api_url", ""),
                dashboard_api_token=config.get("dashboard_api_token", ""),
            )
        except Exception as exc:
            messagebox.showerror("Delete failed", str(exc))
            return

        self.refresh()
        if self.on_task_changed:
            self.on_task_changed()

        sync_warnings = []
        if result.get("calendar_error"):
            sync_warnings.append(f"Calendar cleanup failed:\n\n{result['calendar_error']}")
        if result.get("dashboard_error"):
            sync_warnings.append(f"Dashboard cleanup failed:\n\n{result['dashboard_error']}")
        if sync_warnings:
            messagebox.showwarning(
                "Task deleted locally",
                "The task was deleted locally, but one or more sync cleanups failed:\n\n"
                + "\n\n".join(sync_warnings),
            )

    def modify_task(self):
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("No selection", "Select a task first.")
            return

        df = taskLogger.load_task_log(self.task_log)
        matches = df[df["ID"].astype(str) == str(task_id)]
        if matches.empty:
            messagebox.showerror("Not found", "Selected task could not be loaded.")
            return

        row = matches.iloc[0]
        edit_window = ctk.CTkToplevel(self)
        edit_window.title("Edit Task")
        edit_window.geometry("540x600")
        edit_window.transient(self.winfo_toplevel())
        edit_window.grab_set()

        form = ctk.CTkFrame(edit_window, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=20)
        form.grid_columnconfigure(1, weight=1)

        task_name_entry = self._create_labeled_entry(form, 0, "Task Name", self._safe_text(row.get("Task")))
        client_combo = ctk.CTkComboBox(form, values=self._client_values())
        client_combo.set(self._safe_text(row.get("Client")) or taskLogger.DEFAULT_CLIENT)
        self._add_field(form, 1, "Client", client_combo)

        category_combo = ctk.CTkComboBox(form, values=self._category_values())
        category_combo.set(self._safe_text(row.get("Category")) or taskLogger.DEFAULT_CATEGORY)
        self._add_field(form, 2, "Category", category_combo)

        start_date_entry = self._create_labeled_date_entry(
            form,
            3,
            "Start Date (YYYY-MM-DD)",
            self._format_date(row.get("Start Date")),
            edit_window,
            "Pick Start Date",
        )
        start_time_entry = self._create_labeled_entry(form, 4, "Start Time (HH:MM)", self._safe_text(row.get("Start Time")))

        start_period = self._safe_text(row.get("Start AM/PM")) or "AM"
        start_period_menu = ctk.CTkOptionMenu(form, values=["AM", "PM"])
        start_period_menu.set(start_period if start_period in {"AM", "PM"} else "AM")
        self._add_field(form, 5, "Start AM/PM", start_period_menu)

        end_date_entry = self._create_labeled_date_entry(
            form,
            6,
            "End Date (YYYY-MM-DD)",
            self._format_date(row.get("End Date")),
            edit_window,
            "Pick End Date",
        )
        end_time_entry = self._create_labeled_entry(form, 7, "End Time (HH:MM)", self._safe_text(row.get("End Time")))

        end_period = self._safe_text(row.get("End AM/PM")) or "AM"
        end_period_menu = ctk.CTkOptionMenu(form, values=["AM", "PM"])
        end_period_menu.set(end_period if end_period in {"AM", "PM"} else "AM")
        self._add_field(form, 8, "End AM/PM", end_period_menu)

        timezone_combo = ctk.CTkComboBox(form, values=self.timezones)
        timezone_combo.set(self._safe_text(row.get("Timezone")) or "UTC")
        self._add_field(form, 9, "Timezone", timezone_combo)

        attendees_entry = self._create_labeled_entry(
            form,
            10,
            "Attendees (comma separated)",
            self._safe_text(row.get("Attendees")),
        )

        billable_var = tk.BooleanVar(value=taskLogger.is_billable(row.get("Billable")))
        billable_checkbox = ctk.CTkCheckBox(
            form,
            text="Billable",
            variable=billable_var,
            onvalue=True,
            offvalue=False,
        )
        self._add_field(form, 11, "Billing", billable_checkbox)

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        cancel_button = ctk.CTkButton(button_row, text="Cancel", command=edit_window.destroy)
        cancel_button.pack(side="left", padx=(0, 10))

        def save_changes():
            try:
                config = self.get_config()
                result = taskLogger.update_task_in_log(
                    task_id=task_id,
                    task_name=task_name_entry.get(),
                    client=client_combo.get(),
                    category=category_combo.get(),
                    billable=bool(billable_var.get()),
                    start_date=start_date_entry.get(),
                    start_time=start_time_entry.get(),
                    start_period=start_period_menu.get(),
                    end_date=end_date_entry.get(),
                    end_time=end_time_entry.get(),
                    end_period=end_period_menu.get(),
                    timezone=timezone_combo.get(),
                    task_log=self.task_log,
                    attendees=attendees_entry.get(),
                    sync_to_google=bool(config.get("google_sync_enabled")),
                    credentials_path=config.get("google_credentials_path", "credentials.json"),
                    token_path=config.get("google_token_path", "token.json"),
                    calendar_id=config.get("google_calendar_id", "primary"),
                    sync_to_dashboard=bool(config.get("dashboard_sync_enabled")),
                    dashboard_api_url=config.get("dashboard_api_url", ""),
                    dashboard_api_token=config.get("dashboard_api_token", ""),
                )
            except Exception as exc:
                messagebox.showerror("Save failed", str(exc))
                return

            self.refresh()
            if self.on_task_changed:
                self.on_task_changed()
            edit_window.destroy()

            sync_warnings = []
            if result.get("calendar_error"):
                sync_warnings.append(f"Calendar sync failed:\n\n{result['calendar_error']}")
            if result.get("dashboard_error"):
                sync_warnings.append(f"Dashboard sync failed:\n\n{result['dashboard_error']}")
            if sync_warnings:
                messagebox.showwarning(
                    "Saved locally",
                    "Task changes were saved, but one or more syncs failed:\n\n"
                    + "\n\n".join(sync_warnings),
                )

        save_button = ctk.CTkButton(button_row, text="Save Changes", command=save_changes, fg_color="#2F8A42")
        save_button.pack(side="left")

    def _create_labeled_entry(self, parent, row_index, label_text, initial_value):
        entry = ctk.CTkEntry(parent)
        entry.insert(0, initial_value)
        self._add_field(parent, row_index, label_text, entry)
        return entry

    def _create_labeled_date_entry(self, parent, row_index, label_text, initial_value, picker_parent, picker_title):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(container)
        entry.insert(0, initial_value)
        entry.grid(row=0, column=0, sticky="ew")

        pick_button = ctk.CTkButton(
            container,
            text="Pick",
            width=72,
            command=lambda: open_date_picker(picker_parent, entry, title=picker_title),
        )
        pick_button.grid(row=0, column=1, padx=(8, 0))

        self._add_field(parent, row_index, label_text, container)
        return entry

    def _add_field(self, parent, row_index, label_text, widget):
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row_index, column=0, sticky="w", pady=(0, 8), padx=(0, 10))
        widget.grid(row=row_index, column=1, sticky="ew", pady=(0, 8))

    def _category_values(self):
        config = self.get_config()
        categories = config.get("categories") or []
        cleaned = []
        seen = set()
        for item in categories:
            category = str(item).strip()
            if not category:
                continue
            key = category.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(category)
        return cleaned or [taskLogger.DEFAULT_CATEGORY]

    def _client_values(self):
        config = self.get_config()
        clients = config.get("clients") or []
        cleaned = []
        seen = set()
        for item in clients:
            client = str(item).strip()
            if not client:
                continue
            key = client.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(client)
        return cleaned or [taskLogger.DEFAULT_CLIENT]

    @staticmethod
    def _safe_text(value):
        if pd.isna(value):
            return ""
        text = str(value).strip()
        return "" if text.lower() == "nan" else text

    def _format_date(self, value):
        if pd.isna(value):
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")

        text = self._safe_text(value)
        if not text:
            return ""
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            return text

    def _format_datetime_display(self, row, date_key, time_key, period_key):
        date_text = self._format_date(row.get(date_key))
        time_text = self._safe_text(row.get(time_key))
        period_text = self._safe_text(row.get(period_key))

        parts = [part for part in [date_text, time_text, period_text] if part]
        return " ".join(parts)


if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    root = ctk.CTk()
    root.geometry("1100x600")
    root.title("Task List")

    config = {
        "google_sync_enabled": False,
        "google_credentials_path": "credentials.json",
        "google_token_path": "token.json",
        "google_calendar_id": "primary",
        "dashboard_sync_enabled": False,
        "dashboard_api_url": "http://localhost:3000",
        "dashboard_api_token": "",
        "clients": [taskLogger.DEFAULT_CLIENT],
        "categories": ["Development", "Design", "Admin", "Support", "Meetings"],
    }
    panel = TaskListPanel(root, get_config=lambda: config)
    panel.pack(fill="both", expand=True)
    root.mainloop()
