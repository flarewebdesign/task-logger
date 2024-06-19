import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime
import os
import uuid

# Convert time to 24-hour format
def convert_to_24hour(time, period):
    hour, minute = time.split(":")
    hour = int(hour)
    if period == "PM" and hour != 12:
        hour += 12
    if period == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"

# Add task information to log
def add_task_to_log(task_name, date, start_time, start_period, end_time, end_period, task_log):
    # Convert start and end times to 24-hour format
    start_time_24 = convert_to_24hour(start_time, start_period)
    start_time_24 = datetime.strptime(f"{date} {start_time_24}", '%Y-%m-%d %H:%M')
    
    # Convert end time to 24-hour format
    end_time_24 = convert_to_24hour(end_time, end_period)
    end_time_24 = datetime.strptime(f"{date} {end_time_24}", '%Y-%m-%d %H:%M')
    
    # Calculate hours worked
    delta = end_time_24 - start_time_24
    hours_worked = delta.total_seconds() / 3600
    
    if os.path.exists(task_log):
        wb = openpyxl.load_workbook(task_log)
        sheet = wb.active
    else:
        # Create new log file
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.append(["ID", "Date", "Task", "Start Time", "Start AM/PM", "End Time", "End AM/PM", "Decimal Hours"])
    
    # Generate a unique ID for the task
    task_id = str(uuid.uuid4())

    task_data = [task_id, date, task_name, start_time, start_period, end_time, end_period, hours_worked]
    
    # Append the new task to the sheet
    sheet.append(task_data)
    wb.save(task_log)
    print(f"Task information added to '{task_log}'.")

# Main function
def main():
    task_log = "task_log.xlsx"

    while True:
        # Get task information
        task_name = input("Enter task name: ")
        date = input("Enter date (YYYY-MM-DD): ")
        start_time = input("Enter start time (HH:MM): ")
        start_period = input("Enter start time period (AM/PM): ")
        end_time = input("Enter end time (HH:MM): ")
        end_period = input("Enter end time period (AM/PM): ")

        add_task_to_log(task_name, date, start_time, start_period, end_time, end_period, task_log)
        print("Task added.\n")

if __name__ == "__main__":
    main()