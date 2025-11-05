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

# Commodity definitions
COMMODITIES = {
    "WTI_CRUDE": {"name": "WTI Crude Oil", "symbol": "CL=F", "mt5_symbol": "USOIL", "category": "Energie", "unit": "USD/Barrel", "platform": "MT5"},
    "BRENT_CRUDE": {"name": "Brent Crude Oil", "symbol": "BZ=F", "mt5_symbol": "UKOIL", "category": "Energie", "unit": "USD/Barrel", "platform": "MT5"},
    "GOLD": {"name": "Gold", "symbol": "GC=F", "mt5_symbol": "XAUUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "SILVER": {"name": "Silber", "symbol": "SI=F", "mt5_symbol": "XAGUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "PLATINUM": {"name": "Platin", "symbol": "PL=F", "mt5_symbol": "XPTUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "PALLADIUM": {"name": "Palladium", "symbol": "PA=F", "mt5_symbol": "XPDUSD", "category": "Edelmetalle", "unit": "USD/oz", "platform": "MT5"},
    "COPPER": {"name": "Kupfer", "symbol": "HG=F", "mt5_symbol": "COPPER", "category": "Industriemetalle", "unit": "USD/lb", "platform": "MT5"},
    "ALUMINUM": {"name": "Aluminium", "symbol": "ALI=F", "mt5_symbol": "ALUMINUM", "category": "Industriemetalle", "unit": "USD/ton", "platform": "MT5"},
    "NATURAL_GAS": {"name": "Natural Gas", "symbol": "NG=F", "mt5_symbol": "NATURALGAS", "category": "Energie", "unit": "USD/MMBtu", "platform": "MT5"},
    "HEATING_OIL": {"name": "Heizöl", "symbol": "HO=F", "mt5_symbol": "HEATINGOIL", "category": "Energie", "unit": "USD/Gallon", "platform": "MT5"},
    "WHEAT": {"name": "Weizen", "symbol": "ZW=F", "mt5_symbol": "WHEAT", "category": "Agrar", "unit": "USD/Bushel", "platform": "MT5"},
    "CORN": {"name": "Mais", "symbol": "ZC=F", "mt5_symbol": "CORN", "category": "Agrar", "unit": "USD/Bushel", "platform": "MT5"},
    "SOYBEANS": {"name": "Sojabohnen", "symbol": "ZS=F", "mt5_symbol": "SOYBEANS", "category": "Agrar", "unit": "USD/Bushel", "platform": "MT5"},
    "COFFEE": {"name": "Kaffee", "symbol": "KC=F", "mt5_symbol": "COFFEE", "category": "Agrar", "unit": "USD/lb", "platform": "MT5"},
    
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
    """Generate trading signal based on indicators"""
    try:
        rsi = latest_data.get('RSI')
        macd = latest_data.get('MACD')
        macd_signal = latest_data.get('MACD_signal')
        price = latest_data.get('Close')
        ema = latest_data.get('EMA_20')
        
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
            return "HOLD", "NEUTRAL"
        
        # Determine trend
        trend = "NEUTRAL"
        if not pd.isna(ema) and not pd.isna(price):
            if price > ema:
                trend = "UP"
            elif price < ema:
                trend = "DOWN"
        
        # Generate signal - GELOCKERTE Bedingungen für mehr Trades
        signal = "HOLD"
        
        # BUY signal: RSI < 50 (statt 40) und MACD positiv
        if rsi < 50 and macd > macd_signal:
            signal = "BUY"
        
        # SELL signal: RSI > 50 (statt 60) und MACD negativ
        elif rsi > 50 and macd < macd_signal:
            signal = "SELL"
        
        # Alternative: Starke Trends allein können auch Signale geben
        elif trend == "UP" and rsi < 45 and price > ema * 1.001:
            signal = "BUY"
        
        elif trend == "DOWN" and rsi > 55 and price < ema * 0.999:
            signal = "SELL"
        
        return signal, trend
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "HOLD", "NEUTRAL"


async def calculate_position_size(balance: float, price: float, db, max_risk_percent: float = 20.0) -> float:
    """Calculate position size ensuring max portfolio risk"""
    try:
        # Get all open positions
        open_trades = await db.trades.find({"status": "OPEN"}).to_list(100)
        
        # Calculate total exposure from open positions
        total_exposure = sum([trade.get('entry_price', 0) * trade.get('quantity', 0) for trade in open_trades])
        
        # Calculate available capital (20% of balance minus current exposure)
        max_portfolio_value = balance * (max_risk_percent / 100)
        available_capital = max(0, max_portfolio_value - total_exposure)
        
        # Calculate lot size
        if available_capital > 0 and price > 0:
            lot_size = round(available_capital / price, 2)
        else:
            lot_size = 0.0
            
        logger.info(f"Position size: {lot_size} lots (Balance: {balance}, Price: {price}, Exposure: {total_exposure:.2f}/{max_portfolio_value:.2f})")
        
        return lot_size
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.0
