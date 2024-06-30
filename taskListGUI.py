import customtkinter as ctk
import tkinter.ttk as ttk
import pytz
import pandas as pd
from tkinter import messagebox
import os
import taskLogger
from datetime import datetime

class TaskListApp:
    def __init__(self, rootTaskList):
        self.rootTaskList = rootTaskList
        self.rootTaskList.title("Task List")
        self.rootTaskList.geometry("1000x300")

        self.setup_treeview()
        self.setup_buttons()

        self.show_tasks("task_log.xlsx")

    def setup_treeview(self):
        self.task_tree = ttk.Treeview(self.rootTaskList, columns=("id", "task", "start_date", "start_time", "start_am_pm", "end_date", "end_time", "end_am_pm", "timezone", "hours", "event_id"))
        self.task_tree["show"] = "headings"

        columns = {
            "id": {"text": "ID", "width": 0, "stretch": False, "anchor": "center"},
            "task": {"text": "Task", "width": 150, "anchor": "w", "stretch": True},
            "start_date": {"text": "Start Date", "width": 100, "anchor": "w", "stretch": True},
            "start_time": {"text": "Start Time", "width": 100, "anchor": "w", "stretch": True},
            "start_am_pm": {"text": "Start AM/PM", "width": 80, "anchor": "center", "stretch": True},
            "end_date": {"text": "End Date", "width": 100, "anchor": "w", "stretch": True},
            "end_time": {"text": "End Time", "width": 100, "anchor": "w", "stretch": True},
            "end_am_pm": {"text": "End AM/PM", "width": 80, "anchor": "center", "stretch": True},
            "timezone": {"text": "Timezone", "width": 150, "anchor": "w", "stretch": True},
            "hours": {"text": "Decimal Hours", "width": 100, "anchor": "w", "stretch": True},
            "event_id": {"text": "Event ID", "width": 0, "stretch": False, "anchor": "center"},
        }

        for col, specs in columns.items():
            self.task_tree.heading(col, text=specs["text"])
            self.task_tree.column(col, anchor=specs["anchor"], width=specs["width"], stretch=specs["stretch"])

        self.task_tree.pack(fill="both", expand=True)

    def setup_buttons(self):
        self.refresh_button = ctk.CTkButton(self.rootTaskList, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="left", padx=(10, 0), pady=(10, 10))

        self.remove_task_button = ctk.CTkButton(self.rootTaskList, text="Remove Task", command=self.remove_task, fg_color="red")
        self.remove_task_button.pack(side="left", padx=(10, 0), pady=(10, 10))

        self.modify_task_button = ctk.CTkButton(self.rootTaskList, text="Modify Task", command=self.modify_task)
        self.modify_task_button.pack(side="left", padx=(10, 0), pady=(10, 10))

    def refresh(self):
        self.show_tasks("task_log.xlsx")

    def remove_task(self):
        selected_item = self.task_tree.focus()
        if selected_item == '':
            return
        item = self.task_tree.item(selected_item)
        task_id = item['values'][0]
        event_id = item['values'][10]  # Assuming the 11th column contains the Event ID
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to remove this task?")
        if confirm:
            df = pd.read_excel("task_log.xlsx")
            df = df[df['ID'] != task_id]
            df.to_excel("task_log.xlsx", index=False)
            self.task_tree.delete(selected_item)
            try:
                taskLogger.remove_event_from_calendar(event_id)
            except Exception as e:
                print(f"Error removing event from calendar: {e}")

    def modify_task(self):
        selected_item = self.task_tree.focus()
        if selected_item == '':
            messagebox.showwarning("Warning", "No task selected.")
            return
        item = self.task_tree.item(selected_item)
        task_details = item['values']
        
        # Load the details into the input fields
        modify_window = ctk.CTkToplevel(self.rootTaskList)
        modify_window.title("Modify Task")
        modify_window.geometry("350x350")
        
        modify_frame = ctk.CTkFrame(modify_window, fg_color="transparent")
        modify_frame.pack(pady=20, padx=20, fill="both", expand=True)

        task_name_label = ctk.CTkLabel(modify_frame, text="Task Name:")
        task_name_label.grid(row=0, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        task_name_entry = ctk.CTkEntry(modify_frame)
        task_name_entry.grid(row=0, column=1, pady=(0, 5), padx=(0, 5))
        task_name_entry.insert(0, task_details[1])

        date_label = ctk.CTkLabel(modify_frame, text="Start Date (YYYY-MM-DD):")
        date_label.grid(row=1, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        date_entry = ctk.CTkEntry(modify_frame)
        date_entry.grid(row=1, column=1, pady=(0, 5), padx=(0, 5))
        date_entry.insert(0, task_details[2])

        start_time_label = ctk.CTkLabel(modify_frame, text="Start Time (HH:MM):")
        start_time_label.grid(row=2, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        start_time_entry = ctk.CTkEntry(modify_frame)
        start_time_entry.grid(row=2, column=1, pady=(0, 5), padx=(0, 5))
        start_time_entry.insert(0, task_details[3])

        start_period_label = ctk.CTkLabel(modify_frame, text="Start AM/PM:")
        start_period_label.grid(row=3, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        start_period_toggle = ctk.CTkSwitch(modify_frame, text="AM/PM")
        start_period_toggle.grid(row=3, column=1, pady=(0, 5), padx=(0, 5))
        if task_details[4] == "PM":
            start_period_toggle.select()

        end_date_label = ctk.CTkLabel(modify_frame, text="End Date (YYYY-MM-DD):")
        end_date_label.grid(row=4, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        end_date_entry = ctk.CTkEntry(modify_frame)
        end_date_entry.grid(row=4, column=1, pady=(0, 5), padx=(0, 5))
        end_date_entry.insert(0, task_details[5])

        end_time_label = ctk.CTkLabel(modify_frame, text="End Time (HH:MM):")
        end_time_label.grid(row=5, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        end_time_entry = ctk.CTkEntry(modify_frame)
        end_time_entry.grid(row=5, column=1, pady=(0, 5), padx=(0, 5))
        end_time_entry.insert(0, task_details[6])

        end_period_label = ctk.CTkLabel(modify_frame, text="End AM/PM:")
        end_period_label.grid(row=6, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        end_period_toggle = ctk.CTkSwitch(modify_frame, text="AM/PM")
        end_period_toggle.grid(row=6, column=1, pady=(0, 5), padx=(0, 5))
        if task_details[7] == "PM":
            end_period_toggle.select()

        # Timezone selection
        timezone_label = ctk.CTkLabel(modify_frame, text="Timezone:")
        timezone_label.grid(row=7, column=0, sticky='W', pady=(0, 5), padx=(0, 5))

        timezones = pytz.all_timezones
        timezone_combobox = ctk.CTkComboBox(modify_frame, values=timezones)
        timezone_combobox.grid(row=7, column=1, pady=(0, 5), padx=(0, 5))
        timezone_combobox.set(task_details[8])

        def save_changes():
            task_name = task_name_entry.get()
            start_date = date_entry.get()
            start_time = start_time_entry.get()
            start_period = "PM" if start_period_toggle.get() else "AM"
            end_date = end_date_entry.get()
            end_time = end_time_entry.get()
            end_period = "PM" if end_period_toggle.get() else "AM"
            timezone = timezone_combobox.get()
            
            # Convert to datetime objects
            start_time_24 = taskLogger.convert_to_24hour(start_time, start_period)
            start_datetime = datetime.strptime(f"{start_date} {start_time_24}", '%Y-%m-%d %H:%M')
            end_time_24 = taskLogger.convert_to_24hour(end_time, end_period)
            end_datetime = datetime.strptime(f"{end_date} {end_time_24}", '%Y-%m-%d %H:%M')
            
            # Update task in the Excel file
            df = pd.read_excel("task_log.xlsx")
            df.loc[df['ID'] == task_details[0], ['Task', 'Start Date', 'Start Time', 'Start AM/PM', 'End Date', 'End Time', 'End AM/PM', 'Timezone']] = [task_name, start_date, start_time, start_period, end_date, end_time, end_period, timezone]
            df.to_excel("task_log.xlsx", index=False)

            # Update the event in Google Calendar
            try:
                taskLogger.remove_event_from_calendar(task_details[10])
            except Exception as e:
                print(f"Error removing event from calendar: {e}")
            
            new_event_id = taskLogger.add_event_to_calendar(task_details[0], task_name, start_datetime, end_datetime, timezone)
            df.loc[df['ID'] == task_details[0], 'Event ID'] = new_event_id
            df.to_excel("task_log.xlsx", index=False)

            self.refresh()
            modify_window.destroy()

        save_button = ctk.CTkButton(modify_frame, text="Save Changes", command=save_changes, fg_color="green")
        save_button.grid(row=8, column=0, columnspan=2, pady=(10, 5), padx=(0, 5), sticky='ew')

    def show_tasks(self, file_name):
        self.task_tree.delete(*self.task_tree.get_children())
        if not os.path.exists(file_name):
            df = pd.DataFrame(columns=["ID", "Task", "Start Date", "Start Time", "Start AM/PM", "End Date", "End Time", "End AM/PM", "Timezone", "Decimal Hours", "Event ID"])
            df.to_excel(file_name, index=False)
        else:
            df = pd.read_excel(file_name)
            if "Start Date" not in df.columns or "End Date" not in df.columns or "Event ID" not in df.columns:
                df = pd.DataFrame(columns=["ID", "Task", "Start Date", "Start Time", "Start AM/PM", "End Date", "End Time", "End AM/PM", "Timezone", "Decimal Hours", "Event ID"])
                df.to_excel(file_name, index=False)

        for index, row in df.iterrows():
            self.task_tree.insert("", "end", values=(row['ID'], row['Task'], row['Start Date'], row['Start Time'], row['Start AM/PM'], row['End Date'], row['End Time'], row['End AM/PM'], row['Timezone'], row['Decimal Hours'], row.get('Event ID', '')))

if __name__ == '__main__':
    rootTaskList = ctk.CTk()
    TaskListApp(rootTaskList)
    rootTaskList.mainloop()

def show():
    rootTaskList = ctk.CTk()
    TaskListApp(rootTaskList)
    rootTaskList.mainloop()
