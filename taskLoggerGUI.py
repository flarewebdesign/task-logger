import customtkinter as ctk
import taskLogger
import taskListGUI
import datetime
import pandas as pd
import os
import pytz
import json

CONFIG_FILE = "config.json"

# Ensure the task log file exists
def ensure_task_log_exists(file_name="task_log.xlsx"):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=["ID", "Task", "Start Date", "Start Time", "Start AM/PM", "End Date", "End Time", "End AM/PM", "Timezone", "Decimal Hours", "Event ID"])
        df.to_excel(file_name, index=False)

# Call the function to ensure the Excel file exists
ensure_task_log_exists()

# Load configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        # Create default configuration if file doesn't exist
        default_config = {"timezone": "UTC"}
        save_config(default_config)
        return default_config

# Save configuration
def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# Load initial configuration
config = load_config()
default_timezone = config.get("timezone", "UTC")

# Define the root window
root = ctk.CTk()
root.title("Task Logger")
root.geometry("350x430")

# Set appearance mode
ctk.set_appearance_mode("system")  # Options: "dark", "light", "system"

# Define the frame for the widgets
frame = ctk.CTkFrame(root, fg_color="transparent")  # Use transparent background
frame.pack(pady=20, padx=20, fill="both", expand=True)

def get_period(toggle):
    return "PM" if toggle.get() else "AM"

def add_task():
    task_name = task_name_entry.get()
    start_date = date_entry.get()
    start_time = start_time_entry.get()
    start_period = get_period(start_period_toggle)
    end_date = end_date_entry.get()
    end_time = end_time_entry.get()
    end_period = get_period(end_period_toggle)
    timezone = timezone_combobox.get()
    taskLogger.add_task_to_log(task_name, start_date, start_time, start_period, end_date, end_time, end_period, timezone, "task_log.xlsx")

def save_timezone():
    config["timezone"] = timezone_combobox.get()
    save_config(config)
    print(f"Timezone saved: {config['timezone']}")  # Debugging line

# Define the widgets with improved spacing
task_name_label = ctk.CTkLabel(frame, text="Task Name:")
task_name_label.grid(row=0, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

task_name_entry = ctk.CTkEntry(frame)
task_name_entry.grid(row=0, column=1, pady=(0, 5), padx=(0, 5))

date_label = ctk.CTkLabel(frame, text="Start Date (YYYY-MM-DD):")
date_label.grid(row=1, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

# Populate the date field with today's date
date_entry = ctk.CTkEntry(frame)
date_entry.grid(row=1, column=1, pady=(0, 5), padx=(0, 5))
today = datetime.datetime.now().strftime("%Y-%m-%d")
date_entry.insert(0, today)

start_time_label = ctk.CTkLabel(frame, text="Start Time (HH:MM):")
start_time_label.grid(row=2, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

start_time_entry = ctk.CTkEntry(frame)
start_time_entry.grid(row=2, column=1, pady=(0, 5), padx=(0, 5))

start_period_label = ctk.CTkLabel(frame, text="Start AM/PM:")
start_period_label.grid(row=3, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

start_period_toggle = ctk.CTkSwitch(frame, text="AM/PM")
start_period_toggle.grid(row=3, column=1, pady=(0, 5), padx=(0, 5))

end_date_label = ctk.CTkLabel(frame, text="End Date (YYYY-MM-DD):")
end_date_label.grid(row=4, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

end_date_entry = ctk.CTkEntry(frame)
end_date_entry.grid(row=4, column=1, pady=(0, 5), padx=(0, 5))
end_date_entry.insert(0, today)

end_time_label = ctk.CTkLabel(frame, text="End Time (HH:MM):")
end_time_label.grid(row=5, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

end_time_entry = ctk.CTkEntry(frame)
end_time_entry.grid(row=5, column=1, pady=(0, 5), padx=(0, 5))

end_period_label = ctk.CTkLabel(frame, text="End AM/PM:")
end_period_label.grid(row=6, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

end_period_toggle = ctk.CTkSwitch(frame, text="AM/PM")
end_period_toggle.grid(row=6, column=1, pady=(0, 5), padx=(0, 5))

# Timezone selection
timezone_label = ctk.CTkLabel(frame, text="Timezone:")
timezone_label.grid(row=7, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

timezones = pytz.all_timezones
timezone_combobox = ctk.CTkComboBox(frame, values=timezones)
timezone_combobox.grid(row=7, column=1, pady=(0, 5), padx=(0, 5))
timezone_combobox.set(default_timezone)  # Set default value

save_timezone_button = ctk.CTkButton(frame, text="Save Timezone", command=save_timezone)
save_timezone_button.grid(row=8, column=0, columnspan=2, pady=(15, 0), padx=(10, 15), sticky='ew')

button_frame = ctk.CTkFrame(frame, fg_color="transparent")
button_frame.grid(row=9, column=0, columnspan=2, pady=(5, 5), padx=(5, 5), sticky='ew')

add_task_button = ctk.CTkButton(button_frame, text="Add Task", command=add_task, fg_color="green")
add_task_button.grid(row=0, column=0, pady=(5, 5), padx=(5, 5), sticky='ew')

clear_fields_button = ctk.CTkButton(button_frame, text="Clear Fields", command=lambda: clear_fields(task_name_entry, date_entry, end_date_entry, start_time_entry, start_period_toggle, end_time_entry, end_period_toggle, timezone_combobox))
clear_fields_button.grid(row=0, column=1, pady=(5, 5), padx=(5, 5), sticky='ew')

view_task_list_button = ctk.CTkButton(button_frame, text="View Tasks", command=taskListGUI.show)
view_task_list_button.grid(row=1, column=0, pady=(5, 5), padx=(5, 5), sticky='ew')

exit_button = ctk.CTkButton(button_frame, text="Exit", command=root.destroy)
exit_button.grid(row=1, column=1, pady=(5, 5), padx=(5, 5), sticky='ew')

# Define the function to clear the fields
def clear_fields(*entries):
    for entry in entries:
        if isinstance(entry, ctk.CTkEntry):
            entry.delete(0, 'end')
        elif isinstance(entry, ctk.CTkSwitch):
            entry.deselect()
        elif isinstance(entry, ctk.CTkComboBox):
            entry.set(default_timezone)

# Run the root window's main loop
root.mainloop()