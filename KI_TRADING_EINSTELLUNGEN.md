# KI Trading Strategie-Einstellungen

## Übersicht

Die Rohstoff Trader App bietet jetzt erweiterte KI Trading Strategie-Einstellungen, mit denen Sie die automatische Trading-Logik nach Ihren Wünschen anpassen können.

---

## 📍 Wo finde ich die Einstellungen?

1. Öffnen Sie die App
2. Klicken Sie auf **"Einstellungen"** (oben rechts)
3. Scrollen Sie nach unten zur Sektion **"🤖 KI Trading Strategie"**

---

## ⚙️ Verfügbare Parameter

### 1. **RSI Kaufsignal (Oversold)**
- **Standard**: 30
- **Bereich**: 0 - 50
- **Beschreibung**: Wenn der RSI unter diesen Wert fällt, generiert die KI ein Kaufsignal
- **Tipp**: 
  - Niedrigere Werte (z.B. 20) = Konservativer, weniger Signale
  - Höhere Werte (z.B. 35-40) = Aggressiver, mehr Signale

**Beispiel:**
```
RSI = 25, Threshold = 30 → KAUFSIGNAL ✅
RSI = 35, Threshold = 30 → Kein Signal
```

---

### 2. **RSI Verkaufssignal (Overbought)**
- **Standard**: 70
- **Bereich**: 50 - 100
- **Beschreibung**: Wenn der RSI über diesen Wert steigt, generiert die KI ein Verkaufssignal
- **Tipp**:
  - Höhere Werte (z.B. 80) = Konservativer, weniger Signale
  - Niedrigere Werte (z.B. 65) = Aggressiver, mehr Signale

**Beispiel:**
```
RSI = 75, Threshold = 70 → VERKAUFSSIGNAL ✅
RSI = 65, Threshold = 70 → Kein Signal
```

---

### 3. **Minimale Konfidenz für Auto-Trading**
- **Standard**: 0.6 (60%)
- **Bereich**: 0.0 - 1.0
- **Beschreibung**: Die KI führt nur Trades aus, wenn die Konfidenz über diesem Wert liegt
- **Tipp**:
  - 0.5-0.6 = Ausgewogen (empfohlen für Anfänger)
  - 0.7-0.8 = Konservativ (nur sehr sichere Trades)
  - 0.4-0.5 = Aggressiv (mehr Trades, höheres Risiko)

**Was ist Konfidenz?**
Die KI bewertet jedes Signal anhand mehrerer Faktoren:
- RSI-Wert
- MACD-Signal
- Trend (SMA/EMA)
- Volumen
- Volatilität

Eine Konfidenz von 0.6 bedeutet: 60% Wahrscheinlichkeit, dass der Trade profitabel ist.

---

### 4. **Risiko pro Trade (% der Balance)**
- **Standard**: 2%
- **Bereich**: 0.5% - 10%
- **Beschreibung**: Maximales Risiko pro einzelnem Trade
- **Tipp**:
  - 1-2% = Konservativ (empfohlen)
  - 3-5% = Moderat
  - 5-10% = Aggressiv (nicht empfohlen)

**Beispiel:**
```
Balance: €10.000
Risiko pro Trade: 2%
→ Maximaler Verlust pro Trade: €200
```

**Berechnung der Position-Size:**
```
Stop Loss: 2%
Risiko: 2% (€200)
→ Position-Size = €200 / 0.02 = €10.000
```

---

### 5. **Trend-Following aktivieren**
- **Standard**: AN ✅
- **Beschreibung**: Die KI handelt nur in Richtung des aktuellen Trends

**Wie funktioniert das?**
- Trend UP (Preis > SMA 20): Nur KAUFSIGNALE
- Trend DOWN (Preis < SMA 20): Nur VERKAUFSSIGNALE

**Vorteil**: Reduziert Verluste durch Counter-Trend Trading

**Nachteil**: Verpasst möglicherweise frühe Trendwechsel

**Tipp**: Für Anfänger IMMER aktiviert lassen!

