import customtkinter as ctk
import tkinter.ttk as ttk
import pandas as pd
from tkinter import messagebox
import os

class TaskListApp:
    def __init__(self, rootTaskList):
        self.rootTaskList = rootTaskList
        self.rootTaskList.title("Task List")
        self.rootTaskList.geometry("900x300")

        self.setup_treeview()
        self.setup_buttons()

        self.show_tasks("task_log.xlsx")

    def setup_treeview(self):
        self.task_tree = ttk.Treeview(self.rootTaskList, columns=("id", "start_date", "end_date", "task", "start_time", "start_am_pm", "end_time", "end_am_pm", "hours"))
        self.task_tree["show"] = "headings"

        columns = {
            "id": {"text": "ID", "width": 0, "stretch": False, "anchor": "center"},
            "start_date": {"text": "Start Date", "width": 100, "anchor": "w", "stretch": True},
            "end_date": {"text": "End Date", "width": 100, "anchor": "w", "stretch": True},
            "task": {"text": "Task", "width": 150, "anchor": "w", "stretch": True},
            "start_time": {"text": "Start Time", "width": 100, "anchor": "w", "stretch": True},
            "start_am_pm": {"text": "AM/PM", "width": 50, "anchor": "center", "stretch": True},
            "end_time": {"text": "End Time", "width": 100, "anchor": "w", "stretch": True},
            "end_am_pm": {"text": "AM/PM", "width": 50, "anchor": "center", "stretch": True},
            "hours": {"text": "Decimal Hours", "width": 100, "anchor": "w", "stretch": True},
        }

        for col, specs in columns.items():
            self.task_tree.heading(col, text=specs["text"])
            self.task_tree.column(col, anchor=specs["anchor"], width=specs["width"], stretch=specs["stretch"])

        self.task_tree.pack(fill="both", expand=True)

    def setup_buttons(self):
        self.refresh_button = ctk.CTkButton(self.rootTaskList, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="left", padx=(10, 0), pady=(10, 10))

        self.remove_task_button = ctk.CTkButton(self.rootTaskList, text="Remove Task", command=self.remove_task)
        self.remove_task_button.pack(side="left", padx=(10, 0), pady=(10, 10))

    def refresh(self):
        self.show_tasks("task_log.xlsx")

    def remove_task(self):
        selected_item = self.task_tree.focus()
        if selected_item == '':
            return
        item = self.task_tree.item(selected_item)
        task_id = item['values'][0]
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to remove this task?")
        if confirm:
            df = pd.read_excel("task_log.xlsx")
            df = df[df['ID'] != task_id]
            df.to_excel("task_log.xlsx", index=False)
            self.task_tree.delete(selected_item)

    def show_tasks(self, file_name):
        self.task_tree.delete(*self.task_tree.get_children())
        if not os.path.exists(file_name):
            df = pd.DataFrame(columns=["ID", "Start Date", "End Date", "Task", "Start Time", "Start AM/PM", "End Time", "End AM/PM", "Decimal Hours"])
            df.to_excel(file_name, index=False)
        else:
            df = pd.read_excel(file_name)
            if "Start Date" not in df.columns or "End Date" not in df.columns:
                df = pd.DataFrame(columns=["ID", "Start Date", "End Date", "Task", "Start Time", "Start AM/PM", "End Time", "End AM/PM", "Decimal Hours"])
                df.to_excel(file_name, index=False)
        
        for index, row in df.iterrows():
            self.task_tree.insert("", "end", values=(row['ID'], row['Start Date'], row['End Date'], row['Task'], row['Start Time'], row['Start AM/PM'], row['End Time'], row['End AM/PM'], row['Decimal Hours']))

if __name__ == '__main__':
    rootTaskList = ctk.CTk()
    TaskListApp(rootTaskList)
    rootTaskList.mainloop()

def show():
    rootTaskList = ctk.CTk()
    TaskListApp(rootTaskList)
    rootTaskList.mainloop()
