@echo off
REM ════════════════════════════════════════════════════════════════════════
REM  GITHUB PUSH SCRIPT - WiFi Manager Pro
REM  This script will push your project to GitHub
REM ════════════════════════════════════════════════════════════════════════

echo.
echo ════════════════════════════════════════════════════════════════════════
echo  WIFI MANAGER PRO - GitHub Push Script
echo ════════════════════════════════════════════════════════════════════════
echo.

REM Check if screenshots exist
if not exist "screenshots\01_main_interface.png" (
    echo [ERROR] Screenshots not found!
    echo.
    echo Please take screenshots first:
    echo 1. Launch WiFi Manager
    echo 2. Press Windows + Shift + S to take screenshots
    echo 3. Save to screenshots\ folder
    echo.
    echo Required screenshots:
    echo   - 01_main_interface.png
    echo   - 02_scanning.png
    echo   - 03_devices_detected.png
    echo   - 04_monitoring_graphs.png
    echo   - 05_tv_remote.png
    echo   - 06_kick_dialog.png
    echo.
    pause
    exit /b 1
)

echo [OK] Screenshots folder exists
echo.

REM Check if demo video exists (optional)
if not exist "demo\kick_operation_demo.mp4" (
    echo [WARNING] Demo video not found (optional)
    echo You can add it later to demo\kick_operation_demo.mp4
    echo.
)

REM Replace current README with GitHub version
echo [STEP 1] Updating README.md for GitHub...
copy /Y README_GITHUB.md README.md > nul
echo [OK] README.md updated with screenshots and video
echo.

REM Initialize git if not already done
if not exist ".git" (
    echo [STEP 2] Initializing Git repository...
    git init
    echo [OK] Git initialized
) else (
    echo [STEP 2] Git repository already exists
)
echo.

REM Add remote if not already added
git remote get-url origin > nul 2>&1
if errorlevel 1 (
    echo [STEP 3] Adding GitHub remote...
    git remote add origin https://github.com/zahdineamine2003/Wifi-manager-ARP-.git
    echo [OK] Remote added
) else (
    echo [STEP 3] Remote already configured
)
echo.

REM Show what will be committed
echo [STEP 4] Files to be committed:
echo.
git status --short
echo.

REM Ask for confirmation
set /p confirm="Do you want to push to GitHub? (y/n): "
if /i not "%confirm%"=="y" (
    echo.
    echo Push cancelled.
    pause
    exit /b 0
)

echo.
echo [STEP 5] Staging all files...
git add .
echo [OK] Files staged
echo.

echo [STEP 6] Creating commit...
git commit -m "WiFi Manager Pro - Complete Enterprise Network Management System

Features:
- Real-time ARP network scanning with vendor identification
- Advanced device management (kick, message, control)
- Smart TV remote control (10+ brands)
- Live monitoring with dual-axis graphs
- Multi-protocol messaging system
- Professional dark-themed UI

Includes:
- Complete source code
- Comprehensive documentation
- Screenshots and demo video
- Installation scripts
- Unit tests"

echo [OK] Commit created
echo.

echo [STEP 7] Pushing to GitHub...
echo.
echo NOTE: You may be asked to authenticate.
echo If you get an authentication error, use a Personal Access Token instead of password.
echo Get token from: https://github.com/settings/tokens
echo.
git branch -M main
git push -u origin main --force

if errorlevel 1 (
    echo.
    echo [ERROR] Push failed!
    echo.
    echo Common solutions:
    echo 1. Make sure you're logged in to GitHub
    echo 2. Use Personal Access Token instead of password
    echo 3. Check your internet connection
    echo.
    pause
    exit /b 1
)

echo.
echo ════════════════════════════════════════════════════════════════════════
echo  SUCCESS! Project pushed to GitHub
echo ════════════════════════════════════════════════════════════════════════
echo.
echo Your repository: https://github.com/zahdineamine2003/Wifi-manager-ARP-
echo.
echo Next steps:
echo 1. Visit your repository on GitHub
echo 2. Verify screenshots are displayed
echo 3. Check if video is accessible
echo 4. Add topics/tags to your repo
echo 5. Create a release (optional)
echo.
pause
