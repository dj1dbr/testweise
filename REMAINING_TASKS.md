# Verbleibende Aufgaben für nächste Session

## Kritisch (müssen fertig werden):

### 1. Trade-Liste vervollständigen
**Was fehlt:**
- Delete-Endpoint ist im Backend (Zeile 1215 in server.py)
- Frontend: Trade-Tabelle im eigenen Tab mit:
  - Spalten: Commodity, Type, Entry Price, Current Price, P&L, Plattform, Status, Löschen-Button
  - Live P&L Berechnung
  - Lösch-Button mit Bestätigung

**Code-Stellen:**
- Backend: `/api/trades/{trade_id}` DELETE-Endpoint ✅ FERTIG
- Frontend: Dashboard.jsx - neuer Tab "Trades" ❌ FEHLT

### 2. Standard-Plattform Setting
**Was fehlt:**
- Dropdown in Settings: "Standard-Plattform für neue Trades"
- Options: MT5, Bitpanda
- Speichern in trading_settings

**Code-Stellen:**
- Backend: TradingSettings model erweitern um `default_platform: str = "MT5"`
- Frontend: SettingsForm - neues Feld

### 3. 3-Tab-Struktur
**Was fehlt:**
- Tabs-Komponente mit 3 Tabs:
  - Tab 1: "Rohstoffe" (aktuelle Cards)
  - Tab 2: "Trades" (neue Trade-Liste)
  - Tab 3: "Charts" (aktuelles Chart-Carousel verschieben)

**Code-Stellen:**
- Frontend: Dashboard.jsx - Tabs um Balance-Cards herum

### 4. Platform-Sync (geschlossene Positionen)
**Was fehlt:**
- Background-Task der alle 30 Sekunden läuft
- Vergleicht offene Positionen App vs MT5
- Wenn Position auf MT5 geschlossen → auch in App schließen

**Code-Stellen:**
- Backend: Neuer Background-Task `sync_mt5_positions()`
- Füge zu APScheduler hinzu

### 5. Hybrid-Modus
**Was fehlt:**
- Checkboxen erlauben Multi-Select
- State: `activePlatforms: ['MT5', 'BITPANDA']`
- Bei Trade: Round-Robin oder User-Auswahl
- "Auf welcher Plattform?" Dropdown bei KAUFEN/VERKAUFEN

**Code-Stellen:**
- Frontend: Balance-Cards - Multi-Checkbox-Logik
- Trade-Execution: Plattform-Auswahl

---

## Bugs gefunden:

1. ✅ FIXED: Syntax-Fehler in Dashboard.jsx Zeile 1035 (hidden div nicht geschlossen)
2. ❌ TODO: totalExposure muss pro Plattform berechnet werden (aktuell global)
3. ❌ TODO: Bitpanda Balance fetchen (aktuell hardcoded €0.00)

---

## Libertex MT5 Status:

✅ Account erstellt: 6d29e270-4404-4be2-af6c-e3903dadb6e1
✅ Region: London
✅ Symbole gemappt: 11/14 Rohstoffe handelbar
✅ Backend konfiguriert
✅ Datenbank bereinigt

**Verfügbar auf Libertex MT5:**
- XAUUSD (Gold)
- XAGUSD (Silber)
- PL (Platin)
- PA (Palladium)
- CL (WTI Öl) 🎉 NEU!
- WHEAT (Weizen) 🎉 NEU!
- CORN (Mais) 🎉 NEU!
- SOYBEAN (Sojabohnen) 🎉 NEU!
- COFFEE (Kaffee) 🎉 NEU!
- SUGAR (Zucker) 🎉 NEU!
- COCOA (Kakao) 🎉 NEU!

---

## Fertiggestellt diese Session:

✅ Libertex MT5-Broker eingerichtet
✅ Symbol-Mapping für 11 Rohstoffe
✅ Cards kompakter (RSI/MACD entfernt)
✅ Separate Balance-Felder MT5 + Bitpanda
✅ Checkboxen für Plattform-Wechsel
✅ Portfolio-Risiko pro Plattform
✅ DELETE Trade Endpoint im Backend
✅ Alle Trades aus DB gelöscht
✅ Syntax-Fehler behoben

**Fortschritt: ~70% der geplanten Features fertig**

---

## Nächste Session - Empfohlene Reihenfolge:

1. Trade-Liste Tab fertigstellen (15-20 min)
2. Standard-Plattform Setting (5 min)
3. 3-Tab-Struktur implementieren (20-30 min)
4. Platform-Sync Background-Task (15-20 min)
5. Hybrid-Modus (20-30 min) - OPTIONAL

**Geschätzte Zeit:** 1-2 Stunden
**Token-Bedarf:** ~50-60k

---

## Wichtige Dateien zum Weiterarbeiten:

- `/app/frontend/src/pages/Dashboard.jsx` - Haupt-UI
- `/app/backend/server.py` - API-Endpoints
- `/app/backend/commodity_processor.py` - Symbol-Mappings
- `/app/backend/metaapi_connector.py` - MT5 Connection
- `/app/backend/.env` - Account ID: 6d29e270-4404-4be2-af6c-e3903dadb6e1
