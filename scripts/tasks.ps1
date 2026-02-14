param(
    [ValidateSet("help", "setup", "setup-google", "run", "check", "smoke")]
    [string]$Task = "help"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Ensure-Venv {
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating virtual environment at $VenvDir"
        & python -m venv $VenvDir
    }
}

function Run-InVenv {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )
    & $VenvPython @Arguments
}

function Show-Help {
    Write-Host "Task Logger automation script"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\tasks.ps1 <task>"
    Write-Host ""
    Write-Host "Tasks:"
    Write-Host "  help         Show this message"
    Write-Host "  setup        Create .venv and install core dependencies"
    Write-Host "  setup-google Create .venv and install core + Google dependencies"
    Write-Host "  run          Launch Task Logger from .venv"
    Write-Host "  check        Run syntax checks from .venv"
    Write-Host "  smoke        Run backend local-only smoke test from .venv"
}

Push-Location $RepoRoot
try {
    switch ($Task) {
        "help" {
            Show-Help
        }
        "setup" {
            Ensure-Venv
            Run-InVenv -Arguments @("-m", "pip", "install", "--upgrade", "pip")
            Run-InVenv -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
            Write-Host "Setup complete."
        }
        "setup-google" {
            Ensure-Venv
            Run-InVenv -Arguments @("-m", "pip", "install", "--upgrade", "pip")
            Run-InVenv -Arguments @("-m", "pip", "install", "-r", "requirements-google.txt")
            Write-Host "Google-enabled setup complete."
        }
        "run" {
            Ensure-Venv
            Run-InVenv -Arguments @("taskLoggerGUI.py")
        }
        "check" {
            Ensure-Venv
            Run-InVenv -Arguments @("-m", "py_compile", "taskLogger.py", "taskListGUI.py", "taskLoggerGUI.py")
            Write-Host "Syntax checks passed."
        }
        "smoke" {
            Ensure-Venv
            $smokeScript = @'
import os
import tempfile
import taskLogger

fd, path = tempfile.mkstemp(suffix=".xlsx")
os.close(fd)
os.remove(path)

result = taskLogger.add_task_to_log(
    task_name="smoke",
    start_date="2026-01-01",
    start_time="09:00",
    start_period="AM",
    end_date="2026-01-01",
    end_time="10:00",
    end_period="AM",
    timezone="UTC",
    task_log=path,
    attendees=["smoke@example.com"],
    sync_to_google=False,
)
assert result["task_id"]

update = taskLogger.update_task_in_log(
    task_id=result["task_id"],
    task_name="smoke-updated",
    start_date="2026-01-01",
    start_time="09:00",
    start_period="AM",
    end_date="2026-01-01",
    end_time="11:00",
    end_period="AM",
    timezone="UTC",
    task_log=path,
    attendees="smoke@example.com",
    sync_to_google=False,
)
assert update["task_id"] == result["task_id"]

taskLogger.remove_task_from_log(
    task_id=result["task_id"],
    task_log=path,
    sync_to_google=False,
)
loaded = taskLogger.load_task_log(path)
assert len(loaded) == 0

os.remove(path)
print("Smoke test passed.")
'@
            $smokeScript | & $VenvPython -
        }
    }
}
finally {
    Pop-Location
}
