# Task Logger - A Simple Way to Calculate Hours for Billing

Task Logger is a simple desktop application designed to help you track and manage your tasks efficiently. The application allows you to input detailed task information, including task name, dates, start and end times, and time periods (AM/PM). It calculates the duration of tasks in decimal hours, stores task information in an Excel file, and provides an easy-to-use interface for viewing and managing tasks. Additionally, it integrates with Google Calendar to add and remove tasks as calendar events.

## Features

- **Add Tasks**: Input task name, start date, end date, start time, end time, time periods (AM/PM), timezone, and attendees.
- **Duration Calculation**: Automatically calculates the duration of tasks in decimal hours, accounting for tasks that span multiple days.
- **Excel Storage**: Stores task information in an Excel file (`task_log.xlsx`).
- **View Tasks**: Displays the list of tasks in a tabular format.
- **Manage Tasks**: Refresh the task list and remove tasks as needed.
- **Google Calendar Integration**: Adds tasks to Google Calendar and removes them when deleted.
- **User-Friendly Interface**: Built using CustomTkinter, providing a modern and intuitive user experience.

## Usage

### Running the Application

1. Ensure you have Python and the required libraries installed (`pandas`, `openpyxl`, `customtkinter`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client`).
2. Run the main script `taskLoggerGUI.py` to launch the Task Logger application.

### Adding Tasks

1. Enter the task name in the "Task Name" field.
2. Input the start date and end date in the "Start Date" and "End Date" fields, respectively (format: YYYY-MM-DD).
3. Enter the start time and end time in the "Start Time" and "End Time" fields (format: HH:MM).
4. Set the AM/PM period for both start and end times using the toggle switch.
5. Select the appropriate timezone from the dropdown menu.
6. Enter the email addresses of attendees (if any) separated by commas in the "Attendees" field.
7. Click the "Add Task" button to save the task to the log file and add it to Google Calendar.

### Viewing and Managing Tasks

1. Click the "View Tasks" button to display the list of tasks.
2. Use the "Refresh" button to update the task list.
3. Select a task and click the "Remove Task" button to delete it from the log file and remove it from Google Calendar.
4. Select a task and click the "Modify Task" button to edit the task details. Make the necessary changes and save them.

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
    pip install pandas openpyxl customtkinter google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
    ```
4. Obtain Google API credentials:
    - Follow the instructions at [Google Calendar API Quickstart](https://developers.google.com/calendar/api/quickstart/python) to create a project in the Google Cloud Console.
    - Enable the Google Calendar API for your project.
    - Create OAuth 2.0 Client IDs and download the `credentials.json` file.
    - Place the `credentials.json` file in the project directory.
5. Run the application:
    ```bash
    python taskLoggerGUI.py
    ```
6. Authorize the application to access your Google Calendar when prompted.

## Contributing

If you would like to contribute to the development of Task Logger, please fork the repository and submit a pull request with your changes. Contributions are welcome and appreciated!