# Guide d'utilisation complet - WIFI Manager

## Table des matières
1. [Installation rapide](#installation-rapide)
2. [Lancement de l'application](#lancement)
3. [Cas d'usage pratiques](#cas-dusage-pratiques)
4. [Dépannage](#dépannage)
5. [Compilation en EXE](#compilation-en-exe)

## Installation rapide

### Windows

```batch
# Téléchargez ou clonez le projet
cd WIFI_Manager

# Exécutez le script d'installation
install_and_run.bat

# Suivez les instructions
```

### Linux/macOS

```bash
# Téléchargez ou clonez le projet
cd WIFI_Manager

# Rendez le script exécutable
chmod +x install_and_run.sh

# Exécutez le script
./install_and_run.sh

# Suivez les instructions
```

## Lancement

### Option 1: Via le script (recommandé)

**Windows**:
```batch
install_and_run.bat
```

**Linux/macOS**:
```bash
./install_and_run.sh
```

### Option 2: Manuel

**Activation de l'environnement**:

Windows:
```batch
venv\Scripts\activate
```

Linux/macOS:
```bash
source venv/bin/activate
```

**Lancement de l'application**:

Windows (en tant qu'Admin):
```batch
python main.py
```

Linux/macOS (avec sudo):
```bash
sudo python3 main.py
```

### Option 3: Si compilé en EXE

Windows (en tant qu'Admin):
```batch
dist\WIFI_Manager.exe
```

## Cas d'usage pratiques

### Cas 1: Scanner votre réseau local

**Scénario**: Vous voulez voir tous les appareils connectés à votre Wi-Fi

**Étapes**:
1. Lancez l'application
2. Le CIDR par défaut (`192.168.1.0/24`) convient généralement
3. Cliquez sur "🔍 Lancer le scan"
4. Attendez 10-30 secondes
5. Les appareils apparaissent dans la table

**Résultat**: Table avec tous les appareils + leurs adresses MAC et marques

---

### Cas 2: Identifier un appareil mystérieux

**Scénario**: Quelqu'un s'est connecté à votre Wi-Fi et vous voulez savoir qui

**Étapes**:
1. Lancez un scan normal
2. Cherchez l'adresse IP/MAC inconnue
3. Regardez la colonne "Vendor" pour identifier la marque
4. Recherchez l'IP ou la MAC en ligne pour plus d'infos

**Exemple de résultat**:
```
IP: 192.168.1.50
MAC: 8C:AA:6C:XX:XX:XX
Vendor: Samsung Electronics
→ Probablement un téléphone ou tablette Samsung
```

---

### Cas 3: Tester la connectivité

**Scénario**: Vous voulez vérifier quels appareils répondent et leur latence

**Étapes**:
1. Cochez "Inclure ping (slow)"
2. Lancez le scan
3. Attendez 30-60 secondes (plus lent à cause des pings)
4. Regardez la colonne "Ping (ms)"

**Interprétation**:
- `< 5ms`: Très rapide (câble Ethernet ou Wi-Fi excellent)
- `5-20ms`: Normal (Wi-Fi standard)
- `20-50ms`: Lent (Wi-Fi faible, distance ou obstacles)
- `-`: Timeout (appareil ne répond pas ou off)

---

### Cas 4: Scanner un réseau différent

**Scénario**: Vous êtes à proximité d'un autre réseau (ex: réseau d'entreprise)

**Étapes**:
1. Obtenez le CIDR du réseau (ex: `10.0.0.0/24`)
2. Entrez-le dans le champ CIDR
3. Augmentez le timeout à 3-5 secondes (réseau peut être distant)
4. Lancez le scan

**Exemple**:
```
CIDR: 10.100.5.0/24
Timeout: 4 secondes
→ Scan de 256 adresses IP
```

---

### Cas 5: Exporter les résultats

**Scénario**: Vous voulez garder une trace des appareils trouvés

**Étapes**:
1. Lancez un scan jusqu'à la fin
2. Cliquez sur "💾 Export CSV"
3. Choisissez le dossier et le nom du fichier
4. Le fichier est créé avec timestamp

**Fichier généré**: `scan_results_20250102_143022.csv`

**Contenu**:
```csv
Index,IP,MAC,Vendor,Ping (ms)
1,192.168.1.1,00:11:22:33:44:55,TP-LINK,2.5
2,192.168.1.5,08:00:27:00:00:00,VirtualBox,5.2
...
```

---

### Cas 6: Automatiser les scans

**Scénario**: Vous voulez tester régulièrement votre réseau

**Solution**: Créez un script Python

**Script `auto_scan.py`**:
```python
#!/usr/bin/env python3
from scanner import ARPScanner, OUIDatabase, CSVExporter
from datetime import datetime

# Crée le scanner
scanner = ARPScanner(timeout=2)
oui_db = OUIDatabase()

# Effectue le scan
print("Scan en cours...")
results = scanner.scan("192.168.1.0/24")

# Ajoute les vendors
for device in results:
    device['vendor'] = oui_db.lookup(device['mac'])

# Exporte
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filepath = f"scan_{timestamp}.csv"
CSVExporter.export(results, filepath)

print(f"✓ Scan terminé: {len(results)} appareils")
print(f"✓ Exporté vers: {filepath}")
```

**Utilisation**:
```bash
python auto_scan.py
```

---

## Dépannage

### Le scan ne trouve aucun appareil

**Cause probable**: Mauvais CIDR ou réseau non accessible

**Solution**:
1. Cliquez sur "Auto-détect" pour suggestion automatique
2. Vérifiez que vous êtes connecté au réseau
3. Vérifiez l'adresse IP locale:
   - Windows: `ipconfig` (cherchez "IPv4")
   - Linux/Mac: `ifconfig` (cherchez "inet")

**Exemple**:
```
Si votre IP est: 192.168.1.10
Le CIDR devrait être: 192.168.1.0/24
```

---

### Erreur "Permission denied"

**Cause**: L'application n'a pas les permissions réseau

**Solution Windows**:
1. Fermez l'application
2. Clic droit sur `main.py` ou l'EXE
3. Sélectionnez "Exécuter en tant qu'administrateur"

**Solution Linux/Mac**:
```bash
sudo python3 main.py
```

---

### Le scan est très lent

**Cause probable**: Réseau trop large ou "Inclure ping" activé

**Solution**:
1. Désactivez "Inclure ping (slow)" si activé
2. Utilisez un CIDR plus petit:
   - Au lieu de `10.0.0.0/8` (16M IPs)
   - Utilisez `10.0.1.0/24` (256 IPs)
3. Augmentez le timeout à 3-4 secondes

---

### L'interface se fige pendant le scan

**Note**: C'est normal pour Scapy. Le UI ne devrait pas se figer si le threading fonctionne.

**Solution**:
1. Patientez (le scan prend du temps)
2. Regardez les logs pour voir la progression
3. Si vraiment bloqué, fermez et relancez

---

### Fichier OUI.txt ne télécharge pas

**Cause**: Problème de connexion Internet

**Solution**:
1. Vérifiez votre connexion Internet
2. Relancez l'application (retry automatique)
3. Sans OUI.txt, le scan fonctionne mais sans identification de marques

---

## Compilation en EXE

### Méthode 1: Via le script

**Windows**:
```batch
install_and_run.bat
# Choisissez option 3
```

**Linux/macOS**:
```bash
./install_and_run.sh
# Choisissez option 3
```

### Méthode 2: Manuel

**Installation de PyInstaller**:
```bash
pip install pyinstaller
```

**Création d'un EXE unique**:
```batch
pyinstaller --noconsole --onefile --name "WIFI_Manager" main.py
```

**Résultat**: `dist\WIFI_Manager.exe`

**Avec icône personnalisée**:
```bash
# Créez une image 256x256 et convertissez-la en .ico
# Puis:
pyinstaller --noconsole --onefile --icon=assets/icons/app.ico --name "WIFI_Manager" main.py
```

### Distribution

Pour distribuer l'application:
1. Compilez en EXE
2. Zipiez le dossier `dist/`
3. Fournissez les instructions: "Exécutez en tant qu'Administrateur"

---

## Conseils d'utilisation

### ✓ Bonnes pratiques

- **Toujours exécuter en Admin/root** (nécessaire pour ARP)
- **Utiliser un timeout de 2-3 secondes** (bon compromis)
- **Exporter les résultats** pour archivage
- **Désactiver ping** si vous avez juste besoin des IPs/MACs

### ✗ À éviter

- Scanner des réseaux de classe A ou B complets (trop lent)
- Laisser le ping activé si ce n'est pas utile
- Modifier les fichiers sources sans backup
- Partager les données de scan sans consentement

---

## Exemples complets

### Exemple 1: Audit réseau rapide

```bash
# Setup
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
sudo python3 main.py       # ou python main.py en tant qu'Admin

# Dans l'UI:
# 1. Gardez le CIDR par défaut
# 2. Timeout = 2 secondes
# 3. Ping = OFF
# 4. Cliquez Scan
# 5. Attendez 10-20 secondes
# 6. Exportez en CSV
```

### Exemple 2: Diagnostic approfondi

```bash
# Dans l'UI:
# 1. CIDR = 192.168.1.0/24
# 2. Timeout = 3 secondes
# 3. Ping = ON (pour latences)
# 4. Cliquez Scan
# 5. Attendez 45-60 secondes
# 6. Analysez les latences
# 7. Exportez pour rapport
```

### Exemple 3: Scan continu (script)

```python
#!/usr/bin/env python3
import time
import sys
sys.path.insert(0, '.')
from scanner import ARPScanner, CSVExporter

scanner = ARPScanner()

for i in range(10):  # 10 scans
    print(f"\n[{i+1}/10] Scan en cours...")
    results = scanner.scan("192.168.1.0/24")
    CSVExporter.export(results, f"scan_{i+1}.csv")
    print(f"✓ {len(results)} appareils trouvés")
    time.sleep(60)  # Attendre 1 minute avant le prochain

print("\n✓ 10 scans complétés!")
```

---

## Support

Pour obtenir de l'aide:
1. Consultez le README.md
2. Vérifiez la section Résolution de problèmes
3. Exécutez les tests: `python test_units.py`

Amusez-vous! 🚀