---

### 6. **Volumen-Bestätigung**
- **Standard**: AN ✅
- **Beschreibung**: Die KI nutzt Handelsvolumen zur Signal-Bestätigung

**Wie funktioniert das?**
Ein Signal wird nur akzeptiert, wenn das Volumen überdurchschnittlich ist.

**Beispiel:**
```
RSI = 25 (Kaufsignal)
Volumen = 500.000 (durchschnittlich)
→ Kein Trade

RSI = 25 (Kaufsignal)
Volumen = 1.200.000 (überdurchschnittlich)
→ Trade wird ausgeführt ✅
```

**Vorteil**: Filtert Fehlsignale bei niedrigem Volumen

**Tipp**: Für Anfänger IMMER aktiviert lassen!

---

## 🔄 Zurücksetzen auf Standardwerte

### Wann sollte ich zurücksetzen?

- Sie haben zu viele Parameter verstellt
- Die App generiert zu viele oder zu wenige Signale
- Sie möchten mit den bewährten Standardwerten neu starten

### Wie funktioniert der Reset?

1. Öffnen Sie **Einstellungen**
2. Scrollen Sie zur **"KI Trading Strategie"** Sektion
3. Klicken Sie oben rechts auf **"🔄 Zurücksetzen"**
4. Bestätigen Sie mit **"OK"**

**Was wird zurückgesetzt?**
- ✅ Alle KI-Strategie-Parameter
- ✅ Stop Loss / Take Profit Werte
- ✅ Trailing Stop Einstellungen
- ✅ Max. Trades pro Stunde
- ❌ **NICHT** zurückgesetzt: API-Keys, Account-IDs, Plattform-Aktivierungen

**Nach dem Reset:**
Die Seite lädt automatisch neu und alle Werte sind wieder auf den Standardwerten.

---

## 📊 Empfohlene Einstellungen

### Für Anfänger (Konservativ)
```
RSI Oversold: 25
RSI Overbought: 75
Min. Konfidenz: 0.7
Risiko pro Trade: 1%
Trend-Following: AN ✅
Volumen-Bestätigung: AN ✅
```

**Ergebnis**: Wenige, aber sehr sichere Trades

---

### Für Fortgeschrittene (Ausgewogen)
```
RSI Oversold: 30
RSI Overbought: 70
Min. Konfidenz: 0.6
Risiko pro Trade: 2%
Trend-Following: AN ✅
Volumen-Bestätigung: AN ✅
```

**Ergebnis**: Gute Balance zwischen Sicherheit und Häufigkeit (Standard)

---

### Für Erfahrene (Aggressiv)
```
RSI Oversold: 35
RSI Overbought: 65
Min. Konfidenz: 0.5
Risiko pro Trade: 3-5%
Trend-Following: AUS ❌
Volumen-Bestätigung: AUS ❌
```

**Ergebnis**: Viele Trades, höheres Risiko

⚠️ **Warnung**: Nur für erfahrene Trader empfohlen!

---

## 🎯 Strategie-Beispiele

### Scalping-Strategie
**Ziel**: Viele kleine Gewinne

```
RSI Oversold: 40
RSI Overbought: 60
Min. Konfidenz: 0.5
Risiko pro Trade: 1%
Stop Loss: 1%
Take Profit: 2%
```

---

### Swing-Trading-Strategie
**Ziel**: Mittelfristige Trends nutzen

```
RSI Oversold: 30
RSI Overbought: 70
Min. Konfidenz: 0.7
Risiko pro Trade: 2%
Stop Loss: 3%
Take Profit: 6%
Trend-Following: AN ✅
```

---

### Mean-Reversion-Strategie
**Ziel**: Von Überverkauft/Überkauft profitieren

```
RSI Oversold: 20
RSI Overbought: 80
Min. Konfidenz: 0.6
Risiko pro Trade: 2%
Trend-Following: AUS ❌
Volumen-Bestätigung: AN ✅
```

---

## 💡 Tipps & Tricks

