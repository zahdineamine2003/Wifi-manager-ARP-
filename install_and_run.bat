@echo off
REM Script d'installation et lancement de WIFI Manager sur Windows

setlocal enabledelayedexpansion

echo.
echo ============================================
echo   WIFI Manager - Script d'installation
echo ============================================
echo.

REM Vérifie Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou pas dans le PATH
    echo Téléchargez Python depuis https://www.python.org
    pause
    exit /b 1
)

echo [OK] Python détecté

REM Crée et active l'environnement virtuel
if not exist venv (
    echo.
    echo Création de l'environnement virtuel...
    python -m venv venv
)

echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installe les dépendances
echo.
echo Installation des dépendances...
pip install -r requirements.txt

echo.
echo ============================================
echo   Installation terminée!
echo ============================================
echo.

echo Options:
echo 1. Lancer l'application (nécessite Admin)
echo 2. Exécuter les tests
echo 3. Compiler en .EXE (PyInstaller)
echo.

set /p choice="Votre choix (1/2/3) ou appuyez sur Enter pour quitter: "

if "%choice%"=="1" (
    echo.
    echo Lancement de WIFI Manager...
    echo (Assurez-vous d'être en tant qu'Administrateur!)
    python main.py
) else if "%choice%"=="2" (
    echo.
    echo Exécution des tests...
    python test_units.py
) else if "%choice%"=="3" (
    echo.
    echo Installation de PyInstaller...
    pip install pyinstaller
    echo.
    echo Compilation en .EXE...
    pyinstaller --noconsole --onefile --name "WIFI_Manager" main.py
    echo.
    echo [OK] Fichier créé: dist\WIFI_Manager.exe
    echo Exécutez en tant qu'Administrateur!
) else (
    echo Quitter...
)

pause
