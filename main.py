#!/usr/bin/env python3
"""
WIFI Manager - Application Desktop pour scanner le réseau Wi-Fi
Affiche tous les appareils connectés via ARP scan et PyQt5
"""

import sys
import os

# Ajoute le répertoire courant au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    """Point d'entrée principal de l'application."""
    
    # Crée l'application PyQt
    app = QApplication(sys.argv)
    
    try:
        # Crée et affiche la fenêtre principale
        window = MainWindow()
        window.show()
        
        # Lance la boucle d'événements
        sys.exit(app.exec_())
    
    except ImportError as e:
        QMessageBox.critical(
            None,
            "Erreur d'import",
            f"Erreur lors du chargement des dépendances:\n{e}\n\n"
            "Assurez-vous d'avoir installé toutes les dépendances:\n"
            "pip install -r requirements.txt"
        )
        sys.exit(1)
    
    except PermissionError:
        QMessageBox.critical(
            None,
            "Erreur de permissions",
            "L'accès au réseau a été refusé.\n\n"
            "Windows: Exécutez le programme en tant qu'Administrateur\n"
            "Linux/Mac: Exécutez avec 'sudo' ou ayez les permissions réseau"
        )
        sys.exit(1)
    
    except Exception as e:
        QMessageBox.critical(
            None,
            "Erreur fatale",
            f"Une erreur inattendue s'est produite:\n{e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
