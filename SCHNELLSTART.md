# 🚀 SCHNELLSTART - WTI Smart Trader

**Komplett lokale Trading-App für macOS - Keine Cloud-Abhängigkeiten!**

## ⚡ In 5 Minuten starten

### 1. Voraussetzungen installieren

```bash
# Homebrew (falls nicht vorhanden)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# MongoDB + Node.js + Python
brew install mongodb-community@7.0 node python@3.11

# Yarn
npm install -g yarn

# MongoDB starten
brew services start mongodb-community@7.0
```

### 2. App-Abhängigkeiten installieren

```bash
cd /pfad/zum/trader

# Backend
cd backend && pip install -r requirements.txt && cd ..

# Frontend
cd frontend && yarn install && cd ..
```

### 3. App starten

```bash
# Einfach mit dem Start-Skript:
./start.sh

# ODER manuell:
# Terminal 1: cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload
# Terminal 2: cd frontend && yarn start
```

### 4. Im Browser öffnen

**http://localhost:3000** 🎉

---

## 🤖 Ollama für lokale AI (Optional)

```bash
# Ollama installieren
brew install ollama

# Ollama Server starten
ollama serve &

# Empfohlenes Modell herunterladen
ollama pull mistral
```

**In der App:** Einstellungen → KI Provider → "Ollama (Lokal)" wählen

---

## 🎯 Erste Schritte

1. **Dashboard öffnen**: http://localhost:3000
2. **Einstellungen** (⚙️) öffnen
3. **KI Provider wählen**:
   - **Ollama (Lokal)** - Kostenlos, keine API-Kosten
   - **Emergent LLM** - Universal Cloud Key
   - **OpenAI/Gemini/Claude** - Eigener API Key
4. **Paper Trading testen**
5. Viel Erfolg! 📈

---

## 📚 Vollständige Dokumentation

Siehe [README.md](README.md) für:
- Detaillierte Installation
- AI-Provider-Konfiguration
- Troubleshooting
- Verwendung & Features

---

## 🛑 App stoppen

```bash
./stop.sh
```

---

## 💡 Wichtige Hinweise

✅ **Komplett lokal**: Läuft auf Ihrem Mac
✅ **Keine Cloud**: MongoDB lokal, keine externen Server
✅ **Flexible AI**: Wählen Sie zwischen lokal (Ollama) und Cloud (OpenAI/Gemini/Claude)
✅ **Paper Trading**: Testen Sie risikofrei
✅ **Live-Daten**: Yahoo Finance API (kostenlos)

⚠️ **Trading-Warnung**: Nur für Bildungszwecke. Kein Finanzrat. Risiko beachten!

---

**Viel Erfolg beim Trading! 🚀**
