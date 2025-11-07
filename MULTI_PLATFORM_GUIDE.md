# Multi-Platform Trading System - Implementierungsguide

## Übersicht

Das Rohstoff Trader System unterstützt jetzt **drei Trading-Plattformen parallel**:
- 🔷 **MT5 Libertex** (Primary Platform)
- 🟣 **MT5 ICMarkets** (Secondary Platform)
- 🟢 **Bitpanda** (Alternative Platform)

## Architektur

### Backend-Struktur

```
/app/backend/
├── multi_platform_connector.py    # Zentrale Platform-Verwaltung
├── metaapi_connector.py            # MetaAPI Integration (beide MT5)
├── bitpanda_connector.py           # Bitpanda Integration
├── commodity_processor.py          # Multi-Broker Symbol-Definitionen
└── server.py                       # API-Endpunkte & Models
```

### Frontend-Struktur

```
/app/frontend/src/pages/
└── Dashboard.jsx
    ├── 3 Balance-Cards (MT5 Libertex, MT5 ICMarkets, Bitpanda)
    ├── Platform-spezifischer State
    └── 3-Tab-Navigation (Rohstoffe, Trades, Charts)
```

## Commodity Symbol-Mapping

Jedes Commodity hat broker-spezifische Symbole:

### Edelmetalle
| Commodity | Libertex | ICMarkets | Bitpanda |
|-----------|----------|-----------|----------|
| Gold      | XAUUSD   | XAUUSD    | GOLD     |
| Silber    | XAGUSD   | XAGUSD    | SILVER   |
| Platin    | PL       | XPTUSD    | PLATINUM |
| Palladium | PA       | XPDUSD    | PALLADIUM|

### Energie
| Commodity | Libertex | ICMarkets | Bitpanda |
|-----------|----------|-----------|----------|
| WTI Crude | CL       | WTI_F6    | OIL_WTI  |
| Brent     | BRENT    | BRENT_F6  | OIL_BRENT|
| Nat. Gas  | NATURALGAS| -        | NATURAL_GAS|

### Agrar
| Commodity | Libertex | ICMarkets | Bitpanda |
|-----------|----------|-----------|----------|
| Weizen    | WHEAT    | Wheat_H6  | WHEAT    |
| Mais      | CORN     | Corn_H6   | CORN     |
| Sojabohnen| SOYBEAN  | Sbean_F6  | SOYBEANS |
| Kaffee    | COFFEE   | Coffee_H6 | COFFEE   |
| Zucker    | SUGAR    | Sugar_H6  | SUGAR    |
| Baumwolle | COTTON   | Cotton_H6 | COTTON   |
| Kakao     | COCOA    | Cocoa_H6  | COCOA    |

## API-Endpunkte

### Platform-Management
```
GET  /api/platforms/status                      # Status aller Plattformen
POST /api/platforms/{platform_name}/connect     # Platform verbinden
POST /api/platforms/{platform_name}/disconnect  # Platform trennen
GET  /api/platforms/{platform_name}/account     # Account-Info abrufen
GET  /api/platforms/{platform_name}/positions   # Offene Positionen
```

Platform-Namen:
- `MT5_LIBERTEX`
- `MT5_ICMARKETS`
- `BITPANDA`

### Trading
```
POST /api/trades/execute                        # Trade ausführen
GET  /api/trades/list                          # Alle Trades
DELETE /api/trades/{trade_id}                  # Trade löschen
POST /api/trades/close/{trade_id}              # Position schließen
```

### Existing Endpoints (weiterhin verfügbar)
```
GET  /api/commodities                          # Commodity-Definitionen
GET  /api/market/current                       # Aktuelle Marktdaten
GET  /api/market/all                           # Alle Märkte
GET  /api/settings                             # Trading-Einstellungen
POST /api/settings                             # Einstellungen speichern
```

## Environment-Variablen

Erforderliche Variablen in `/app/backend/.env`:

```bash
# MongoDB
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"

# MetaAPI (shared token für beide MT5-Accounts)
METAAPI_TOKEN="your_metaapi_token"

# MT5 Libertex (Primary)
METAAPI_ACCOUNT_ID="rohstoff-trader"

# MT5 ICMarkets (Secondary)
METAAPI_ICMARKETS_ACCOUNT_ID="d2605e89-7bc2-4144-9f7c-951edd596c39"

# Bitpanda
BITPANDA_API_KEY="your_bitpanda_key"
```

## Trading-Settings Model

```python
{
    "active_platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"],  # Array
    "default_platform": "MT5_LIBERTEX",
    "auto_trading": false,
    "use_ai_analysis": true,
    "max_portfolio_risk_percent": 20.0,
    "enabled_commodities": ["GOLD", "SILVER", "WTI_CRUDE", ...]
}
```

## Trade Model

```python
{
    "id": "uuid",
    "commodity": "WTI_CRUDE",
    "type": "BUY",
    "platform": "MT5_LIBERTEX",  # Neue Feld statt "mode"
    "price": 59.93,
    "quantity": 1.0,
    "entry_price": 59.93,
    "status": "OPEN",
    "profit_loss": 0.0
}
```

## Frontend-Verwendung

### Platform-Aktivierung

