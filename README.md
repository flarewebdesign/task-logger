﻿# Task Logger - A Simple Way to Calculate Hours for Billing

Task Logger is a simple desktop application designed to help you track and manage your tasks efficiently. The application allows you to input detailed task information, including task name, dates, start and end times, and time periods (AM/PM). It calculates the duration of tasks in decimal hours, stores task information in an Excel file, and provides an easy-to-use interface for viewing and managing tasks.

## Features

- **Add Tasks**: Input task name, start date, end date, start time, end time, and time periods (AM/PM).
- **Duration Calculation**: Automatically calculates the duration of tasks in decimal hours, accounting for tasks that span multiple days.
- **Excel Storage**: Stores task information in an Excel file (`task_log.xlsx`).
- **View Tasks**: Displays the list of tasks in a tabular format.
- **Manage Tasks**: Refresh the task list and remove tasks as needed.
- **User-Friendly Interface**: Built using CustomTkinter, providing a modern and intuitive user experience.

## Usage

### Running the Application

1. Ensure you have Python and the required libraries installed (`pandas`, `openpyxl`, `customtkinter`).
2. Run the main script `taskLoggerGUI.py` to launch the Task Logger application.

### Adding Tasks

1. Enter the task name in the "Task Name" field.
2. Input the start date and end date in the "Start Date" and "End Date" fields, respectively (format: YYYY-MM-DD).
3. Enter the start time and end time in the "Start Time" and "End Time" fields (format: HH:MM).
4. Set the AM/PM period for both start and end times using the toggle switch.
5. Click the "Add Task" button to save the task to the log file.

### Viewing and Managing Tasks

1. Click the "View Tasks" button to display the list of tasks.
2. Use the "Refresh" button to update the task list.
3. Select a task and click the "Remove Task" button to delete it from the log file.

## Use Cases

Task Logger can be used for a variety of service-based jobs, such as:

- **Freelancers**: Keep track of billable hours for multiple clients and projects.
- **Consultants**: Log time spent on different tasks and generate reports for clients.
- **Service Technicians**: Record the start and end times of service calls.
- **Project Managers**: Monitor task durations and manage team workloads.
- **Remote Workers**: Track time spent on different assignments throughout the day.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/flarewebdesign/task-logger.git
    ```
2. Navigate to the project directory:
    ```bash
    cd task-logger
    ```
3. Install the required libraries:
    ```bash
    pip install pandas openpyxl customtkinter
    ```
4. Run the application:
    ```bash
    python taskLoggerGUI.py
    ```

## Contributing

If you would like to contribute to the development of Task Logger, please fork the repository and submit a pull request with your changes. Contributions are welcome and appreciated!
