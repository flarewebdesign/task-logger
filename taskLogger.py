import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
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
def add_task_to_log(task_name, start_date, end_date, start_time, start_period, end_time, end_period, task_log):
    try:
        start_time_24 = convert_to_24hour(start_time, start_period)
        start_datetime = datetime.strptime(f"{start_date} {start_time_24}", '%Y-%m-%d %H:%M')

        end_time_24 = convert_to_24hour(end_time, end_period)
        end_datetime = datetime.strptime(f"{end_date} {end_time_24}", '%Y-%m-%d %H:%M')

        if end_datetime < start_datetime:
            end_datetime += timedelta(days=1)

        hours_worked = (end_datetime - start_datetime).total_seconds() / 3600

        wb, sheet = open_task_log(task_log)

        task_id = str(uuid.uuid4())
        task_data = [task_id, start_date, end_date, task_name, start_time, start_period, end_time, end_period, hours_worked]

        sheet.append(task_data)
        wb.save(task_log)
        print(f"Task information added to '{task_log}'.")
    except Exception as e:
        print(f"Error adding task to log: {e}")

def open_task_log(task_log):
    if os.path.exists(task_log):
        wb = openpyxl.load_workbook(task_log)
        sheet = wb.active
        # Ensure the correct columns are present
        headers = ["ID", "Start Date", "End Date", "Task", "Start Time", "Start AM/PM", "End Time", "End AM/PM", "Decimal Hours"]
        if sheet.max_row == 0 or sheet[1][0].value != "ID":
            sheet.append(headers)
    else:
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.append(headers)
    return wb, sheet

def main():
    task_log = "task_log.xlsx"

    while True:
        task_name = input("Enter task name: ")
        start_date = input("Enter start date (YYYY-MM-DD): ")
        end_date = input("Enter end date (YYYY-MM-DD): ")
        start_time = input("Enter start time (HH:MM): ")
        start_period = input("Enter start time period (AM/PM): ")
        end_time = input("Enter end time (HH:MM): ")
        end_period = input("Enter end time period (AM/PM): ")

        add_task_to_log(task_name, start_date, end_date, start_time, start_period, end_time, end_period, task_log)
        print("Task added.\n")

if __name__ == "__main__":
    main()