### 1. **Backtesting**
Ändern Sie Parameter nur schrittweise und beobachten Sie die Ergebnisse über mehrere Tage.

### 2. **Risiko-Management**
Halten Sie das Gesamtrisiko unter 10% der Balance:
```
Max. 5 offene Trades × 2% Risiko = 10% Gesamt-Risiko
```

### 3. **Marktbedingungen**
- **Trending Markt**: Trend-Following AN, niedrige Konfidenz
- **Seitwärts Markt**: Trend-Following AUS, hohe Konfidenz
- **Volatiler Markt**: Höherer RSI-Threshold, höhere Konfidenz

### 4. **Zeit der Parameter-Änderung**
Ändern Sie Parameter am besten:
- ✅ Außerhalb der Handelszeiten
- ✅ Nach Analyse vergangener Trades
- ❌ NICHT während offener Positionen

---

## 🔧 Technische Details

### Wie die KI entscheidet

**Schritt 1: Daten sammeln**
- Aktueller Preis
- RSI, MACD, SMA, EMA
- Volumen
- Historische Volatilität

**Schritt 2: Signal generieren**
```python
if RSI < rsi_oversold_threshold:
    base_signal = "BUY"
elif RSI > rsi_overbought_threshold:
    base_signal = "SELL"
else:
    base_signal = "HOLD"
```

**Schritt 3: Konfidenz berechnen**
```python
confidence = calculate_confidence(
    rsi_value,
    macd_signal,
    trend_direction,
    volume_ratio,
    volatility
)
```

**Schritt 4: Filtern**
```python
if confidence >= min_confidence_score:
    if trend_following:
        if (base_signal == "BUY" and trend == "UP") or \
           (base_signal == "SELL" and trend == "DOWN"):
            execute_trade()
```

**Schritt 5: Position-Sizing**
```python
risk_amount = balance * (risk_per_trade_percent / 100)
position_size = risk_amount / (stop_loss_percent / 100)
```

---

## ❓ FAQ

**Q: Kann ich für verschiedene Rohstoffe unterschiedliche Einstellungen haben?**
A: Aktuell nicht. Die Einstellungen gelten für alle Rohstoffe. Ein zukünftiges Feature könnte individuelle Parameter pro Rohstoff ermöglichen.

**Q: Was passiert mit offenen Trades, wenn ich die Einstellungen ändere?**
A: Offene Trades behalten ihre ursprünglichen Stop Loss/Take Profit Werte. Nur neue Trades nutzen die neuen Einstellungen.

**Q: Wie oft sollte ich die Einstellungen anpassen?**
A: Maximal einmal pro Woche. Lassen Sie der Strategie Zeit zu arbeiten.

**Q: Gibt es eine Möglichkeit, verschiedene Strategien zu speichern?**
A: Aktuell nicht, aber Sie können Screenshots Ihrer Einstellungen machen, um verschiedene Konfigurationen zu dokumentieren.

---

## 🚀 Nächste Schritte

1. Starten Sie mit den **Standardwerten**
2. Beobachten Sie die Trades für **1-2 Wochen**
3. Analysieren Sie die Ergebnisse
4. Passen Sie **einen Parameter** leicht an
5. Beobachten Sie erneut
6. Wiederholen Sie den Prozess

**Wichtig**: Ändern Sie nie alle Parameter gleichzeitig!

---

## 📚 Weiterführende Informationen

- **RSI (Relative Strength Index)**: Misst Momentum (0-100)
- **MACD (Moving Average Convergence Divergence)**: Trend-Indikator
- **SMA/EMA**: Gleitende Durchschnitte zur Trendbestimmung
- **Volumen**: Bestätigt die Stärke eines Trends

---

## 🆘 Support

Bei Fragen oder Problemen:
1. Versuchen Sie einen Reset auf Standardwerte
2. Prüfen Sie die Logs im Backend Terminal
3. Kontaktieren Sie den Support

---

**Stand**: November 2024
**Version**: 2.0 mit KI-Strategie-Einstellungen
