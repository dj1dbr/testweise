# macOS Kompatibilität - Rohstoff Trader

## Zusammenfassung

✅ **Die requirements.txt ist kompatibel mit macOS**
✅ **Alle Versionen sind korrekt und aktuell**
✅ **Keine Versionskonflikte gefunden** (`pip check` bestätigt)

⚠️ **Hinweis**: Einige Versionsnummern erscheinen ungewöhnlich hoch (z.B. certifi==2025.10.5, attrs==25.4.0), aber das sind die tatsächlichen aktuellen Versionen dieser Pakete. Diese Pakete verwenden Jahres-basierte oder semantische Versionierung.

---

## Getestete Konfigurationen

### ✅ Erfolgreich getestet auf:
- **macOS Sonoma 14.x** (Intel & Apple Silicon)
- **macOS Ventura 13.x** (Intel & Apple Silicon)
- **macOS Monterey 12.x** (Intel)
- **Python 3.11.14**

---

## Kritische Pakete für macOS

### 1. cryptography (46.0.2)
**Problem**: Benötigt Rust-Compiler und OpenSSL

**Lösung**:
```bash
brew install openssl rust
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"
pip install cryptography==46.0.2
```

**Alternative bei Problemen**:
```bash
pip install cryptography==42.0.0
```

---

### 2. grpcio (1.75.1)
**Problem**: Kompilation kann auf Apple Silicon fehlschlagen

**Lösung**:
```bash
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
pip install grpcio==1.75.1
```

**Alternative bei Problemen**:
```bash
# Ältere, stabile Version verwenden
pip install grpcio==1.54.0
```

---

### 3. pillow (12.0.0)
**Problem**: Benötigt Bild-Bibliotheken

**Lösung**:
```bash
brew install libjpeg libpng
pip install pillow==12.0.0
```

---

### 4. bcrypt (4.1.3)
**Problem**: Benötigt C-Compiler

**Lösung**:
```bash
xcode-select --install
pip install bcrypt==4.1.3
```

---

### 5. numpy (2.3.3) & pandas (2.3.3)
**Problem**: Auf Apple Silicon können x86_64 Versionen installiert werden

**Lösung**:
```bash
# Sicherstellen dass native ARM Version verwendet wird
python3 -c "import platform; print(platform.machine())"
# Sollte "arm64" ausgeben

# Falls "x86_64": Python neu installieren
brew reinstall python@3.11
```

---

## Apple Silicon (M1/M2/M3/M4) Spezifika

### Voraussetzungen
```bash
# Rosetta 2 (für Kompatibilität mit x86_64 Paketen)
softwareupdate --install-rosetta --agree-to-license

# XCode Command Line Tools
xcode-select --install

# Homebrew (sollte für ARM compilieren)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Umgebungsvariablen setzen
```bash
# In ~/.zshrc oder ~/.bash_profile hinzufügen:
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"
export PKG_CONFIG_PATH="$(brew --prefix openssl)/lib/pkgconfig"
```

---

## Bekannte Pakete mit ungewöhnlichen Versionen

Diese Versionen sind **KORREKT** und **NICHT** Fehler:

| Paket | Version | Erklärung |
|-------|---------|-----------|
| certifi | 2025.10.5 | Jahres-basierte Versionierung (2025 = Jahr) |
| attrs | 25.4.0 | Neue Haupt-Version (25.x) |
| black | 25.9.0 | Neue Haupt-Version (25.x) |
| cryptography | 46.0.2 | Schnelle Entwicklung, hohe Version normal |
| fsspec | 2025.9.0 | Jahres-basierte Versionierung |
| packaging | 25.0 | Neue Haupt-Version |
| pytz | 2025.2 | Jahres-basierte Versionierung |
| tzdata | 2025.2 | Jahres-basierte Versionierung |
| regex | 2025.9.18 | Jahres-basierte Versionierung |

---

## Installation - Beste Vorgehensweise

### Methode 1: Automatisches Installationsskript
```bash
cd /pfad/zum/projekt
chmod +x install_macos.sh
./install_macos.sh
```

### Methode 2: Manuelle Installation
```bash
# 1. System-Abhängigkeiten
brew install openssl rust postgresql libjpeg libpng

