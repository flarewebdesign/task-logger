import tkinter as tk
import tkinter.ttk as ttk
import pandas as pd
from tkinter import messagebox

class TaskListApp:
    def __init__(self, rootTaskList):
        self.rootTaskList = rootTaskList
        self.rootTaskList.title("Task List")
        self.rootTaskList.geometry("800x300")
        
        self.task_tree = ttk.Treeview(self.rootTaskList, columns=("date", "task", "start", "start_am_pm", "end", "end_am_pm", "hours"))
        #remove extra column
        self.task_tree["show"] = "headings"
        #set column headings
        self.task_tree.heading("date", text="Date")
        self.task_tree.column("date", anchor="w", width=100)
        self.task_tree.heading("task", text="Task")
        self.task_tree.column("task", anchor="w", width=150)
        self.task_tree.heading("start", text="Start Time")
        self.task_tree.column("start", anchor="w", width=100)
        self.task_tree.heading("start_am_pm", text="AM/PM")
        self.task_tree.column("start_am_pm", anchor="center", width=50)
        self.task_tree.heading("end", text="End Time")
        self.task_tree.column("end", anchor="w", width=100)
        self.task_tree.heading("end_am_pm", text="AM/PM")
        self.task_tree.column("end_am_pm", anchor="center", width=50)
        self.task_tree.heading("hours", text="Decimal Hours")
        self.task_tree.column("hours", anchor="w", width=100)
        self.task_tree.pack(fill="both", expand=True)
        
        #show tasks
        self.show_tasks("task_log.xlsx")

        #buttons
        self.refresh_button = ttk.Button(self.rootTaskList, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="left", padx=(10, 0), pady=(10, 10))
        
        self.remove_task_button = ttk.Button(self.rootTaskList, text="Remove Task", command=self.remove_task)
        self.remove_task_button.pack(side="left", padx=(10, 0), pady=(10, 10))

    #refresh treeview
    def refresh(self):
        self.show_tasks("task_log.xlsx")

    #remove task
    def remove_task(self):
        selected_item = self.task_tree.focus()
        if selected_item == '':
            return
        item = self.task_tree.item(selected_item)
        task = item['values'][1]
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to remove this task?")
        if confirm:
            df = pd.read_excel("task_log.xlsx")
            df = df[df['Task'] != task]
            df.to_excel("task_log.xlsx", index=False)
            self.task_tree.delete(selected_item)

    #show tasks
    def show_tasks(self, file_name):
        self.task_tree.delete(*self.task_tree.get_children())
        df = pd.read_excel(file_name)
        for index, row in df.iterrows():
            self.task_tree.insert("", "end", values=(row['Date'], row['Task'], f"{row['Start Time']}", row['Start AM/PM'], f"{row['End Time']}", row['End AM/PM'], f"{row['Decimal Hours']}"))

#main
if __name__ == '__main__':
    rootTaskList = tk.Tk()
    TaskListApp(rootTaskList)
    rootTaskList.mainloop()

# Path: TaskLogger-0.0.3/taskLoggerGUI.py
def show():
        rootTaskList = tk.Tk()
        TaskListApp(rootTaskList)
        rootTaskList.mainloop()






