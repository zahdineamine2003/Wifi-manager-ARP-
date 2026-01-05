# WIFI Manager - Scanner ARP Desktop

Une application desktop Python+PyQt5 pour scanner tous les appareils connectés au même réseau Wi-Fi que votre PC.

## 🎯 Fonctionnalités

✅ **Scan ARP complet** - Découvre automatiquement tous les appareils sur un réseau  
✅ **Lookup Vendor (OUI)** - Identifie les marques des appareils via adresse MAC  
✅ **Ping optionnel** - Mesure la latence vers chaque appareil (mode slow)  
✅ **Interface moderne** - UI dark mode avec PyQt5  
✅ **Export CSV** - Sauvegarde les résultats en CSV UTF-8  
✅ **Threading propre** - L'UI ne se bloque jamais lors du scan  
✅ **Multi-plateforme** - Windows, Linux, macOS  
✅ **Gestion d'erreurs** - Messages clairs sur les permissions manquantes  

## 📋 Prérequis

- **Python 3.7+**
- **Permissions admin/root** (pour accéder à la couche réseau)
  - Windows: Exécutez en tant qu'Administrateur
  - Linux/Mac: Exécutez avec `sudo`

## 🚀 Installation

### 1. Cloner/Télécharger le projet

```bash
# Option 1: Si vous avez git
git clone <url-du-repo> WIFI_Manager
cd WIFI_Manager

# Option 2: Télécharger le ZIP et extraire
cd WIFI_Manager
```

### 2. Créer un environnement virtuel (recommandé)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## 💻 Utilisation

### Lancer l'application

```bash
# Windows (en tant qu'Administrateur)
python main.py

# Linux/Mac (avec sudo)
sudo python3 main.py
```

### Guide d'utilisation

1. **Champ CIDR**: Entrez le réseau à scanner (ex: `192.168.1.0/24`)
   - Cliquez sur "Auto-détect" pour suggestion automatique
   - Format: `<IP>/<CIDR>` (ex: `10.0.0.0/24`)

2. **Options**:
   - **Inclure ping**: Mesure la latence (plus lent)
   - **Timeout**: Délai d'attente pour les réponses ARP (1-10 secondes)

3. **Boutons**:
   - **Lancer le scan**: Démarre le scan ARP
   - **Rafraîchir**: Réaffiche les résultats actuels
   - **Export CSV**: Sauvegarde les résultats dans un fichier
   - **Effacer**: Vide la table et les logs
   - **Quitter**: Ferme l'application

