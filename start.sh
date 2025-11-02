#!/bin/bash

# WTI Smart Trader - Lokales Start-Skript für macOS
# Dieses Skript startet alle benötigten Services

set -e  # Exit on error

echo "🚀 WTI Smart Trader wird gestartet..."
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Projektverzeichnis
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Funktion: Service-Check
check_service() {
    local service=$1
    local port=$2
    local name=$3
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${GREEN}✓${NC} $name läuft bereits auf Port $port"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $name läuft nicht auf Port $port"
        return 1
    fi
}

# Funktion: MongoDB prüfen/starten
start_mongodb() {
    echo -e "${BLUE}[1/4]${NC} MongoDB wird geprüft..."
    
    if check_service "mongod" 27017 "MongoDB"; then
        return 0
    fi
    
    # Versuche MongoDB mit Homebrew zu starten
    if command -v brew &> /dev/null; then
        echo "  Starte MongoDB mit Homebrew..."
        brew services start mongodb-community@7.0 2>/dev/null || brew services start mongodb-community 2>/dev/null || {
            echo -e "${RED}✗${NC} MongoDB konnte nicht gestartet werden"
            echo "  Bitte installieren Sie MongoDB: brew install mongodb-community@7.0"
            exit 1
        }
        sleep 3
        if check_service "mongod" 27017 "MongoDB"; then
            return 0
        fi
    fi
    
    echo -e "${RED}✗${NC} MongoDB konnte nicht gestartet werden"
    echo "  Starten Sie MongoDB manuell: mongod --dbpath ~/data/db"
    exit 1
}

# Funktion: Backend starten
start_backend() {
    echo -e "${BLUE}[2/4]${NC} Backend wird gestartet..."
    
    if check_service "uvicorn" 8001 "Backend"; then
        echo "  Backend bereits aktiv, wird neu gestartet..."
        pkill -f "uvicorn server:app" 2>/dev/null || true
        sleep 2
    fi
    
    cd "$PROJECT_DIR/backend"
    
    # Virtual Environment aktivieren, falls vorhanden
    if [ -d "$PROJECT_DIR/venv" ]; then
        source "$PROJECT_DIR/venv/bin/activate"
    fi
    
    # Backend im Hintergrund starten
    nohup uvicorn server:app --host 0.0.0.0 --port 8001 --reload > /tmp/wti-backend.log 2>&1 &
    BACKEND_PID=$!
    
    echo "  Backend PID: $BACKEND_PID"
    echo "  Warte auf Backend-Start..."
    sleep 5
    
    if check_service "uvicorn" 8001 "Backend"; then
        echo -e "${GREEN}✓${NC} Backend erfolgreich gestartet"
        echo "  API Dokumentation: http://localhost:8001/docs"
    else
        echo -e "${RED}✗${NC} Backend konnte nicht gestartet werden"
        echo "  Logs: tail -f /tmp/wti-backend.log"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
}

# Funktion: Frontend starten
start_frontend() {
    echo -e "${BLUE}[3/4]${NC} Frontend wird gestartet..."
    
    if check_service "node" 3000 "Frontend"; then
        echo "  Frontend bereits aktiv, wird neu gestartet..."
        pkill -f "react-scripts start" 2>/dev/null || true
        pkill -f "craco start" 2>/dev/null || true
        sleep 2
    fi
    
    cd "$PROJECT_DIR/frontend"
    
    # Frontend im Hintergrund starten
    nohup yarn start > /tmp/wti-frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    echo "  Frontend PID: $FRONTEND_PID"
    echo "  Warte auf Frontend-Build..."
    sleep 10
    
    if check_service "node" 3000 "Frontend"; then
        echo -e "${GREEN}✓${NC} Frontend erfolgreich gestartet"
        echo "  Dashboard: http://localhost:3000"
    else
        echo -e "${RED}✗${NC} Frontend konnte nicht gestartet werden"
        echo "  Logs: tail -f /tmp/wti-frontend.log"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
}

# Funktion: Ollama prüfen (optional)
check_ollama() {
    echo -e "${BLUE}[4/4]${NC} Ollama wird geprüft (optional)..."
    
    if check_service "ollama" 11434 "Ollama"; then
        # Verfügbare Modelle anzeigen
        if command -v ollama &> /dev/null; then
            echo "  Verfügbare Modelle:"
            ollama list 2>/dev/null | sed 's/^/    /' || echo "    Keine Modelle installiert"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Ollama läuft nicht (optional für lokale AI)"
        echo "  Zum Starten: ollama serve &"
        echo "  Zum Installieren: brew install ollama"
    fi
}

# Funktion: Status anzeigen
show_status() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✅ WTI Smart Trader erfolgreich gestartet!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 Services:"
    echo "  • MongoDB:  http://localhost:27017"
    echo "  • Backend:  http://localhost:8001"
    echo "  • Frontend: http://localhost:3000"
    echo "  • API Docs: http://localhost:8001/docs"
    echo ""
    echo "🌐 Öffnen Sie im Browser: http://localhost:3000"
    echo ""
    echo "📝 Logs:"
    echo "  • Backend:  tail -f /tmp/wti-backend.log"
    echo "  • Frontend: tail -f /tmp/wti-frontend.log"
    echo ""
    echo "🛑 Zum Beenden:"
    echo "  • ./stop.sh"
    echo "  • Oder: pkill -f 'uvicorn|react-scripts|craco'"
    echo ""
}

# Hauptprogramm
main() {
    start_mongodb
    start_backend
    start_frontend
    check_ollama
    show_status
}

# Ausführen
main