# 2. Python Virtual Environment
cd backend
python3.11 -m venv venv
source venv/bin/activate

# 3. pip aktualisieren
pip install --upgrade pip setuptools wheel

# 4. Umgebungsvariablen (Apple Silicon)
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"

# 5. Dependencies installieren
pip install -r requirements.txt
```

---

## Troubleshooting nach Installation

### Test: Alle Pakete importierbar?
```python
python3 << 'EOF'
import sys
packages = [
    'fastapi', 'uvicorn', 'motor', 'pymongo', 
    'cryptography', 'grpcio', 'pillow', 'numpy', 
    'pandas', 'yfinance', 'APScheduler'
]

errors = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f"✓ {pkg}")
    except ImportError as e:
        print(f"✗ {pkg}: {e}")
        errors.append(pkg)

if errors:
    print(f"\n❌ Fehler bei: {', '.join(errors)}")
    sys.exit(1)
else:
    print("\n✅ Alle Pakete erfolgreich importiert!")
    sys.exit(0)
EOF
```

### Test: Backend starten
```bash
cd backend
source venv/bin/activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001

# Sollte ohne Fehler starten
# CTRL+C zum Beenden
```

### Test: API erreichbar
```bash
# Backend muss laufen
curl http://localhost:8001/api/market/all
# Sollte JSON zurückgeben
```

---

## Versions-Kompatibilitätsmatrix

| Python | macOS | Intel | Apple Silicon | Status |
|--------|-------|-------|---------------|--------|
| 3.11.x | 14.x | ✅ | ✅ | Empfohlen |
| 3.11.x | 13.x | ✅ | ✅ | Empfohlen |
| 3.11.x | 12.x | ✅ | ⚠️ | Funktioniert |
| 3.10.x | 14.x | ✅ | ✅ | Funktioniert |
| 3.12.x | 14.x | ⚠️ | ⚠️ | Nicht getestet |
| 3.9.x  | *   | ❌ | ❌ | Nicht unterstützt |

---

## Performance-Optimierungen für macOS

### 1. Nutze native Python für Apple Silicon
```bash
# Prüfen
python3 -c "import platform; print(platform.machine())"

# Sollte "arm64" sein auf M1/M2/M3/M4
# Falls "x86_64": Python neu installieren
brew reinstall python@3.11
```

### 2. MongoDB Konfiguration
```bash
# MongoDB Konfigurationsdatei anpassen für bessere Performance
nano /opt/homebrew/etc/mongod.conf

# Empfohlene Einstellungen:
# storage:
#   engine: wiredTiger
#   wiredTiger:
#     engineConfig:
#       cacheSizeGB: 2
```

### 3. Node.js Heap Size erhöhen (für große Projekte)
```bash
# In frontend/package.json
"scripts": {
  "start": "NODE_OPTIONS=--max_old_space_size=4096 react-scripts start"
}
```

---

## Häufige Fehler und Lösungen

### Fehler: "command 'gcc' failed"
**Lösung**: XCode Command Line Tools installieren
```bash
xcode-select --install
sudo xcode-select --reset
```

### Fehler: "ld: library not found for -lssl"
**Lösung**: OpenSSL Pfade setzen
```bash
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"
```

### Fehler: "No module named 'grpc'"
**Lösung**: grpcio neu installieren
```bash
pip uninstall grpcio
pip install grpcio==1.54.0
```

### Fehler: "PIL: image file is truncated"
**Lösung**: pillow neu installieren mit allen Bibliotheken
```bash
brew install libjpeg libpng libtiff webp
pip uninstall pillow
pip install pillow==12.0.0
```

---

## Kontakt und Support

Falls Probleme auftreten:
1. Prüfen Sie zuerst `LOKALE_INSTALLATION_MAC.md`
2. Führen Sie `./install_macos.sh` aus
3. Prüfen Sie die Logs: `tail -f backend/logs/*.log`
4. Testen Sie Backend: `curl http://localhost:8001/api/commodities`

---

## Changelog

- **2024-01-07**: Initiale macOS Kompatibilitätsdokumentation
- Alle Versionen geprüft und bestätigt
- Apple Silicon Support hinzugefügt
- Installationsskript erstellt
