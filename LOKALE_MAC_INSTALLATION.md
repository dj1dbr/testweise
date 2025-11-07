# 🍎 Rohstoff Trader - Lokale Installation für Mac

## Voraussetzungen

### 1. Python 3.11+ installieren (Python 3.14 kompatibel)

```bash
# Prüfen Sie Ihre Python-Version
python3 --version

# Falls nicht installiert, mit Homebrew installieren:
brew install python@3.11
```

**Hinweis**: Die App funktioniert mit Python 3.11, 3.12, 3.13 und 3.14.

### 2. Node.js und Yarn installieren

```bash
# Node.js installieren
brew install node

# Yarn installieren
npm install -g yarn

# Versionen prüfen
node --version  # sollte >= 16.0.0 sein
yarn --version  # sollte >= 1.22.0 sein
```

### 3. MongoDB installieren

```bash
# MongoDB Community Edition installieren
brew tap mongodb/brew
brew install mongodb-community

# MongoDB als Service starten
brew services start mongodb-community

# Status prüfen
brew services list | grep mongodb
```

## Installation Schritt für Schritt

### Schritt 1: Repository klonen

```bash
# In Ihr gewünschtes Verzeichnis wechseln
cd ~/Projects

# Repository herunterladen (oder von GitHub klonen)
# Falls Sie ZIP haben:
unzip rohstoff-trader.zip
cd rohstoff-trader

# Falls von GitHub:
git clone <repository-url>
cd rohstoff-trader
```

### Schritt 2: Backend einrichten

```bash
# In Backend-Verzeichnis wechseln
cd backend

# Virtuelle Python-Umgebung erstellen
python3 -m venv venv

# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt

# .env-Datei erstellen (falls nicht vorhanden)
cp .env.example .env  # oder manuell erstellen
```

### Schritt 3: .env-Datei konfigurieren

Öffnen Sie `backend/.env` mit einem Texteditor:

```bash
nano backend/.env
```

Fügen Sie folgende Konfiguration ein:

```bash
# MongoDB (lokal)
MONGO_URL="mongodb://localhost:27017"
DB_NAME="rohstoff_trader_db"
CORS_ORIGINS="*"

# MT5 Libertex (MetaAPI)
METAAPI_ACCOUNT_ID=multiplatformtrader
METAAPI_ICMARKETS_ACCOUNT_ID=multiplatformtrader
METAAPI_TOKEN=<IHR_METAAPI_TOKEN>

# Bitpanda (auf Mac verfügbar!)
BITPANDA_API_KEY=<IHR_BITPANDA_API_KEY>

# Optional: AI-APIs
OPENAI_API_KEY=<IHR_OPENAI_KEY>
GEMINI_API_KEY=<IHR_GEMINI_KEY>
ANTHROPIC_API_KEY=<IHR_ANTHROPIC_KEY>

# Emergent LLM Key (falls vorhanden)
EMERGENT_LLM_KEY=<IHR_EMERGENT_KEY>
```

**Speichern**: `Ctrl+O`, dann `Enter`, dann `Ctrl+X`

### Schritt 4: Frontend einrichten

```bash
# In Frontend-Verzeichnis wechseln (aus backend raus)
cd ../frontend

# Dependencies installieren
yarn install

# .env-Datei erstellen
nano .env
```

Fügen Sie folgende Konfiguration ein:

```bash
# Backend URL (lokal)
REACT_APP_BACKEND_URL=http://localhost:8001

# WebSocket-Konfiguration
WDS_SOCKET_HOST=localhost
WDS_SOCKET_PORT=3000
WDS_SOCKET_PATH=/ws

# Weitere Config
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
```

**Speichern**: `Ctrl+O`, dann `Enter`, dann `Ctrl+X`

### Schritt 5: Anwendung starten

#### Terminal 1 - Backend starten:

```bash
cd backend
source venv/bin/activate  # Falls nicht schon aktiv
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Erwartete Ausgabe**:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

#### Terminal 2 - Frontend starten:

```bash
cd frontend
yarn start
```

**Erwartete Ausgabe**:
```
Compiled successfully!
You can now view the app in the browser.
  Local:            http://localhost:3000
```

### Schritt 6: Anwendung öffnen

Öffnen Sie Ihren Browser und gehen Sie zu:
```
http://localhost:3000
```

## Troubleshooting

### Problem: MongoDB startet nicht

```bash
# MongoDB-Logs prüfen
tail -f /usr/local/var/log/mongodb/mongo.log

# MongoDB manuell starten
mongod --config /usr/local/etc/mongod.conf

# Alternative: Docker verwenden
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Problem: Port 8001 oder 3000 bereits belegt

```bash
# Prozess auf Port finden und beenden
lsof -ti:8001 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### Problem: Python-Module fehlen

```bash
# Virtuelle Umgebung reaktivieren
cd backend
source venv/bin/activate

