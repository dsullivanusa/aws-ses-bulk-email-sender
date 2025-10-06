@echo off
echo ============================================================
echo AWS SES Email System - Automated Fix Script
echo ============================================================
echo.
echo This script will fix:
echo   1. Contacts page pagination dropdown issue
echo   2. Send Campaign tab filtering issue
echo.
echo ============================================================

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if the main file exists
if not exist "bulk_email_api_lambda.py" (
    echo ERROR: bulk_email_api_lambda.py not found
    echo Please run this script from the correct directory
    pause
    exit /b 1
)

echo Starting automated fix process...
echo.

REM Run the automated fix script
python automated_fix_script.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo Fix completed successfully!
    echo ============================================================
    echo.
    echo Next steps:
    echo 1. Deploy the updated Lambda function
    echo 2. Test the fixes in your web application
    echo.
    
    REM Ask about deployment
    set /p deploy="Do you want to deploy now? (y/n): "
    if /i "%deploy%"=="y" (
        echo.
        echo Deploying Lambda function...
        python deploy_email_worker.py
    )
    
) else (
    echo.
    echo ============================================================
    echo Fix failed! Please check the error messages above.
    echo ============================================================
)

echo.
echo Press any key to exit...
pause >nul
