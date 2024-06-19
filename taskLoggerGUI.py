import tkinter as tk
from tkinter import ttk
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
root = tk.Tk()
root.title("Task Logger")

# Define the frame for the widgets
frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=10, pady=10)

# Define the widgets
task_name_label = ttk.Label(frame, text="Task Name:")
task_name_label.grid(row=0, column=0, sticky='W')

task_name_entry = ttk.Entry(frame)
task_name_entry.grid(row=0, column=1)

date_label = ttk.Label(frame, text="Date (YYYY-MM-DD):")
date_label.grid(row=1, column=0, sticky='W')

# Populate the date field with today's date
date_entry = ttk.Entry(frame)
date_entry.grid(row=1, column=1)
today = datetime.datetime.now().strftime("%Y-%m-%d")
date_entry.insert(0, today)

start_time_label = ttk.Label(frame, text="Start Time (HH:MM):")
start_time_label.grid(row=2, column=0, sticky='W')

start_time_entry = ttk.Entry(frame)
start_time_entry.grid(row=2, column=1)

start_period_label = ttk.Label(frame, text="Start Time Period (AM/PM):")
start_period_label.grid(row=3, column=0, sticky='W')

start_period_entry = ttk.Entry(frame)
start_period_entry.grid(row=3, column=1)

end_time_label = ttk.Label(frame, text="End Time (HH:MM):")
end_time_label.grid(row=4, column=0, sticky='W')

end_time_entry = ttk.Entry(frame)
end_time_entry.grid(row=4, column=1)

end_period_label = ttk.Label(frame, text="End Time Period (AM/PM):")
end_period_label.grid(row=5, column=0, sticky='W')

end_period_entry = ttk.Entry(frame)
end_period_entry.grid(row=5, column=1)

add_task_button = ttk.Button(frame, text="Add Task", command=lambda: taskLogger.add_task_to_log(task_name_entry.get(), date_entry.get(), start_time_entry.get(), start_period_entry.get(), end_time_entry.get(), end_period_entry.get(), "task_log.xlsx"))
add_task_button.grid(row=6, column=0, pady=5)

clear_fields_button = ttk.Button(frame, text="Clear Fields", command=lambda: clear_fields(task_name_entry, date_entry, start_time_entry, start_period_entry, end_time_entry, end_period_entry))
clear_fields_button.grid(row=6, column=1, pady=5)

# Define the function to clear the fields
def clear_fields(*entries):
    for entry in entries:
        entry.delete(0, 'end')

view_task_list_button = ttk.Button(frame, text="View Tasks", command=taskListGUI.show)
view_task_list_button.grid(row=7, column=0, pady=5)

exit_button = ttk.Button(frame, text="Exit", command=root.destroy)
exit_button.grid(row=7, column=1, pady=5)

# Run the root window's main loop
root.mainloop()