# Alle Dependencies neu installieren
pip install --force-reinstall -r requirements.txt
```

### Problem: Yarn-Installation schlägt fehl

```bash
# Cache löschen und neu versuchen
cd frontend
yarn cache clean
rm -rf node_modules package-lock.json yarn.lock
yarn install
```

### Problem: Bitpanda funktioniert nicht

**Auf Mac sollte Bitpanda funktionieren!** Falls nicht:

```bash
# Netzwerk-Test
curl -I https://api.exchange.bitpanda.com/public/v1/time

# Falls Fehler: Firewall-Einstellungen prüfen
# System Preferences > Security & Privacy > Firewall
```

## Python-Versionskompatibilität

### Unterstützte Versionen:
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13
- ✅ Python 3.14

### Zwischen Versionen wechseln:

```bash
# Verfügbare Python-Versionen anzeigen
ls -la /usr/local/bin/python3*

# Spezifische Version verwenden
/usr/local/bin/python3.14 -m venv venv

# Oder mit pyenv (empfohlen)
brew install pyenv
pyenv install 3.14.0
pyenv local 3.14.0
python3 -m venv venv
```

### Dependencies-Kompatibilität prüfen:

```bash
# Alle installierten Pakete anzeigen
pip list

# Kompatibilitätsprobleme prüfen
pip check

# Falls Probleme: Pakete aktualisieren
pip install --upgrade -r requirements.txt
```

## Zusätzliche Features (Optional)

### 1. Auto-Restart bei Code-Änderungen

**Backend** nutzt bereits `--reload` Flag.

**Frontend** hat Hot-Reload automatisch aktiv.

### 2. Logs anzeigen

```bash
# Backend-Logs in Echtzeit
cd backend
tail -f logs/app.log  # falls Log-Datei konfiguriert

# Oder direkt im Terminal sichtbar durch --reload
```

### 3. Datenbank-Backup erstellen

```bash
# MongoDB-Dump erstellen
mongodump --db rohstoff_trader_db --out ~/backups/mongodb-backup

# Backup wiederherstellen
mongorestore --db rohstoff_trader_db ~/backups/mongodb-backup/rohstoff_trader_db
```

### 4. Produktions-Build erstellen

```bash
# Frontend Production-Build
cd frontend
yarn build

# Build im Browser testen
npx serve -s build -p 3000
```

## Häufige Fragen

### Kann ich mehrere Instanzen gleichzeitig laufen lassen?

Ja, aber Sie müssen unterschiedliche Ports verwenden:

```bash
# Backend auf Port 8002
uvicorn server:app --reload --port 8002

# Frontend auf Port 3001
PORT=3001 yarn start
```

### Muss ich MongoDB immer manuell starten?

Nein, als Service läuft es automatisch:

```bash
# Als Service konfigurieren (einmalig)
brew services start mongodb-community
```

### Wie aktualisiere ich die App?

```bash
# Code aktualisieren (falls Git)
git pull origin main

# Backend-Dependencies aktualisieren
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend-Dependencies aktualisieren
cd ../frontend
yarn install

# Server neu starten
```

## Performance-Tipps

### 1. MongoDB-Indizes erstellen

```javascript
// In MongoDB Shell
use rohstoff_trader_db
db.trades.createIndex({ "timestamp": -1 })
db.market_data.createIndex({ "commodity": 1, "timestamp": -1 })
```

### 2. Python-Optimierung

```bash
# Python mit Optimierungen starten
python -O -m uvicorn server:app --reload
```

### 3. Node.js Memory erhöhen (falls nötig)

```bash
# Frontend mit mehr Memory starten
NODE_OPTIONS=--max_old_space_size=4096 yarn start
```

## Deinstallation

```bash
# MongoDB-Service stoppen
brew services stop mongodb-community

# MongoDB deinstallieren (optional)
brew uninstall mongodb-community

# Projektordner löschen
rm -rf ~/Projects/rohstoff-trader

# Python venv löschen
# (wird mit Projektordner gelöscht)

# Globale Tools behalten (Node, Yarn, Python)
```

## Support

Bei Problemen:

1. **Logs prüfen**: Backend und Frontend Terminal
2. **MongoDB prüfen**: `brew services list`
3. **Ports prüfen**: `lsof -i :8001` und `lsof -i :3000`
4. **Dependencies prüfen**: `pip check` und `yarn check`

## Checkliste

- [ ] Python 3.11+ installiert
- [ ] Node.js und Yarn installiert
- [ ] MongoDB läuft (als Service)
- [ ] Backend-Dependencies installiert (`pip install -r requirements.txt`)
- [ ] Frontend-Dependencies installiert (`yarn install`)
- [ ] `.env`-Dateien konfiguriert (Backend und Frontend)
- [ ] Backend läuft auf Port 8001
- [ ] Frontend läuft auf Port 3000
- [ ] Browser öffnet `http://localhost:3000`
- [ ] ✅ **Bitpanda funktioniert auf Mac!**

---

**Version**: 2.0  
**Letzte Aktualisierung**: November 2025  
**Python-Kompatibilität**: 3.11 - 3.14
