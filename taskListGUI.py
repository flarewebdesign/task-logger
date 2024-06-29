import customtkinter as ctk
import tkinter.ttk as ttk
import pytz
import pandas as pd
from tkinter import messagebox
import os
import taskLogger

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
            taskLogger.remove_event_from_calendar(event_id)

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
