#!/bin/bash

# WTI Smart Trader - Stop-Skript für macOS
# Stoppt alle laufenden Services

echo "🛑 WTI Smart Trader wird gestoppt..."

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Backend stoppen
echo "  Stoppe Backend..."
pkill -f "uvicorn server:app" 2>/dev/null && echo -e "${GREEN}✓${NC} Backend gestoppt" || echo -e "${YELLOW}⚠${NC} Backend läuft nicht"

# Frontend stoppen
echo "  Stoppe Frontend..."
pkill -f "react-scripts start" 2>/dev/null || pkill -f "craco start" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Frontend gestoppt"
else
    echo -e "${YELLOW}⚠${NC} Frontend läuft nicht"
fi

# MongoDB stoppen (optional - nur wenn nicht als System-Service)
read -p "MongoDB auch stoppen? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v brew &> /dev/null; then
        brew services stop mongodb-community@7.0 2>/dev/null || brew services stop mongodb-community 2>/dev/null
        echo -e "${GREEN}✓${NC} MongoDB gestoppt"
    else
        pkill mongod 2>/dev/null && echo -e "${GREEN}✓${NC} MongoDB gestoppt" || echo -e "${YELLOW}⚠${NC} MongoDB läuft nicht"
    fi
fi

echo ""
echo -e "${GREEN}✅ WTI Smart Trader gestoppt${NC}"
