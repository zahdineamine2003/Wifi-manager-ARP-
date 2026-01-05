#!/bin/bash
# Script d'installation et lancement de WIFI Manager sur Linux/macOS

echo ""
echo "============================================"
echo "   WIFI Manager - Script d'installation"
echo "============================================"
echo ""

# Vérifie Python
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python 3 n'est pas installé"
    echo "Installez Python 3 via votre gestionnaire de paquets"
    exit 1
fi

echo "[OK] Python 3 détecté"

# Crée et active l'environnement virtuel
if [ ! -d "venv" ]; then
    echo ""
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Installe les dépendances
echo ""
echo "Installation des dépendances..."
pip install -r requirements.txt

echo ""
echo "============================================"
echo "   Installation terminée!"
echo "============================================"
echo ""

echo "Options:"
echo "1. Lancer l'application (nécessite sudo)"
echo "2. Exécuter les tests"
echo "3. Compiler en exécutable (PyInstaller)"
echo ""

read -p "Votre choix (1/2/3) ou appuyez sur Enter pour quitter: " choice

case $choice in
    1)
        echo ""
        echo "Lancement de WIFI Manager..."
        echo "(L'application s'exécute avec sudo pour l'accès réseau)"
        sudo python3 main.py
        ;;
    2)
        echo ""
        echo "Exécution des tests..."
        python3 test_units.py
        ;;
    3)
        echo ""
        echo "Installation de PyInstaller..."
        pip install pyinstaller
        echo ""
        echo "Compilation en exécutable..."
        pyinstaller --noconsole --onefile --name "WIFI_Manager" main.py
        echo ""
        echo "[OK] Exécutable créé: dist/WIFI_Manager"
        echo "Exécutez avec: sudo ./dist/WIFI_Manager"
        ;;
    *)
        echo "Quitter..."
        ;;
esac

deactivate
