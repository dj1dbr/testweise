# Rohstoff Trader - Lokale Installation auf Mac

## Warum lokal auf dem Mac?

✅ **Bitpanda funktioniert lokal!** (In der Cloud blockiert das Netzwerk Bitpanda)
✅ **Volle Kontrolle** über die Anwendung
✅ **Schneller** (keine Cloud-Latenz)
✅ **Debugging einfacher**

---

## Voraussetzungen

Ihr Mac benötigt:
- **Python 3.10+** (installiert via Homebrew)
- **Node.js 18+** und **Yarn** (für Frontend)
- **MongoDB** (lokal oder MongoDB Atlas)
- **Git** (zum Klonen des Projekts)

---

## Schritt 1: System-Abhängigkeiten installieren

### Für alle Macs (Intel & Apple Silicon)

```bash
# Homebrew (falls noch nicht installiert)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# System-Bibliotheken für Python-Pakete
brew install openssl rust postgresql libjpeg libpng

# Python 3.11
brew install python@3.11

# Node.js und Yarn
brew install node
npm install -g yarn

# MongoDB (lokal)
brew tap mongodb/brew
brew install mongodb-community

# MongoDB starten
brew services start mongodb-community
```

### Für Apple Silicon (M1/M2/M3/M4) - Zusätzliche Schritte

```bash
# Rosetta 2 installieren (falls noch nicht vorhanden)
softwareupdate --install-rosetta

# XCode Command Line Tools
xcode-select --install
```

---

## Schritt 2: Projekt-Dateien kopieren

### Option A: Von dieser Cloud-Instanz herunterladen

1. **Projekt als ZIP herunterladen:**
   - Nutzen Sie die "Save to Github" Funktion in Emergent
   - Oder: Erstellen Sie ein ZIP der `/app` Ordner

2. **Auf Ihrem Mac entpacken:**
   ```bash
   cd ~/Desktop
   unzip rohstoff-trader.zip
   cd rohstoff-trader
   ```

### Option B: Von GitHub klonen (falls Sie es gepusht haben)

```bash
cd ~/Desktop
git clone https://github.com/IHR-USERNAME/rohstoff-trader.git
cd rohstoff-trader
```

---

## Schritt 3: Backend einrichten

```bash
cd backend

# Virtual Environment erstellen
python3.11 -m venv venv
source venv/bin/activate

# pip und setuptools aktualisieren
pip install --upgrade pip setuptools wheel

# WICHTIG: Für Apple Silicon (M1/M2/M3/M4)
# Umgebungsvariablen für grpcio und cryptography setzen
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1

# Dependencies installieren
pip install -r requirements.txt

# Falls Fehler bei grpcio auftreten:
# pip install grpcio==1.75.1 --no-binary=grpcio

# Falls Fehler bei cryptography auftreten:
# pip install cryptography==46.0.2 --no-binary=cryptography

# .env Datei anpassen
nano .env
```

### Wichtig: .env für lokalen Mac anpassen

```bash
# MongoDB (lokal)
MONGO_URL=mongodb://localhost:27017
DB_NAME=rohstoff_trader

# MetaAPI (Ihre bestehenden Zugangsdaten)
METAAPI_ACCOUNT_ID=rohstoff-trader
METAAPI_TOKEN=IHR_TOKEN_HIER

# Bitpanda (Ihre bestehenden Zugangsdaten)
BITPANDA_API_KEY=440f37c27ca395a9fbb1305dbf80c5ee541450f4b420a2d68bfa44dcb08f90d021d395b824b2806947299c69e71c17ebeb21e0b4572226d59f2afcab718a6fa5
BITPANDA_EMAIL=ihre-email@beispiel.de

# OpenAI (optional, für AI-Analyse)
OPENAI_API_KEY=IHR_OPENAI_KEY  # oder nutzen Sie Emergent LLM Key
```

### Backend starten

```bash
# Im backend/ Ordner mit aktiviertem venv
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend läuft jetzt auf: `http://localhost:8001`

---

## Schritt 4: Frontend einrichten

**Neues Terminal-Fenster öffnen:**

```bash
cd ~/Desktop/rohstoff-trader/frontend

# Dependencies installieren
yarn install

# .env Datei anpassen
nano .env
```

### Frontend .env für lokalen Mac:

```bash
# Backend URL - LOKAL!
REACT_APP_BACKEND_URL=http://localhost:8001
```

### Frontend starten

```bash
# Im frontend/ Ordner
yarn start
```

Frontend läuft jetzt auf: `http://localhost:3000`

---

## Schritt 5: Bitpanda testen

1. **Öffnen Sie die App:** `http://localhost:3000`
2. **Gehen Sie zu Settings**
3. **Wählen Sie Modus: "🟢 Bitpanda"**
4. **Ihr Bitpanda API-Key sollte automatisch geladen werden**
5. **Klicken Sie "Speichern"**

### Bitpanda-Verbindung testen (Terminal):

```bash
# Test: Bitpanda Account Info
curl http://localhost:8001/api/bitpanda/account

# Test: Bitpanda Balance
curl http://localhost:8001/api/bitpanda/balances
```

