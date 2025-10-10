@echo off
REM Simple startup script for Material Library
REM Check Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found
    pause
    exit /b 1
)

REM Check main.py
if not exist "main.py" (
    echo Error: main.py not found
    pause
    exit /b 1
)

REM Start application
echo Starting Material Library Application...
python main.py

if %errorlevel% neq 0 (
    echo Application failed to start
    pause
)