4. **Résultats**: La table affiche:
   - Index (numéro d'ordre)
   - IP Address (adresse IP trouvée)
   - MAC Address (adresse MAC)
   - Vendor (marque de l'appareil)
   - Ping (latence en ms, si activé)

5. **Logs**: Zone en bas pour suivre la progression et les erreurs

## 📁 Structure du projet

```
WIFI_Manager/
├── main.py                          # Point d'entrée principal
├── requirements.txt                 # Dépendances Python
├── README.md                        # Ce fichier
│
├── scanner/                         # Module de scanning
│   ├── __init__.py
│   ├── arp_scanner.py              # Classe ARPScanner (Scapy)
│   └── utils.py                    # Utilitaires (OUI, CIDR, CSV, etc.)
│
├── ui/                              # Interface PyQt5
│   ├── __init__.py
│   └── main_window.py              # Classe MainWindow
│
└── assets/                          # Ressources
    └── icons/                       # Dossier pour icônes (futur)
```

## 🔧 Fichiers clés

### scanner/arp_scanner.py
- **ARPScanner**: Classe principale pour les scans ARP
  - `scan()`: Scan bloquant
  - `scan_async()`: Scan en arrière-plan (avec callbacks)
  - Support du ping optionnel
  - Gestion des erreurs et permissions

### scanner/utils.py
- **OUIDatabase**: Lookup des noms de marques à partir des adresses MAC
  - Télécharge la base OUI.txt depuis IEEE
  - Cache local dans `~/.wifi_manager/`
- **CIDRValidator**: Valide les adresses CIDR
- **CSVExporter**: Exporte les résultats en CSV
- **PingUtils**: Utilitaires pour les pings
- **AppConfig**: Configuration globale (styles, timeouts, etc.)

### ui/main_window.py
- **MainWindow**: Fenêtre principale PyQt5
  - Layout complet avec champs et boutons
  - Table des résultats avec alternance de couleurs
  - Zone de logs pour suivi
  - Threading pour éviter blocages UI

### main.py
- Point d'entrée
- Gestion des exceptions (imports, permissions, erreurs fatales)
- Création et affichage de l'application

## 🔍 Exemples d'utilisation

### Exemple 1: Scan simple du réseau local

1. Lancez l'application: `python main.py`
2. Le CIDR par défaut est `192.168.1.0/24` (généralement correct)
3. Cliquez sur "Lancer le scan"
4. Attendez 10-20 secondes
5. Les appareils s'affichent dans la table

### Exemple 2: Scan d'un autre réseau

1. Entrez le CIDR: `10.0.0.0/8` (réseau classe A)
2. Augmentez le timeout à 3-5 secondes
3. Lancez le scan

### Exemple 3: Export des résultats

1. Lancez un scan jusqu'à la fin
2. Cliquez sur "Export CSV"
3. Choisissez le dossier et le nom du fichier
4. Le fichier est créé avec timestamp: `scan_results_20250102_143022.csv`

### Exemple 4: Scan avec latences

1. Cochez "Inclure ping (slow)"
2. Lancez le scan
3. Attendez plus longtemps (2-3x plus long)
4. La colonne "Ping" affichera les latences en ms

## 📦 Packaging en .EXE (PyInstaller)

### Installation de PyInstaller

```bash
pip install pyinstaller
```

### Créer un .EXE unique

```bash
pyinstaller --noconsole --onefile --name "WIFI_Manager" main.py
```

Options:
- `--noconsole`: Masque la console Windows
- `--onefile`: Crée un seul fichier .exe
- `--name`: Nom du programme

Le fichier .exe sera créé dans `dist/WIFI_Manager.exe`

### Créer un .EXE avec dossier (version optimisée)

```bash
pyinstaller --noconsole --name "WIFI_Manager" main.py
```

Résultat: dossier `dist/WIFI_Manager/` avec tous les fichiers nécessaires (plus rapide au lancement)

### Options avancées

Pour ajouter une icône:

```bash
pyinstaller --noconsole --onefile --icon=assets/icons/app.ico --name "WIFI_Manager" main.py
```

(Créez une image `app.ico` dans `assets/icons/`)

## 🧪 Tests

Des tests unitaires peuvent être ajoutés. Voici des exemples manuels:

### Test 1: Validation CIDR

```python
from scanner import CIDRValidator

print(CIDRValidator.is_valid("192.168.1.0/24"))  # True
print(CIDRValidator.is_valid("256.1.1.1/24"))    # False
print(CIDRValidator.is_valid("10.0.0.0/8"))      # True
```

### Test 2: Lookup OUI

```python
from scanner import OUIDatabase

db = OUIDatabase()
vendor = db.lookup("08:00:27:00:00:00")  # Exemple
print(vendor)  # Affiche le nom du vendor
```

### Test 3: Validation IP

```python
from scanner import PingUtils

print(PingUtils.validate_ip("192.168.1.1"))  # True
print(PingUtils.validate_ip("999.999.999.999"))  # False
```

## ⚠️ Résolution de problèmes

### Erreur: "Permission denied" / "Access denied"

**Windows**:
- Relancez l'application en tant qu'**Administrateur**
- Clic droit → "Exécuter en tant qu'administrateur"

**Linux**:
```bash
sudo python3 main.py
```

**macOS**:
```bash
sudo python3 main.py
```

### Erreur: "No module named 'scapy'"

```bash
pip install -r requirements.txt
```

### Erreur: "No module named 'PyQt5'"

```bash
pip install PyQt5
```

### Le scan est très lent

- Vérifiez que le CIDR ne couvre pas trop d'IP (ex: `/8` = 16M d'IPs)
- Augmentez le timeout si le réseau est lent
- Désactivez "Inclure ping" (option très lente)

### L'application se fige pendant le scan

C'est normal pour Scapy (scanning réseau). Le UI ne devrait pas se figer si threading fonctionne correctement. Si UI bloquée:
- Rendez-vous aux logs pour voir où elle est
- Vérifiez que vous avez lancé avec les bonnes permissions

### Aucun appareil trouvé

- Vérifiez le CIDR (cliquez "Auto-détect")
- Vérifiez que vous êtes connecté au Wi-Fi
- Augmentez le timeout à 3-5 secondes
- Sur Linux, vérifiez que l'interface réseau correcte est utilisée

## 📊 Exemple de sortie CSV

```csv
Index,IP,MAC,Vendor,Ping (ms)
1,192.168.1.1,00:11:22:33:44:55,Tp-Link,2.5
2,192.168.1.5,08:00:27:00:00:00,VirtualBox,5.2
3,192.168.1.10,AA:BB:CC:DD:EE:FF,Asus,3.1
```

## 🔐 Sécurité

- L'application n'envoie aucune donnée externe (sauf download du fichier OUI au premier lancement)
- Les résultats restent locaux
- L'OUI.txt est téléchargé depuis le site officiel IEEE

## 📝 Licences des dépendances

- **PyQt5**: GPL v3
- **Scapy**: GPL v2
- **OUI.txt**: Public domain (IEEE)

## 🤝 Contribution

Pour contribuer:
1. Fork le projet
2. Créez une branche (`git checkout -b feature/ma-feature`)
3. Committer vos changements
4. Push et créez une Pull Request

## 📞 Support

Pour les problèmes:
1. Vérifiez la section "Résolution de problèmes"
2. Consultez les logs de l'application
3. Vérifiez les permissions admin/root

## ✨ Améliorations futures

- [ ] Icône personnalisée
- [ ] Dark/Light mode toggle
- [ ] Filtrage/recherche dans la table
- [ ] Enregistrement de scans historiques
- [ ] Géolocalisation des IPs
- [ ] Détection de modèles spécifiques
- [ ] Notifications en temps réel
- [ ] Configuration persistante

## 📄 Licence

MIT License - Vous êtes libre d'utiliser, modifier et distribuer ce projet

## 🎉 Conclusion

WIFI Manager est une application complète, propre et prête pour :
- Scanner votre réseau Wi-Fi
- Identifier tous les appareils connectés
- Exporter les résultats
- Être compilée en .exe pour distribution

Amusez-vous à explorer votre réseau! 🚀
