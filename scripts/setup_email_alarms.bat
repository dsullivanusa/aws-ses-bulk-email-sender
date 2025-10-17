@echo off
REM Quick launcher to create email failure alarms

echo ================================================================================
echo Creating Email Failure CloudWatch Alarms
echo ================================================================================
echo.

python create_email_failure_alarms.py

if errorlevel 1 (
    echo.
    echo Error occurred. Make sure:
    echo   1. Python is installed
    echo   2. boto3 is installed: pip install boto3
    echo   3. AWS credentials are configured
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo View alarm status:
echo   python view_alarm_status.py
echo.
echo View alarm history:
echo   python view_alarm_status.py --history
echo ================================================================================
pause