```javascript
// Checkboxen in Balance-Cards
const activatePlatform = async (platformName) => {
  const newPlatforms = [...settings.active_platforms, platformName];
  await handleUpdateSettings({ 
    ...settings, 
    active_platforms: newPlatforms 
  });
};
```

### Trade-Ausführung

```javascript
// Backend wählt automatisch die Platform aus settings
await axios.post(`${API}/trades/execute`, {
  trade_type: 'BUY',
  commodity: 'GOLD',
  price: 2650.00,
  quantity: 1.0
});
```

### Platform-spezifische Daten abrufen

```javascript
// MT5 Libertex Account
const response = await axios.get(`${API}/platforms/MT5_LIBERTEX/account`);

// MT5 ICMarkets Account
const response = await axios.get(`${API}/platforms/MT5_ICMARKETS/account`);

// Bitpanda Account
const response = await axios.get(`${API}/platforms/BITPANDA/account`);
```

## UI-Features

### Balance-Cards
- ✅ Drei separate Cards im 3-Spalten-Layout
- ✅ Unabhängige Checkboxen zur Aktivierung
- ✅ "Aktiv"-Badge bei verbundenen Plattformen
- ✅ Balance-Anzeige pro Platform
- ✅ Portfolio-Risiko-Anzeige pro Platform
- ✅ Status-Information (Region, Verbindung)

### Trade-Liste
- ✅ Live P&L-Berechnung für offene Positionen
- ✅ Platform-Badge (Libertex/ICMarkets/Bitpanda)
- ✅ Delete-Funktion für einzelne Trades
- ✅ Filter nach Status (OPEN/CLOSED)
- ✅ Sortierung und Übersicht

### Tab-Navigation
- 📊 **Rohstoffe**: Commodity-Cards mit Live-Preisen
- 📈 **Trades**: Vollständige Trade-Historie
- 📉 **Charts**: Markt-Charts mit technischen Indikatoren

## Bekannte Einschränkungen

### 1. MT5 Libertex Region
- Account "rohstoff-trader" ist nicht in London-Region verfügbar
- **Lösung**: Region über MetaAPI Dashboard anpassen oder neuen Account erstellen

### 2. ICMarkets Futures-Kontrakte
- Symbole wie WTI_F6, Wheat_H6 sind Futures mit Ablaufdatum
- **Empfehlung**: Regelmäßiges Contract-Rollover einplanen

### 3. Bitpanda-Verfügbarkeit
- Nur lokal auf Mac verfügbar (Netzwerk-Beschränkungen in Cloud)
- **Alternative**: VPN oder lokale Entwicklungsumgebung

## Nächste Schritte

### Kurzfristig
1. ☐ MT5 Libertex Region konfigurieren
2. ☐ Manuelle Connect/Disconnect-Buttons
3. ☐ Symbol-Validation vor Trade-Execution

### Mittelfristig
4. ☐ Platform-basiertes Trade-Routing
5. ☐ Automatisches Symbol-Mapping
6. ☐ Platform-spezifische Risk-Limits
7. ☐ Consolidated P&L über alle Plattformen

### Langfristig
8. ☐ Multi-Platform Arbitrage-Detection
9. ☐ Automated Contract-Rollover
10. ☐ Cross-Platform Position-Hedging
11. ☐ Advanced Multi-Platform Analytics

## Support & Troubleshooting

### Problem: Platform verbindet nicht
**Lösung**:
1. Prüfen Sie die Account-ID in `.env`
2. Verifizieren Sie den MetaAPI-Token
3. Überprüfen Sie die Region (London/New York/Singapore)
4. Testen Sie mit: `curl ${API}/platforms/MT5_LIBERTEX/account`

### Problem: Symbole nicht gefunden
**Lösung**:
1. Überprüfen Sie COMMODITIES-Definitionen in `commodity_processor.py`
2. Nutzen Sie `/api/mt5/symbols` für verfügbare Symbole
3. Passen Sie Symbol-Mapping für Ihren Broker an

### Problem: Trade-Execution schlägt fehl
**Lösung**:
1. Prüfen Sie Balance und freie Margin
2. Verifizieren Sie Mindestvolumen für Symbol
3. Überprüfen Sie Handelszeiten
4. Testen Sie mit kleineren Volumina

## Entwickler-Hinweise

### Neue Platform hinzufügen

1. **Backend**: Erweitern Sie `multi_platform_connector.py`
```python
self.platforms['NEW_PLATFORM'] = {
    'type': 'NEW',
    'name': 'New Platform',
    'connector': None,
    'active': False
}
```

2. **Frontend**: Fügen Sie Balance-Card hinzu
```jsx
<Card className="bg-gradient-to-br from-orange-900/20...">
  <input type="checkbox" checked={settings?.active_platforms?.includes('NEW_PLATFORM')} />
  <h3>🟠 New Platform</h3>
</Card>
```

3. **Models**: Erweitern Sie Literal-Types
```python
platform: Literal["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA", "NEW_PLATFORM"]
```

### Testing

```bash
# Backend starten
cd /app/backend
uvicorn server:app --reload

# Frontend starten
cd /app/frontend
yarn start

# API testen
curl https://your-domain/api/platforms/status
```

## Lizenz & Credits

Entwickelt für Rohstoff Trader Multi-Platform System
Version: 2.0
Letzte Aktualisierung: November 2025
