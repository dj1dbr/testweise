# Anleitung: Broker-Wechsel für Rohstoff Trader

## Wenn Sie zu einem anderen MT5-Broker wechseln möchten

### Schritt 1: Neue Broker-Zugangsdaten eintragen

Öffnen Sie `/app/backend/.env` und aktualisieren Sie:

```bash
# Alte MetaAPI Account-Daten ersetzen
METAAPI_ACCOUNT_ID=NEUE_UUID_HIER
METAAPI_TOKEN=NEUER_TOKEN_HIER

# Falls anderer Region (z.B. New York statt London)
# Dann in metaapi_connector.py die base_url anpassen
```

**So finden Sie die neuen Daten:**
1. Gehen Sie zu https://app.metaapi.cloud
2. Fügen Sie Ihren neuen MT5-Broker hinzu
3. Kopieren Sie Account ID (UUID-Format)
4. Kopieren Sie Ihren API Token

### Schritt 2: Automatisches Symbol-Mapping ausführen

```bash
cd /app/backend
python auto_map_broker_symbols.py
```

**Das Script macht automatisch:**
- ✅ Ruft alle verfügbaren Symbole vom neuen Broker ab
- ✅ Findet die richtigen Symbol-Namen für alle Rohstoffe
- ✅ Generiert den fertigen Code zum Kopieren

### Schritt 3: Code aktualisieren

Das Script zeigt Ihnen:

1. **COMMODITIES-Code** für `commodity_processor.py`
2. **MT5_TRADEABLE-Liste** für `server.py`

Kopieren Sie diese und ersetzen Sie in den entsprechenden Dateien.

### Schritt 4: Backend neu starten

```bash
sudo supervisorctl restart backend
```

### Schritt 5: Testen

```bash
# Test: Symbolzuordnung prüfen
curl https://trade-hub-116.preview.emergentagent.com/api/mt5/symbols

# Test: Account-Verbindung
curl https://trade-hub-116.preview.emergentagent.com/api/mt5/account

# Test: Manuelle Order (z.B. Gold)
curl -X POST "https://trade-hub-116.preview.emergentagent.com/api/trades/execute?trade_type=BUY&price=3978&commodity=GOLD"
```

## Beispiel: Broker-spezifische Symbole

### ICMarkets (aktuell):
- Gold: `XAUUSD`
- WTI: `WTI_F6`
- Weizen: `Wheat_H6`

### Andere Broker (Beispiele):
- Gold: `XAUUSD`, `GOLD`, `GC-FUT`
- WTI: `USOIL`, `CL.fut`, `CRUDE`, `WTI`
- Weizen: `WHEAT`, `ZW-FUT`, `W-FUTURE`

**Das automatische Mapping findet die richtigen Symbole für Sie!**

## Hinweis zu Futures

Manche Broker bieten:
- **Spot-Preise** (z.B. XAUUSD für Gold) ✅ Einfacher
- **Futures-Kontrakte** (z.B. GC-M25 für Gold Mai 2025) ⚠️ Komplexer

Bei Futures müssen Sie:
1. Regelmäßig den Kontraktmonat aktualisieren (z.B. von H6 auf M6)
2. Oder das Script anpassen, um automatisch den nächsten Kontrakt zu wählen

## Wichtig: Region-URL

Verschiedene Broker sind in verschiedenen MetaAPI-Regionen:

```python
# In metaapi_connector.py:
# London (aktuell)
self.base_url = "https://mt-client-api-v1.london.agiliumtrade.ai"

# New York
self.base_url = "https://mt-client-api-v1.new-york.agiliumtrade.ai"

# Singapore
self.base_url = "https://mt-client-api-v1.singapore.agiliumtrade.ai"
```

Verwenden Sie das `list_metaapi_accounts.py` Script, um die richtige Region zu finden:

```bash
cd /app/backend
python list_metaapi_accounts.py
```

## Zusammenfassung

✅ **Was automatisch funktioniert:**
- Preisanzeige für alle Rohstoffe
- Frontend bleibt gleich
- Account-Verbindung

🔧 **Was angepasst werden muss:**
- Symbol-Namen (mit auto_map_broker_symbols.py)
- Eventuell Region-URL (mit list_metaapi_accounts.py)
- MT5_TRADEABLE Liste aktualisieren

**Zeit: ca. 5-10 Minuten** für kompletten Broker-Wechsel! 🚀
