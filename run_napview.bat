@echo off
setlocal

:: Set Python path explicitly
set PYTHON_PATH=%~dp0python\python.exe

:: Check if Python exists
if not exist "%PYTHON_PATH%" (
    echo Python not found at: %PYTHON_PATH%
    exit /b 1
)

:: Launch the backend with error handling
"%PYTHON_PATH%" -m napview_backend
if errorlevel 1 (
    echo Backend failed to start
    pause
    exit /b 1
)

endlocal