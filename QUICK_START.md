# 🚀 QUICK START - WIFI Manager

## 30 secondes pour démarrer

### Windows

```batch
# 1. Ouvrez PowerShell en tant qu'Administrateur
# 2. Naviguez vers le dossier
cd C:\Users\Hp\Desktop\WIFI_Manager

# 3. Lancez le script
install_and_run.bat

# 4. Sélectionnez option 1 pour lancer l'app
```

### Linux / macOS

```bash
# 1. Terminal
cd ~/WIFI_Manager

# 2. Rendez le script exécutable
chmod +x install_and_run.sh

# 3. Lancez
./install_and_run.sh

# 4. Sélectionnez option 1
```

## Ou manuellement (plus rapide)

### Windows (Administrateur)

```batch
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo python3 main.py
```

## Utilisation rapide

1. **Entrez le CIDR** (ex: `192.168.1.0/24`)
2. **Cliquez "Scan"**
3. **Attendez 15-30 secondes**
4. **Voyez les appareils!**

## Fichiers importants

| Fichier | Utilité |
|---------|---------|
| `main.py` | 🎬 Lancer l'app |
| `requirements.txt` | 📦 Dépendances |
| `README.md` | 📖 Documentation |
| `USAGE.md` | 💡 Cas d'usage |

## Premiers problèmes?

### "Permission denied"
→ Relancez en Admin (Windows) ou avec `sudo` (Linux/Mac)

### "No module named 'scapy'"
→ Lancez: `pip install -r requirements.txt`

### Aucun appareil trouvé
→ Cliquez "Auto-détect" pour le bon CIDR

## Compilation en EXE (optionnel)

```batch
pip install pyinstaller
pyinstaller --noconsole --onefile --name "WIFI_Manager" main.py
# Résultat: dist/WIFI_Manager.exe (exécutez en Admin)
```

---

C'est tout! L'app est prête. Amusez-vous! 🎉
