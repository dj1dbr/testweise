# WTI Smart Trader - Lokale Installation für macOS

Eine KI-gestützte Trading-Anwendung für WTI Crude Oil mit automatischer technischer Analyse und verschiedenen AI-Provider-Optionen.

## 📋 Inhaltsverzeichnis

- [Funktionen](#funktionen)
- [Systemanforderungen](#systemanforderungen)
- [Installation](#installation)
  - [1. MongoDB Installation](#1-mongodb-installation)
  - [2. Python Setup](#2-python-setup)
  - [3. Node.js & Yarn Setup](#3-nodejs--yarn-setup)
  - [4. Ollama Installation (Optional)](#4-ollama-installation-optional)
  - [5. Abhängigkeiten installieren](#5-abhängigkeiten-installieren)
- [Konfiguration](#konfiguration)
- [App starten](#app-starten)
- [AI-Provider Konfiguration](#ai-provider-konfiguration)
- [Verwendung](#verwendung)
- [Troubleshooting](#troubleshooting)

## ✨ Funktionen

- **Live WTI Ölpreis-Tracking** über Yahoo Finance API
- **Technische Indikatoren**: RSI, MACD, SMA, EMA
- **Multiple AI-Provider**:
  - Emergent LLM Key (Universal)
  - OpenAI GPT-5/4
  - Google Gemini
  - Anthropic Claude
  - **Ollama (Lokal auf Ihrem Mac)**
- **Automatisches Trading** mit AI-Signalen
- **Paper Trading** & MetaTrader 5 Integration
- **Echtzeit-Charts** und Trading-Historie

## 💻 Systemanforderungen

- **macOS** 10.15 (Catalina) oder höher
- **Python** 3.9 oder höher
- **Node.js** 16.x oder höher
- **Yarn** Package Manager
- **MongoDB** Community Edition 5.0+
- **Ollama** (Optional, für lokale AI)
- Mindestens 4 GB RAM (8 GB empfohlen für Ollama)
- 5 GB freier Festplattenspeicher

## 🚀 Installation

### 1. MongoDB Installation

#### Option A: Mit Homebrew (Empfohlen)

```bash
# Homebrew installieren (falls noch nicht vorhanden)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# MongoDB installieren
brew tap mongodb/brew
brew install mongodb-community@7.0

# MongoDB als Service starten (startet automatisch bei Systemstart)
brew services start mongodb-community@7.0

# MongoDB Status prüfen
brew services list | grep mongodb
```

#### Option B: Manueller Download

1. Besuchen Sie: https://www.mongodb.com/try/download/community
2. Wählen Sie:
   - Version: 7.0.x
   - Platform: macOS
   - Package: TGZ
3. Laden Sie herunter und entpacken Sie das Archiv
4. Verschieben Sie es nach `/usr/local/mongodb`
5. Fügen Sie zu `~/.zshrc` oder `~/.bash_profile` hinzu:
   ```bash
   export PATH="/usr/local/mongodb/bin:$PATH"
   ```
6. Starten Sie MongoDB manuell:
   ```bash
   mongod --dbpath ~/data/db
   ```

#### MongoDB Verbindung testen

```bash
# MongoDB Shell öffnen
mongosh

# Sollte erfolgreich verbinden und zeigen: "test>"
# Mit "exit" wieder verlassen
```

### 2. Python Setup

```bash
# Python Version prüfen (sollte 3.9+ sein)
python3 --version

# Falls Python nicht installiert ist:
brew install python@3.11

# Virtuelle Umgebung erstellen (Optional, aber empfohlen)
cd /pfad/zum/trader
python3 -m venv venv

# Virtuelle Umgebung aktivieren
source venv/bin/activate  # Für bash/zsh
# oder
. venv/bin/activate.fish  # Für fish shell
```

### 3. Node.js & Yarn Setup

```bash
# Node.js installieren
brew install node

# Node.js Version prüfen (sollte 16.x+ sein)
node --version

# Yarn global installieren
npm install -g yarn

# Yarn Version prüfen
yarn --version
```

### 4. Ollama Installation (Optional)

Ollama ermöglicht lokale AI-Modelle auf Ihrem Mac **ohne externe API-Kosten**.

```bash
# Ollama herunterladen und installieren
# Besuchen Sie: https://ollama.ai/download
# Oder direkt mit Homebrew:
brew install ollama

# Ollama Server starten (läuft im Hintergrund)
ollama serve &

# Empfohlene Modelle für Trading herunterladen
ollama pull llama2        # Allzweck-Modell (3.8 GB)
ollama pull mistral       # Schneller und präzise (4.1 GB)
ollama pull llama3        # Neuestes Meta Modell (4.7 GB)

# Verfügbare Modelle anzeigen
ollama list

# Ollama Server Status prüfen
curl http://localhost:11434/api/tags
```

**Ollama Modell-Empfehlungen für Trading:**
- **llama2**: Gute Balance zwischen Geschwindigkeit und Qualität
- **mistral**: Schnell und präzise für Finanzdaten
- **llama3**: Beste Qualität, benötigt mehr RAM

### 5. Abhängigkeiten installieren

```bash
# Navigieren Sie zum Projektverzeichnis
cd /pfad/zum/trader

# Backend-Abhängigkeiten installieren
cd backend
pip install -r requirements.txt
cd ..

# Frontend-Abhängigkeiten installieren
cd frontend
yarn install
cd ..
```

## ⚙️ Konfiguration

### Backend Konfiguration (`backend/.env`)

```bash
# Datenbank (bereits konfiguriert)
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database

# CORS (für lokalen Zugriff)
CORS_ORIGINS=*

# Emergent LLM Key (Optional - für Cloud AI)
EMERGENT_LLM_KEY=sk-emergent-d644671BdC5A62417B

# MetaTrader 5 (Optional - für Live Trading)
MT5_LOGIN=52565616
MT5_PASSWORD=sBqsS94&1FTlkC
MT5_SERVER=ICMarketsEU-Demo
```

### Frontend Konfiguration (`frontend/.env`)

```bash
# Backend URL (localhost)
REACT_APP_BACKEND_URL=http://localhost:8001

# WebSocket Port (nicht ändern)
WDS_SOCKET_PORT=443

# Features (nicht ändern)
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
```

**⚠️ WICHTIG: Ändern Sie NICHT die URLs in den .env-Dateien, außer Sie wissen genau was Sie tun!**

## 🎬 App starten

### Methode 1: Mit Supervisor (Empfohlen - Automatisch)

Wenn Sie diese App auf einem Server mit Supervisor betreiben:

```bash
# Alle Services starten
sudo supervisorctl restart all

# Einzelne Services starten
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Status prüfen
sudo supervisorctl status

# Logs anzeigen
sudo supervisorctl tail -f backend
sudo supervisorctl tail -f frontend
```

### Methode 2: Manuell (Für lokale Entwicklung)

Öffnen Sie **3 separate Terminal-Fenster**:

#### Terminal 1: MongoDB

```bash
# Falls MongoDB nicht als Service läuft
mongod --dbpath ~/data/db
```

#### Terminal 2: Backend

```bash
cd /pfad/zum/trader/backend

# Virtuelle Umgebung aktivieren (falls verwendet)
source venv/bin/activate

# Backend starten
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend läuft auf: **http://localhost:8001**
API Dokumentation: **http://localhost:8001/docs**

#### Terminal 3: Frontend

```bash
cd /pfad/zum/trader/frontend

# Frontend starten
yarn start
```

Frontend öffnet automatisch im Browser: **http://localhost:3000**

#### Terminal 4: Ollama (Optional)

```bash
# Ollama Server starten (falls nicht bereits läuft)
ollama serve
```

Ollama API läuft auf: **http://localhost:11434**

## 🤖 AI-Provider Konfiguration

### In der App einrichten

1. Öffnen Sie die Trading-App im Browser: http://localhost:3000
2. Klicken Sie auf **"Einstellungen"** (⚙️)
3. Im Abschnitt **"KI-Analyse Einstellungen"**:

#### Option 1: Ollama (Lokal - KOSTENLOS)

- **KI Provider**: Wählen Sie "Ollama (Lokal)"
- **Ollama Server URL**: `http://localhost:11434` (Standard)
- **Ollama Model**: Wählen Sie ein installiertes Modell (z.B. `llama2`)
- **Vorteil**: Komplett lokal, keine API-Kosten, Datenschutz
- **Nachteil**: Benötigt mehr RAM, langsamere Inferenz

#### Option 2: Emergent LLM Key (Cloud - Universal)

- **KI Provider**: "Emergent LLM Key (Universal)"
- **KI Model**: `gpt-5` oder andere verfügbare Modelle
- **API Key**: Bereits in `.env` konfiguriert
- **Vorteil**: Schnell, hochwertige Ergebnisse
- **Nachteil**: Kostet Credits

#### Option 3: OpenAI (Cloud)

- **KI Provider**: "OpenAI API"
- **OpenAI API Key**: Ihr eigener Key von platform.openai.com
- **KI Model**: `gpt-4-turbo`, `gpt-4`, etc.

#### Option 4: Google Gemini (Cloud)

- **KI Provider**: "Google Gemini API"
- **Gemini API Key**: Ihr Key von aistudio.google.com
- **KI Model**: `gemini-1.5-pro`, `gemini-1.5-flash`

#### Option 5: Anthropic Claude (Cloud)

- **KI Provider**: "Anthropic Claude API"
- **Anthropic API Key**: Ihr Key von console.anthropic.com
- **KI Model**: `claude-3-5-sonnet-20241022`

### Empfohlene Konfiguration für lokalen Betrieb

```
✅ KI-Analyse verwenden: AN
✅ KI Provider: Ollama (Lokal)
✅ Ollama Server URL: http://localhost:11434
✅ Ollama Model: mistral (schnell) oder llama3 (qualitativ)
✅ Auto-Trading: AUS (für Tests)
✅ Trading Modus: Paper Trading
```

## 📖 Verwendung

### 1. Dashboard öffnen

Nach dem Start öffnet sich automatisch: http://localhost:3000

### 2. Live-Daten beobachten

- Der **Live-Ticker** aktualisiert Marktdaten alle 10 Sekunden
- Aktivieren/Deaktivieren mit dem **"Live-Ticker"** Schalter

### 3. Manuelle Trades

- **"Manuell KAUFEN"**: Öffnet eine BUY-Position zum aktuellen Preis
- **"Manuell VERKAUFEN"**: Schließt offene Positionen

### 4. Auto-Trading aktivieren

1. Gehen Sie zu **Einstellungen**
2. Aktivieren Sie **"Auto-Trading"**
3. Konfigurieren Sie:
   - Stop Loss % (Empfohlen: 2%)
   - Take Profit % (Empfohlen: 4%)
   - Max Trades pro Stunde (Empfohlen: 3)
4. Speichern Sie die Einstellungen

Die AI analysiert nun automatisch Marktdaten und führt Trades aus.

### 5. AI-Signale verstehen

- **BUY**: AI empfiehlt Kaufen (grün)
- **SELL**: AI empfiehlt Verkaufen (rot)
- **HOLD**: AI empfiehlt abwarten (grau)

Die AI analysiert:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Trendrichtung (SMA/EMA)
- Momentum

## 🔧 Troubleshooting

### Problem: MongoDB startet nicht

```bash
# Prüfen ob MongoDB bereits läuft
ps aux | grep mongod

# Port 27017 freigeben
lsof -ti:27017 | xargs kill -9

# MongoDB neu starten
brew services restart mongodb-community@7.0
```

### Problem: Backend startet nicht

```bash
# Prüfen ob Port 8001 frei ist
lsof -ti:8001 | xargs kill -9

# Python-Abhängigkeiten neu installieren
cd backend
pip install --upgrade -r requirements.txt

# Backend mit mehr Logs starten
uvicorn server:app --host 0.0.0.0 --port 8001 --reload --log-level debug
```

### Problem: Frontend startet nicht

```bash
# Prüfen ob Port 3000 frei ist
lsof -ti:3000 | xargs kill -9

# Node-Module neu installieren
cd frontend
rm -rf node_modules yarn.lock
yarn install

# Frontend neu starten
yarn start
```

### Problem: Ollama Verbindung fehlgeschlagen

```bash
# Prüfen ob Ollama läuft
ps aux | grep ollama

# Ollama neu starten
pkill ollama
ollama serve &

# Modell erneut herunterladen
ollama pull llama2

# Ollama API testen
curl http://localhost:11434/api/tags
```

### Problem: Keine Yahoo Finance Daten

```bash
# Internet-Verbindung prüfen
ping finance.yahoo.com

# Python yfinance neu installieren
pip install --upgrade yfinance

# API manuell testen
python3 -c "import yfinance as yf; print(yf.Ticker('CL=F').history(period='1d'))"
```

### Problem: AI gibt keine Empfehlungen

1. **Prüfen Sie die AI-Einstellungen**:
   - "KI-Analyse verwenden" aktiviert?
   - Richtiger Provider ausgewählt?
   - API Key (falls erforderlich) eingegeben?

2. **Für Ollama**:
   ```bash
   # Modell testen
   ollama run llama2 "Hello"
   
   # Sollte eine Antwort generieren
   ```

3. **Backend-Logs prüfen**:
   ```bash
   # Terminal mit Backend-Prozess öffnen
   # Suchen Sie nach Fehlermeldungen wie:
   # "Failed to initialize AI chat"
   # "Error getting AI analysis"
   ```

### Problem: "CORS Error" im Browser

Stellen Sie sicher, dass:
- Backend auf Port 8001 läuft
- `REACT_APP_BACKEND_URL=http://localhost:8001` in `frontend/.env`
- `CORS_ORIGINS=*` in `backend/.env`

### Problem: Hohe CPU/RAM-Nutzung

**Ollama verbraucht viel RAM** (4-8 GB je nach Modell):
- Verwenden Sie kleinere Modelle: `ollama pull phi` (2 GB)
- Schließen Sie andere Anwendungen
- Oder wechseln Sie zu Cloud-AI-Providern

## 📊 Architektur

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                  │
│                 http://localhost:3000               │
└────────────────────┬────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────┐
│              Backend (FastAPI)                      │
│             http://localhost:8001/api               │
└─────┬──────────────┬──────────────┬─────────────────┘
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ MongoDB  │  │  Yahoo   │  │  AI Provider │
│ :27017   │  │ Finance  │  │   (Ollama/   │
│          │  │   API    │  │  Cloud APIs) │
└──────────┘  └──────────┘  └──────────────┘
```

## 🎯 Nächste Schritte

1. ✅ Installieren Sie alle Abhängigkeiten
2. ✅ Starten Sie MongoDB
3. ✅ Starten Sie das Backend
4. ✅ Starten Sie das Frontend
5. ✅ (Optional) Installieren Sie Ollama
6. ✅ Konfigurieren Sie Ihren bevorzugten AI-Provider
7. ✅ Testen Sie mit Paper Trading
8. ✅ Viel Erfolg beim Trading! 📈

## 🆘 Support

Bei Problemen:
1. Prüfen Sie das **Troubleshooting** oben
2. Schauen Sie in die Backend-Logs
3. Schauen Sie in die Browser-Konsole (F12)
4. Öffnen Sie ein Issue auf GitHub

## 📄 Lizenz

Dieses Projekt ist für den persönlichen Gebrauch bestimmt.

**⚠️ WARNUNG**: Trading birgt Risiken. Verwenden Sie diese Software auf eigene Gefahr. Testen Sie ausführlich mit Paper Trading, bevor Sie echtes Geld einsetzen!