Wenn Sie eine Antwort mit Ihrem Account-Balance sehen: **✅ Bitpanda funktioniert!**

---

## Unterschiede Cloud vs. Lokal

| Feature | Cloud (Emergent) | Lokal (Mac) |
|---------|------------------|-------------|
| **MT5 Trading** | ✅ Funktioniert | ✅ Funktioniert |
| **Bitpanda Trading** | ❌ Netzwerk blockiert | ✅ Funktioniert |
| **Preise & Charts** | ✅ Funktioniert | ✅ Funktioniert |
| **Datenbank** | ✅ Zentral | ⚠️ Nur lokal |
| **Zugriff von überall** | ✅ Ja | ❌ Nur am Mac |
| **Automatisch neustart** | ✅ Ja | ❌ Manuell |

---

## Empfohlener Workflow

**Entwicklung & Testing:** Lokal auf dem Mac (Bitpanda testen)
**Produktion:** Cloud (24/7 Trading, von überall zugreifbar)

---

## Troubleshooting

### Problem: MongoDB läuft nicht
```bash
# Status prüfen
brew services list

# Neu starten
brew services restart mongodb-community
```

### Problem: Port 8001 bereits belegt
```bash
# Anderen Port verwenden
python -m uvicorn server:app --host 0.0.0.0 --port 8002 --reload

# Dann in frontend/.env anpassen:
REACT_APP_BACKEND_URL=http://localhost:8002
```

### Problem: Dependencies fehlen
```bash
# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
yarn install
```

### Problem: Bitpanda API nicht erreichbar
```bash
# Testen Sie manuell:
curl https://api.exchange.bitpanda.com/public/v1/time

# Wenn das funktioniert, ist Bitpanda erreichbar
```

### Problem: grpcio Installation schlägt fehl (Apple Silicon)
```bash
# Lösung 1: Mit Umgebungsvariablen
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
pip install grpcio==1.75.1

# Lösung 2: Von Quelle kompilieren
pip install grpcio==1.75.1 --no-binary=grpcio

# Lösung 3: Ältere Version verwenden
pip install grpcio==1.54.0
```

### Problem: cryptography Installation schlägt fehl
```bash
# Sicherstellen dass OpenSSL und Rust installiert sind
brew install openssl rust

# Mit spezifischen Pfaden installieren
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"
pip install cryptography==46.0.2

# Oder ohne Binary:
pip install cryptography==46.0.2 --no-binary=cryptography
```

### Problem: pillow Installation schlägt fehl
```bash
# Bild-Bibliotheken installieren
brew install libjpeg libpng

# Dann pillow installieren
pip install pillow==12.0.0
```

### Problem: "xcrun: error: invalid active developer path"
```bash
# XCode Command Line Tools installieren
xcode-select --install

# Nach Installation nochmal versuchen:
pip install -r requirements.txt
```

### Problem: numpy/pandas Fehler auf Apple Silicon
```bash
# Sicherstellen dass Sie native ARM-Version von Python verwenden
python3 -c "import platform; print(platform.machine())"
# Sollte "arm64" ausgeben auf Apple Silicon

# Falls "x86_64": Python neu installieren
brew reinstall python@3.11
```

### Problem: "command 'gcc' failed"
```bash
# Compiler-Tools installieren
xcode-select --install

# Falls schon installiert, neu setzen:
sudo xcode-select --reset
```

---

## Wichtige Befehle

### Backend stoppen/starten
```bash
# Stoppen: CTRL+C im Terminal

# Starten:
cd backend
source venv/bin/activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend stoppen/starten
```bash
# Stoppen: CTRL+C im Terminal

# Starten:
cd frontend
yarn start
```

### Logs anschauen
```bash
# Backend-Logs erscheinen direkt im Terminal

# Frontend-Logs im Browser:
# Rechtsklick -> Untersuchen -> Console
```

---

## Bitpanda Trading aktivieren

1. **Settings öffnen** in der App
2. **Modus: "🟢 Bitpanda"** wählen
3. **Bitpanda API-Key** wird automatisch aus .env geladen
4. **"Speichern"** klicken
5. **Balance sollte oben angezeigt werden** (wenn API-Key gültig ist)

### Verfügbare Rohstoffe auf Bitpanda:

Bitpanda bietet hauptsächlich **Kryptowährungen** und einige **Edelmetalle**:
- ✅ Bitcoin (BTC)
- ✅ Ethereum (ETH)
- ✅ Gold (paxos Gold Token)
- ✅ Silber (noch in Entwicklung)

**Wichtig:** Bitpanda unterstützt KEINE Rohstoff-Futures (kein WTI, Weizen, etc.)

---

## Zusammenfassung

✅ **Ja, Bitpanda funktioniert auf Ihrem Mac!**
✅ Installation dauert ca. **15-20 Minuten**
✅ Alle Anleitungen und Scripts sind bereits vorbereitet
✅ MT5 **und** Bitpanda gleichzeitig nutzbar

**Nächster Schritt:** Projekt-Dateien auf Ihren Mac kopieren und Anleitung folgen! 🚀
