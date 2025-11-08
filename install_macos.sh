#!/bin/bash

# Rohstoff Trader - macOS Installation Script
# Automatisiert die Installation aller Abhängigkeiten

set -e  # Bei Fehler abbrechen

echo "========================================"
echo "Rohstoff Trader - macOS Setup"
echo "========================================"
echo ""

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# System-Info
echo -e "${YELLOW}System-Information:${NC}"
echo "  OS: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "  Architektur: $(uname -m)"
echo ""

# Homebrew prüfen
echo -e "${YELLOW}Schritt 1: Homebrew prüfen...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew nicht gefunden. Installiere Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo -e "${GREEN}✓ Homebrew installiert${NC}"
else
    echo -e "${GREEN}✓ Homebrew bereits installiert${NC}"
fi
echo ""

# System-Bibliotheken installieren
echo -e "${YELLOW}Schritt 2: System-Bibliotheken installieren...${NC}"
brew install openssl rust postgresql libjpeg libpng || true
echo -e "${GREEN}✓ System-Bibliotheken installiert${NC}"
echo ""

# Python prüfen/installieren
echo -e "${YELLOW}Schritt 3: Python 3.11 prüfen...${NC}"
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}Python 3.11 nicht gefunden. Installiere...${NC}"
    brew install python@3.11
    echo -e "${GREEN}✓ Python 3.11 installiert${NC}"
else
    echo -e "${GREEN}✓ Python 3.11 bereits installiert${NC}"
    python3.11 --version
fi
echo ""

# Node.js prüfen/installieren
echo -e "${YELLOW}Schritt 4: Node.js prüfen...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Node.js nicht gefunden. Installiere...${NC}"
    brew install node
    echo -e "${GREEN}✓ Node.js installiert${NC}"
else
    echo -e "${GREEN}✓ Node.js bereits installiert${NC}"
    node --version
fi
echo ""

# Yarn prüfen/installieren
echo -e "${YELLOW}Schritt 5: Yarn prüfen...${NC}"
if ! command -v yarn &> /dev/null; then
    echo -e "${YELLOW}Yarn nicht gefunden. Installiere...${NC}"
    npm install -g yarn
    echo -e "${GREEN}✓ Yarn installiert${NC}"
else
    echo -e "${GREEN}✓ Yarn bereits installiert${NC}"
    yarn --version
fi
echo ""

# MongoDB prüfen/installieren
echo -e "${YELLOW}Schritt 6: MongoDB prüfen...${NC}"
if ! brew list mongodb-community &> /dev/null; then
    echo -e "${YELLOW}MongoDB nicht gefunden. Installiere...${NC}"
    brew tap mongodb/brew
    brew install mongodb-community
    echo -e "${GREEN}✓ MongoDB installiert${NC}"
else
    echo -e "${GREEN}✓ MongoDB bereits installiert${NC}"
fi

# MongoDB starten
echo -e "${YELLOW}Starte MongoDB...${NC}"
brew services start mongodb-community
echo -e "${GREEN}✓ MongoDB gestartet${NC}"
echo ""

# Apple Silicon spezifische Checks
if [[ $(uname -m) == 'arm64' ]]; then
    echo -e "${YELLOW}Apple Silicon (M1/M2/M3/M4) erkannt${NC}"
    
    # Rosetta 2 prüfen
    if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
        echo -e "${YELLOW}Rosetta 2 wird installiert...${NC}"
        softwareupdate --install-rosetta --agree-to-license
        echo -e "${GREEN}✓ Rosetta 2 installiert${NC}"
    else
        echo -e "${GREEN}✓ Rosetta 2 bereits installiert${NC}"
    fi
    
    # XCode Command Line Tools prüfen
    if ! xcode-select -p &> /dev/null; then
        echo -e "${YELLOW}XCode Command Line Tools werden installiert...${NC}"
        xcode-select --install
        echo -e "${YELLOW}Bitte warten Sie, bis die Installation abgeschlossen ist...${NC}"
        read -p "Drücken Sie Enter, wenn die Installation abgeschlossen ist..."
        echo -e "${GREEN}✓ XCode Command Line Tools installiert${NC}"
    else
        echo -e "${GREEN}✓ XCode Command Line Tools bereits installiert${NC}"
    fi
fi
echo ""

# Backend einrichten
echo -e "${YELLOW}Schritt 7: Backend einrichten...${NC}"
cd backend

# Virtual Environment erstellen
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Erstelle Virtual Environment...${NC}"
    python3.11 -m venv venv
    echo -e "${GREEN}✓ Virtual Environment erstellt${NC}"
