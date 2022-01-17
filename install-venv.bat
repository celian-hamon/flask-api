@echo off

IF EXIST "venv" (
    echo "Virtual environment already exists"

    exit /b 0
) ELSE (
    python -m venv venv

    "venv\Scripts\pip" install -r requirements.txt
    exit /b 0
)
