@echo off
REM Quick launcher for Lambda Error Search
REM Usage: search_errors.bat [hours]

setlocal

echo ================================================================================
echo Lambda Error Search with Source Code Mapping
echo ================================================================================
echo.

REM Check if hours parameter provided
if "%1"=="" (
    set HOURS=1
) else (
    set HOURS=%1
)

echo Searching email-worker-function logs from last %HOURS% hour(s)...
echo.

python search_lambda_errors_with_code.py email-worker-function %HOURS%

if errorlevel 1 (
    echo.
    echo Error occurred during search. Make sure:
    echo   1. Python is installed and in PATH
    echo   2. boto3 is installed: pip install boto3
    echo   3. AWS credentials are configured
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Search complete!
echo ================================================================================
pause

