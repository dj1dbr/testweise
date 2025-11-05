"""
Commodity Data Processor for Multi-Commodity Trading
"""

import logging
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Commodity definitions - NUR Edelmetalle (auf ICMarketsEU-Demo handelbar)
# mt5_symbol values are based on ICMarketsEU-Demo broker (London region)
# These symbols were retrieved via MetaAPI /symbols endpoint
COMMODITIES = {
    # Precious Metals (Spot prices) - NUR DIESE FUNKTIONIEREN!
    "GOLD": {"name": "Gold", "symbol": "GC=F", "mt5_symbol": "XAUUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "SILVER": {"name": "Silber", "symbol": "SI=F", "mt5_symbol": "XAGUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "PLATINUM": {"name": "Platin", "symbol": "PL=F", "mt5_symbol": "XPTUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "PALLADIUM": {"name": "Palladium", "symbol": "PA=F", "mt5_symbol": "XPDUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"}
    
    # Energy & Agricultural Futures NICHT auf diesem Broker verfügbar!
    # WTI_CRUDE, BRENT_CRUDE, WHEAT, CORN, SOYBEANS, COFFEE, etc.
    # können nicht gehandelt werden (broker-spezifische Einschränkungen)
}
    
    # Kryptowährungen (Bitpanda)
    "BITCOIN": {"name": "Bitcoin", "symbol": "BTC-USD", "bitpanda_symbol": "BTC_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "ETHEREUM": {"name": "Ethereum", "symbol": "ETH-USD", "bitpanda_symbol": "ETH_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "RIPPLE": {"name": "Ripple", "symbol": "XRP-USD", "bitpanda_symbol": "XRP_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "CARDANO": {"name": "Cardano", "symbol": "ADA-USD", "bitpanda_symbol": "ADA_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "SOLANA": {"name": "Solana", "symbol": "SOL-USD", "bitpanda_symbol": "SOL_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "POLKADOT": {"name": "Polkadot", "symbol": "DOT-USD", "bitpanda_symbol": "DOT_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "LITECOIN": {"name": "Litecoin", "symbol": "LTC-USD", "bitpanda_symbol": "LTC_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
    "CHAINLINK": {"name": "Chainlink", "symbol": "LINK-USD", "bitpanda_symbol": "LINK_EUR", "category": "Kryptowährungen", "unit": "EUR", "platform": "BITPANDA"},
}


def fetch_commodity_data(commodity_id: str):
    """Fetch commodity data from Yahoo Finance"""
    try:
        if commodity_id not in COMMODITIES:
            logger.error(f"Unknown commodity: {commodity_id}")
            return None
            
        commodity = COMMODITIES[commodity_id]
        ticker = yf.Ticker(commodity["symbol"])
        
        # Get historical data
        hist = ticker.history(period="100d", interval="1h")
        
        if hist.empty:
            logger.warning(f"No data received for {commodity['name']}")
            return None
            
        return hist
    except Exception as e:
        logger.error(f"Error fetching {commodity_id} data: {e}")
        return None


def calculate_indicators(df):
    """Calculate technical indicators"""
    try:
        # SMA
        sma_indicator = SMAIndicator(close=df['Close'], window=20)
        df['SMA_20'] = sma_indicator.sma_indicator()
        
        # EMA
        ema_indicator = EMAIndicator(close=df['Close'], window=20)
        df['EMA_20'] = ema_indicator.ema_indicator()
        
        # RSI
        rsi_indicator = RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = rsi_indicator.rsi()
        
        # MACD
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_histogram'] = macd.macd_diff()
        
        return df
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return df


def generate_signal(latest_data):
    """Generate trading signal based on indicators - REALISTISCHE Strategie"""
    try:
        rsi = latest_data.get('RSI')
        macd = latest_data.get('MACD')
        macd_signal = latest_data.get('MACD_signal')
        price = latest_data.get('Close')
        ema = latest_data.get('EMA_20')
        sma = latest_data.get('SMA_20')
        
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
            return "HOLD", "NEUTRAL"
        
        # Determine trend
        trend = "NEUTRAL"
        if not pd.isna(ema) and not pd.isna(price):
            if price > ema * 1.002:
                trend = "UP"
            elif price < ema * 0.998:
                trend = "DOWN"
        
        # REALISTISCHE TRADING STRATEGIE
        signal = "HOLD"
        
        # BUY Bedingungen (konservativ):
        # 1. RSI überverkauft UND positives MACD Momentum
        if rsi < 35 and macd > macd_signal:
            signal = "BUY"
        
        # 2. Starker Aufwärtstrend mit Bestätigung
        elif trend == "UP" and rsi < 60 and macd > macd_signal:
            signal = "BUY"
        
        # SELL Bedingungen (konservativ):
        # 1. RSI überkauft UND negatives MACD Momentum
        elif rsi > 65 and macd < macd_signal:
            signal = "SELL"
        
        # 2. Starker Abwärtstrend mit Bestätigung
        elif trend == "DOWN" and rsi > 40 and macd < macd_signal:
            signal = "SELL"
        
        return signal, trend
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "HOLD", "NEUTRAL"


async def calculate_position_size(balance: float, price: float, db, max_risk_percent: float = 20.0, free_margin: float = None) -> float:
    """Calculate position size ensuring max portfolio risk and considering free margin"""
    try:
        # Get all open positions from database
        open_trades = await db.trades.find({"status": "OPEN"}).to_list(100)
        
        # Calculate total exposure from open positions
        total_exposure = sum([trade.get('entry_price', 0) * trade.get('quantity', 0) for trade in open_trades])
        
        # Calculate available capital (max_risk_percent of balance minus current exposure)
        max_portfolio_value = balance * (max_risk_percent / 100)
        available_capital = max(0, max_portfolio_value - total_exposure)
        
        # WICHTIG: Wenn free_margin übergeben wurde, limitiere auf verfügbare Margin
        if free_margin is not None and free_margin < 500:
            # Bei wenig freier Margin (< 500 EUR), nutze nur 20% davon für neue Order
            max_order_value = free_margin * 0.2
            available_capital = min(available_capital, max_order_value)
            logger.warning(f"⚠️ Geringe freie Margin ({free_margin:.2f} EUR) - Order auf {max_order_value:.2f} EUR limitiert")
        
        # Calculate lot size
        if available_capital > 0 and price > 0:
            lot_size = round(available_capital / price, 2)  # 2 Dezimalstellen
            # Minimum 0.01 (Broker-Minimum), maximum 0.1 für Sicherheit
            lot_size = max(0.01, min(lot_size, 0.1))
        else:
            lot_size = 0.01  # Minimum Lot Size (Broker-Standard)
            
        logger.info(f"Position size: {lot_size} lots (Balance: {balance}, Price: {price}, Free Margin: {free_margin}, Exposure: {total_exposure:.2f}/{max_portfolio_value:.2f})")
        
        return lot_size
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.001  # Minimum fallback
