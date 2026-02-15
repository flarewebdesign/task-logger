import datetime
import sys
from tkinter import messagebox

import customtkinter as ctk

TKCALENDAR_IMPORT_ERROR = ""

try:
    from tkcalendar import Calendar

    HAS_TKCALENDAR = True
except ImportError as exc:
    Calendar = None
    HAS_TKCALENDAR = False
    TKCALENDAR_IMPORT_ERROR = str(exc)


def _parse_entry_date(value):
    try:
        return datetime.datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return datetime.date.today()


def open_date_picker(master, entry_widget, title="Select Date"):
    if not HAS_TKCALENDAR:
        python_path = sys.executable
        messagebox.showinfo(
            "Calendar picker unavailable",
            "Install 'tkcalendar' in the same Python environment running this app.\n\n"
            f"Python: {python_path}\n"
            f"Command: \"{python_path}\" -m pip install \"tkcalendar>=1.6.1,<2.0.0\"\n"
            f"Import error: {TKCALENDAR_IMPORT_ERROR}\n\n"
            "You can still type dates manually in YYYY-MM-DD format.",
        )
        entry_widget.focus_set()
        return

    current_date = _parse_entry_date(entry_widget.get())

    picker_window = ctk.CTkToplevel(master)
    picker_window.title(title)
    picker_window.geometry("300x340")
    picker_window.resizable(False, False)
    picker_window.transient(master.winfo_toplevel())
    picker_window.grab_set()

    calendar = Calendar(
        picker_window,
        selectmode="day",
        date_pattern="yyyy-mm-dd",
        year=current_date.year,
        month=current_date.month,
        day=current_date.day,
    )
    calendar.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    buttons = ctk.CTkFrame(picker_window, fg_color="transparent")
    buttons.pack(fill="x", padx=12, pady=(0, 12))

    def apply_date():
        entry_widget.delete(0, "end")
        entry_widget.insert(0, calendar.get_date())
        picker_window.destroy()
        entry_widget.focus_set()

    cancel_button = ctk.CTkButton(buttons, text="Cancel", command=picker_window.destroy, width=110)
    cancel_button.pack(side="left")

    use_date_button = ctk.CTkButton(
        buttons,
        text="Use Date",
        command=apply_date,
        width=110,
        fg_color="#2F8A42",
        hover_color="#246A32",
    )
    use_date_button.pack(side="right")
