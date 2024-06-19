import customtkinter as ctk
import taskLogger
import taskListGUI
import datetime
import pandas as pd
import os

# Ensure the task log file exists
def ensure_task_log_exists(file_name="task_log.xlsx"):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=["ID", "Date", "Task", "Start Time", "Start AM/PM", "End Time", "End AM/PM", "Decimal Hours"])
        df.to_excel(file_name, index=False)

# Call the function to ensure the Excel file exists
ensure_task_log_exists()

# Define the root window
root = ctk.CTk()
root.title("Task Logger")
root.geometry("325x320")

# Set appearance mode
ctk.set_appearance_mode("system")  # Options: "dark", "light", "system"

# Define the frame for the widgets
frame = ctk.CTkFrame(root, fg_color="transparent")  # Use transparent background
frame.pack(pady=20, padx=20, fill="both", expand=True)

# Define the widgets with improved spacing
task_name_label = ctk.CTkLabel(frame, text="Task Name:")
task_name_label.grid(row=0, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

task_name_entry = ctk.CTkEntry(frame)
task_name_entry.grid(row=0, column=1, pady=(0, 5), padx=(0, 5))

date_label = ctk.CTkLabel(frame, text="Date (YYYY-MM-DD):")
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

end_time_label = ctk.CTkLabel(frame, text="End Time (HH:MM):")
end_time_label.grid(row=4, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

end_time_entry = ctk.CTkEntry(frame)
end_time_entry.grid(row=4, column=1, pady=(0, 5), padx=(0, 5))

end_period_label = ctk.CTkLabel(frame, text="End AM/PM:")
end_period_label.grid(row=5, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

end_period_toggle = ctk.CTkSwitch(frame, text="AM/PM")
end_period_toggle.grid(row=5, column=1, pady=(0, 5), padx=(0, 5))

def get_period(toggle):
    return "PM" if toggle.get() else "AM"

add_task_button = ctk.CTkButton(frame, text="Add Task", command=lambda: taskLogger.add_task_to_log(task_name_entry.get(), date_entry.get(), start_time_entry.get(), get_period(start_period_toggle), end_time_entry.get(), get_period(end_period_toggle), "task_log.xlsx"))
add_task_button.grid(row=6, column=0, pady=(10, 5), padx=(0, 5))

clear_fields_button = ctk.CTkButton(frame, text="Clear Fields", command=lambda: clear_fields(task_name_entry, date_entry, start_time_entry, start_period_toggle, end_time_entry, end_period_toggle))
clear_fields_button.grid(row=6, column=1, pady=(10, 5), padx=(0, 5))

# Define the function to clear the fields
def clear_fields(*entries):
    for entry in entries:
        if isinstance(entry, ctk.CTkEntry):
            entry.delete(0, 'end')
        elif isinstance(entry, ctk.CTkSwitch):
            entry.deselect()

view_task_list_button = ctk.CTkButton(frame, text="View Tasks", command=taskListGUI.show)
view_task_list_button.grid(row=7, column=0, pady=(10, 5), padx=(0, 5))

exit_button = ctk.CTkButton(frame, text="Exit", command=root.destroy)
exit_button.grid(row=7, column=1, pady=(10, 5), padx=(0, 5))

# Run the root window's main loop
root.mainloop()