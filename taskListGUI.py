# taskListGUI.py

import threading
import tkinter as tk
import tkinter.ttk as ttk
from datetime import datetime
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
        self.search_var = tk.StringVar()
        self.billing_filter_var = tk.StringVar(value="All billing")
        self.summary_var = tk.StringVar(value="Loading tasks...")
        self._last_load_error = ""
        self._sync_actions_by_task_id = {}

        self._setup_treeview()
        self._setup_buttons()
        self.refresh()

    def _setup_treeview(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(10, 0))
        toolbar.grid_columnconfigure(0, weight=1)

        search_entry = ctk.CTkEntry(
            toolbar,
            textvariable=self.search_var,
            placeholder_text="Search task, client, category, or timezone",
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh())

        billing_filter = ctk.CTkComboBox(
            toolbar,
            values=["All billing", "Billable", "No charge"],
            variable=self.billing_filter_var,
            width=140,
            command=lambda _value: self.refresh(),
        )
        billing_filter.grid(row=0, column=1, padx=(0, 12))

        summary = ctk.CTkLabel(toolbar, textvariable=self.summary_var, text_color=("gray35", "gray70"))
        summary.grid(row=0, column=2, sticky="e")

        tree_container = ctk.CTkFrame(self, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

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
            "sync",
            "attendees",
            "event_id",
        )

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TaskLogger.Treeview",
            background="#202020",
            foreground="#F4F4F5",
            fieldbackground="#202020",
            borderwidth=0,
            rowheight=30,
        )
        style.configure(
            "TaskLogger.Treeview.Heading",
            background="#303030",
            foreground="#F4F4F5",
            relief="flat",
            padding=(8, 7),
        )
        style.map(
            "TaskLogger.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

        self.task_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            displaycolumns=(
                "task",
                "client",
                "category",
                "start",
                "end",
                "timezone",
                "hours",
                "billing",
                "sync",
            ),
            show="headings",
            selectmode="browse",
            style="TaskLogger.Treeview",
        )

        column_specs = {
            "id": {"text": "ID", "width": 0, "anchor": "w", "stretch": False},
            "task": {"text": "Task", "width": 190, "anchor": "w", "stretch": True},
            "client": {"text": "Client", "width": 110, "anchor": "w", "stretch": False},
            "category": {"text": "Category", "width": 90, "anchor": "w", "stretch": False},
            "start": {"text": "Start", "width": 125, "anchor": "w", "stretch": False},
            "end": {"text": "End", "width": 125, "anchor": "w", "stretch": False},
            "timezone": {"text": "Timezone", "width": 105, "anchor": "w", "stretch": False},
            "hours": {"text": "Hours", "width": 55, "anchor": "e", "stretch": False},
            "billing": {"text": "Billing", "width": 70, "anchor": "w", "stretch": False},
            "sync": {"text": "Sync", "width": 95, "anchor": "w", "stretch": False},
            "attendees": {"text": "Attendees", "width": 0, "anchor": "w", "stretch": False},
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
        x_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.task_tree.xview)
        self.task_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        self.task_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.task_tree.bind("<Double-1>", lambda _event: self.modify_task())
        self.task_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_action_states())
        self.task_tree.tag_configure("sync_error", foreground="#FCA5A5")
        self.task_tree.tag_configure("delete_pending", foreground="#FCD34D")

    def _setup_buttons(self):
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=10)

        self.refresh_button = ctk.CTkButton(controls, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="left", padx=(0, 10))

        self.modify_button = ctk.CTkButton(controls, text="Edit Selected", command=self.modify_task)
        self.modify_button.pack(side="left", padx=(0, 10))

        self.retry_button = ctk.CTkButton(
            controls,
            text="Retry Sync",
            command=self.retry_sync,
            fg_color="#7C5A16",
            hover_color="#624711",
        )

        self.remove_button = ctk.CTkButton(
            controls,
            text="Delete Selected",
            command=self.remove_task,
            fg_color="#B93838",
            hover_color="#992E2E",
        )
        self.remove_button.pack(side="left")
        self._update_action_states()

    def _selected_task_id(self):
        selected_item = self.task_tree.focus()
        if not selected_item:
            return ""
        values = self.task_tree.item(selected_item).get("values", [])
        return str(values[0]) if values else ""

    def _update_action_states(self):
        task_id = self._selected_task_id()
        state = "normal" if task_id else "disabled"
        self.modify_button.configure(state=state)
        self.remove_button.configure(state=state)

        retry_label = self._sync_actions_by_task_id.get(task_id)
        if retry_label:
            self.retry_button.configure(state="normal", text=retry_label)
            if not self.retry_button.winfo_manager():
                self.retry_button.pack(side="left", padx=(0, 10), before=self.remove_button)
        else:
            self.retry_button.pack_forget()

    def _run_background(self, operation, on_success, on_error):
        def worker():
            try:
                result = operation()
            except Exception as exc:
                self.after(0, lambda error=exc: on_error(error))
            else:
                self.after(0, lambda value=result: on_success(value))

        threading.Thread(target=worker, daemon=True).start()

    def refresh(self):
        self.task_tree.delete(*self.task_tree.get_children())
        self._sync_actions_by_task_id.clear()
        try:
            df = taskLogger.load_task_log(self.task_log)
            self._last_load_error = ""
        except taskLogger.TaskLogError as exc:
            self.summary_var.set("Workbook unavailable")
            self._update_action_states()
            if str(exc) != self._last_load_error:
                self._last_load_error = str(exc)
                messagebox.showerror("Could not load task workbook", str(exc))
            return

        search_text = self.search_var.get().strip().lower()
        billing_filter = self.billing_filter_var.get()
        visible_rows = []

        for _, row in df.iterrows():
            billing_text = "Billable" if taskLogger.is_billable(row.get("Billable")) else "No charge"
            searchable = " ".join(
                self._safe_text(row.get(column)) for column in ["Task", "Client", "Category", "Timezone", "Attendees"]
            ).lower()
            if search_text and search_text not in searchable:
                continue
            if billing_filter != "All billing" and billing_text != billing_filter:
                continue
            visible_rows.append((row, billing_text))

        for row, billing_text in visible_rows:
            task_id = self._safe_text(row.get("ID"))
            task_name = self._safe_text(row.get("Task"))
            client = self._safe_text(row.get("Client")) or taskLogger.DEFAULT_CLIENT
            category = self._safe_text(row.get("Category")) or taskLogger.DEFAULT_CATEGORY
            start = self._format_datetime_display(row, "Start Date", "Start Time", "Start AM/PM")
            end = self._format_datetime_display(row, "End Date", "End Time", "End AM/PM")
            timezone = self._safe_text(row.get("Timezone"))
            attendees = self._safe_text(row.get("Attendees"))
            event_id = self._safe_text(row.get("Event ID"))
            sync_text = taskLogger.task_sync_summary(row)
            retry_action = taskLogger.sync_retry_action(row)
            if retry_action:
                self._sync_actions_by_task_id[task_id] = retry_action
            tags = ()
            if "error" in sync_text.lower():
                tags = ("sync_error",)
            elif sync_text == "Delete pending":
                tags = ("delete_pending",)

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
                    sync_text,
                    attendees,
                    event_id,
                ),
                tags=tags,
            )

        self.summary_var.set(f"{len(visible_rows)} of {len(df)} tasks")
        self._update_action_states()

    def remove_task(self):
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("No selection", "Select a task first.")
            return

        confirmed = messagebox.askyesno("Delete Task", "Delete the selected task?")
        if not confirmed:
            return

        config = self.get_config()
        self.remove_button.configure(state="disabled", text="Deleting...")
        self.modify_button.configure(state="disabled")
        self.retry_button.configure(state="disabled")
        self.summary_var.set("Deleting task and cleaning up enabled sync targets...")

        def operation():
            return taskLogger.remove_task_from_log(
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

        def on_error(exc):
            self.remove_button.configure(text="Delete Selected")
            self._update_action_states()
            messagebox.showerror("Delete failed", str(exc))

        def on_success(result):
            self.remove_button.configure(text="Delete Selected")
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
                    "Deletion pending",
                    "The task remains in the Excel workbook so cleanup can be retried safely:\n\n"
                    + "\n\n".join(sync_warnings),
                )

        self._run_background(operation, on_success, on_error)

    def retry_sync(self):
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("No selection", "Select a task first.")
            return

        config = self.get_config()
        self.retry_button.configure(state="disabled", text="Retrying...")
        self.modify_button.configure(state="disabled")
        self.remove_button.configure(state="disabled")
        self.summary_var.set("Retrying enabled sync targets...")

        def operation():
            return taskLogger.retry_task_sync(
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

        def on_error(exc):
            self._update_action_states()
            messagebox.showerror("Sync retry failed", str(exc))

        def on_success(result):
            self.refresh()
            if self.on_task_changed:
                self.on_task_changed()

            errors = [message for message in [result.get("calendar_error"), result.get("dashboard_error")] if message]
            if errors:
                messagebox.showwarning("Sync still pending", "\n\n".join(errors))
            else:
                messagebox.showinfo("Sync complete", "The selected task is synchronized.")

        self._run_background(operation, on_success, on_error)

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

        form = ctk.CTkScrollableFrame(edit_window, fg_color="transparent")
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
        start_time_entry = self._create_labeled_entry(
            form, 4, "Start Time (HH:MM)", self._safe_text(row.get("Start Time"))
        )

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
            config = self.get_config()
            values = {
                "task_name": task_name_entry.get(),
                "client": client_combo.get(),
                "category": category_combo.get(),
                "billable": bool(billable_var.get()),
                "start_date": start_date_entry.get(),
                "start_time": start_time_entry.get(),
                "start_period": start_period_menu.get(),
                "end_date": end_date_entry.get(),
                "end_time": end_time_entry.get(),
                "end_period": end_period_menu.get(),
                "timezone": timezone_combo.get(),
                "attendees": attendees_entry.get(),
            }
            save_button.configure(state="disabled", text="Saving...")
            cancel_button.configure(state="disabled")
            edit_window.protocol("WM_DELETE_WINDOW", lambda: None)

            def operation():
                return taskLogger.update_task_in_log(
                    task_id=task_id,
                    task_name=values["task_name"],
                    client=values["client"],
                    category=values["category"],
                    billable=values["billable"],
                    start_date=values["start_date"],
                    start_time=values["start_time"],
                    start_period=values["start_period"],
                    end_date=values["end_date"],
                    end_time=values["end_time"],
                    end_period=values["end_period"],
                    timezone=values["timezone"],
                    task_log=self.task_log,
                    attendees=values["attendees"],
                    sync_to_google=bool(config.get("google_sync_enabled")),
                    credentials_path=config.get("google_credentials_path", "credentials.json"),
                    token_path=config.get("google_token_path", "token.json"),
                    calendar_id=config.get("google_calendar_id", "primary"),
                    sync_to_dashboard=bool(config.get("dashboard_sync_enabled")),
                    dashboard_api_url=config.get("dashboard_api_url", ""),
                    dashboard_api_token=config.get("dashboard_api_token", ""),
                )

            def on_error(exc):
                save_button.configure(state="normal", text="Save Changes")
                cancel_button.configure(state="normal")
                edit_window.protocol("WM_DELETE_WINDOW", edit_window.destroy)
                messagebox.showerror("Save failed", str(exc))

            def on_success(result):
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
                        "Task changes were saved, but one or more syncs are pending:\n\n" + "\n\n".join(sync_warnings),
                    )

            self._run_background(operation, on_success, on_error)

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