else
    echo -e "${GREEN}✓ Virtual Environment existiert bereits${NC}"
fi

# Virtual Environment aktivieren
source venv/bin/activate

# pip aktualisieren
echo -e "${YELLOW}Aktualisiere pip, setuptools und wheel...${NC}"
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip aktualisiert${NC}"

# Umgebungsvariablen für Apple Silicon
if [[ $(uname -m) == 'arm64' ]]; then
    export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
    export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
    export LDFLAGS="-L$(brew --prefix openssl)/lib"
    export CPPFLAGS="-I$(brew --prefix openssl)/include"
fi

# Dependencies installieren
echo -e "${YELLOW}Installiere Python-Abhängigkeiten...${NC}"
echo -e "${YELLOW}(Dies kann einige Minuten dauern)${NC}"
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Alle Python-Abhängigkeiten installiert${NC}"
else
    echo -e "${RED}✗ Fehler bei der Installation der Python-Abhängigkeiten${NC}"
    echo -e "${YELLOW}Versuche problematische Pakete einzeln zu installieren...${NC}"
    
    # Versuche grpcio mit speziellen Flags
    pip install grpcio==1.75.1 --no-binary=grpcio || pip install grpcio==1.54.0
    
    # Versuche cryptography mit speziellen Flags  
    pip install cryptography==46.0.2 --no-binary=cryptography || pip install cryptography==42.0.0
    
    # Restliche Pakete
    pip install -r requirements.txt || true
fi

cd ..
echo ""

# Frontend einrichten
echo -e "${YELLOW}Schritt 8: Frontend einrichten...${NC}"
cd frontend

echo -e "${YELLOW}Installiere Frontend-Abhängigkeiten...${NC}"
echo -e "${YELLOW}(Dies kann einige Minuten dauern)${NC}"
yarn install

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Alle Frontend-Abhängigkeiten installiert${NC}"
else
    echo -e "${RED}✗ Fehler bei der Installation der Frontend-Abhängigkeiten${NC}"
fi

cd ..
echo ""

# .env Dateien prüfen
echo -e "${YELLOW}Schritt 9: Konfiguration prüfen...${NC}"

if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}backend/.env nicht gefunden - erstelle Vorlage...${NC}"
    cat > backend/.env << 'EOF'
# MongoDB (lokal)
MONGO_URL=mongodb://localhost:27017
DB_NAME=rohstoff_trader

# MetaAPI
METAAPI_ACCOUNT_ID_LIBERTEX=IHR_LIBERTEX_ACCOUNT_ID
METAAPI_TOKEN_LIBERTEX=IHR_LIBERTEX_TOKEN
METAAPI_ACCOUNT_ID_ICMARKETS=IHR_ICMARKETS_ACCOUNT_ID
METAAPI_TOKEN_ICMARKETS=IHR_ICMARKETS_TOKEN

# Bitpanda (optional)
BITPANDA_API_KEY=IHR_BITPANDA_API_KEY
BITPANDA_EMAIL=ihre-email@example.com

# OpenAI (optional)
OPENAI_API_KEY=IHR_OPENAI_KEY
EOF
    echo -e "${GREEN}✓ backend/.env Vorlage erstellt${NC}"
    echo -e "${RED}⚠ Bitte backend/.env mit Ihren API-Keys anpassen!${NC}"
else
    echo -e "${GREEN}✓ backend/.env existiert bereits${NC}"
fi

if [ ! -f "frontend/.env" ]; then
    echo -e "${YELLOW}frontend/.env nicht gefunden - erstelle Vorlage...${NC}"
    cat > frontend/.env << 'EOF'
# Backend URL (lokal)
REACT_APP_BACKEND_URL=http://localhost:8001
EOF
    echo -e "${GREEN}✓ frontend/.env erstellt${NC}"
else
    echo -e "${GREEN}✓ frontend/.env existiert bereits${NC}"
fi
echo ""

# Zusammenfassung
echo "========================================"
echo -e "${GREEN}Installation abgeschlossen!${NC}"
echo "========================================"
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. API-Keys konfigurieren:"
echo "   nano backend/.env"
echo ""
echo "2. Backend starten:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
echo ""
echo "3. Frontend starten (neues Terminal):"
echo "   cd frontend"
echo "   yarn start"
echo ""
echo "4. App öffnen:"
echo "   http://localhost:3000"
echo ""
echo "Weitere Informationen: LOKALE_INSTALLATION_MAC.md"
echo ""
