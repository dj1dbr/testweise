"""
Commodity Data Processor for Multi-Commodity Trading
"""

import logging
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Global reference to platform connector (will be set by server.py)
_platform_connector = None

def set_platform_connector(connector):
    """Set the platform connector for fetching MetaAPI data"""
    global _platform_connector
    _platform_connector = connector

# Commodity definitions - Multi-Platform Support mit separaten MT5 Brokern
# MT5 Libertex: Erweiterte Auswahl
# MT5 ICMarkets: Nur Edelmetalle + WTI_F6, BRENT_F6
# Bitpanda: Alle Rohstoffe verfügbar
COMMODITIES = {
    # Precious Metals (Spot prices)
    # Libertex: ✅ | ICMarkets: ✅ | Bitpanda: ✅
    "GOLD": {
        "name": "Gold", 
        "symbol": "GC=F", 
        "mt5_libertex_symbol": "XAUUSD",
        "mt5_icmarkets_symbol": "XAUUSD", 
        "bitpanda_symbol": "GOLD",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "SILVER": {
        "name": "Silber", 
        "symbol": "SI=F", 
        "mt5_libertex_symbol": "XAGUSD",
        "mt5_icmarkets_symbol": "XAGUSD", 
        "bitpanda_symbol": "SILVER",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "PLATINUM": {
        "name": "Platin", 
        "symbol": "PL=F", 
        "mt5_libertex_symbol": "PL",
        "mt5_icmarkets_symbol": "XPTUSD", 
        "bitpanda_symbol": "PLATINUM",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "PALLADIUM": {
        "name": "Palladium", 
        "symbol": "PA=F", 
        "mt5_libertex_symbol": "PA",
        "mt5_icmarkets_symbol": "XPDUSD", 
        "bitpanda_symbol": "PALLADIUM",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    
    # Energy Commodities
    # Libertex: ✅ CL, USOILCash, NGASCash | ICMarkets: ✅ WTI_F6, BRENT_F6 | Bitpanda: ✅ Alle
    "WTI_CRUDE": {
        "name": "WTI Crude Oil", 
        "symbol": "CL=F", 
        "mt5_libertex_symbol": "USOILCash",  # Libertex uses USOILCash
        "mt5_icmarkets_symbol": "WTI_F6", 
        "bitpanda_symbol": "OIL_WTI",
        "category": "Energie", 
        "unit": "USD/Barrel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "BRENT_CRUDE": {
        "name": "Brent Crude Oil", 
        "symbol": "BZ=F", 
        "mt5_libertex_symbol": "CL",  # Libertex CL for Brent
        "mt5_icmarkets_symbol": "BRENT_F6", 
        "bitpanda_symbol": "OIL_BRENT",
        "category": "Energie", 
        "unit": "USD/Barrel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "NATURAL_GAS": {
        "name": "Natural Gas", 
        "symbol": "NG=F", 
        "mt5_libertex_symbol": "NGASCash",  # Libertex uses NGASCash
        "mt5_icmarkets_symbol": None, 
        "bitpanda_symbol": "NATURAL_GAS",
        "category": "Energie", 
        "unit": "USD/MMBtu", 
        "platforms": ["MT5_LIBERTEX", "BITPANDA"]
    },
    
    # Agricultural Commodities
    # Libertex: ✅ | ICMarkets: teilweise | Bitpanda: ✅
    "WHEAT": {
        "name": "Weizen", 
        "symbol": "ZW=F", 
        "mt5_libertex_symbol": "WHEAT",
        "mt5_icmarkets_symbol": "Wheat_H6", 
        "bitpanda_symbol": "WHEAT",
        "category": "Agrar", 
        "unit": "USD/Bushel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "CORN": {
        "name": "Mais", 
        "symbol": "ZC=F", 
        "mt5_libertex_symbol": "CORN",
        "mt5_icmarkets_symbol": "Corn_H6", 
        "bitpanda_symbol": "CORN",
        "category": "Agrar", 
        "unit": "USD/Bushel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "SOYBEANS": {
        "name": "Sojabohnen", 
        "symbol": "ZS=F", 
        "mt5_libertex_symbol": "SOYBEAN",
        "mt5_icmarkets_symbol": "Sbean_F6", 
        "bitpanda_symbol": "SOYBEANS",
        "category": "Agrar", 
        "unit": "USD/Bushel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "COFFEE": {
        "name": "Kaffee", 
        "symbol": "KC=F", 
        "mt5_libertex_symbol": "COFFEE",
        "mt5_icmarkets_symbol": "Coffee_H6", 
        "bitpanda_symbol": "COFFEE",
        "category": "Agrar", 
        "unit": "USD/lb", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "SUGAR": {
        "name": "Zucker", 
        "symbol": "SB=F", 
        "mt5_libertex_symbol": "SUGAR",
        "mt5_icmarkets_symbol": "Sugar_H6", 
        "bitpanda_symbol": "SUGAR",
        "category": "Agrar", 
        "unit": "USD/lb", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "COTTON": {
        "name": "Baumwolle", 
        "symbol": "CT=F", 
        "mt5_libertex_symbol": "COTTON",
        "mt5_icmarkets_symbol": "Cotton_H6", 
        "bitpanda_symbol": "COTTON",
        "category": "Agrar", 
        "unit": "USD/lb", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "COCOA": {
        "name": "Kakao", 
        "symbol": "CC=F", 
        "mt5_libertex_symbol": "COCOA",
        "mt5_icmarkets_symbol": "Cocoa_H6", 
        "bitpanda_symbol": "COCOA",
        "category": "Agrar", 
        "unit": "USD/ton", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    }
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
        
        if hist.empty or len(hist) == 0:
            logger.warning(f"No data received for {commodity['name']}")
            return None
            
        return hist
    except Exception as e:
        logger.error(f"Error fetching {commodity_id} data: {e}")
        return None


import time
from datetime import datetime, timedelta

# Cache for OHLCV data to avoid rate limiting
_ohlcv_cache = {}
_cache_expiry = {}

async def fetch_metaapi_candles(commodity_id: str, timeframe: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
    """
    Fetch historical candle data from MetaAPI for supported commodities
    
    Args:
        commodity_id: Commodity identifier (e.g., 'GOLD', 'SILVER', 'WTI_CRUDE')
        timeframe: Timeframe - '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
        limit: Number of candles
    
    Returns:
        pandas DataFrame with OHLCV data or None if not available
    """
    try:
        if commodity_id not in COMMODITIES:
            return None
        
        commodity = COMMODITIES[commodity_id]
        
        # Check if MetaAPI is available for this commodity
        if _platform_connector is None:
            return None
        
        # Try ICMarkets first (primary broker)
        symbol = commodity.get('mt5_icmarkets_symbol')
        if symbol and 'MT5_ICMARKETS' in _platform_connector.platforms:
            connector = _platform_connector.platforms['MT5_ICMARKETS'].get('connector')
            if connector:
                candles = await connector.get_candles(symbol, timeframe, limit)
                if candles and len(candles) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(candles)
                    # Rename columns to match yfinance format
                    if 'time' in df.columns:
                        df['Date'] = pd.to_datetime(df['time'])
                        df.set_index('Date', inplace=True)
                    if 'open' in df.columns:
                        df.rename(columns={
                            'open': 'Open',
                            'high': 'High',
                            'low': 'Low',
                            'close': 'Close',
                            'volume': 'Volume'
                        }, inplace=True)
                    logger.info(f"✅ Fetched {len(df)} candles from MetaAPI for {commodity_id}")
                    return df
        
        # Fallback to Libertex if ICMarkets unavailable
        symbol = commodity.get('mt5_libertex_symbol')
        if symbol and 'MT5_LIBERTEX' in _platform_connector.platforms:
            connector = _platform_connector.platforms['MT5_LIBERTEX'].get('connector')
            if connector:
                candles = await connector.get_candles(symbol, timeframe, limit)
                if candles and len(candles) > 0:
                    df = pd.DataFrame(candles)
                    if 'time' in df.columns:
                        df['Date'] = pd.to_datetime(df['time'])
                        df.set_index('Date', inplace=True)
                    if 'open' in df.columns:
                        df.rename(columns={
                            'open': 'Open',
                            'high': 'High',
                            'low': 'Low',
                            'close': 'Close',
                            'volume': 'Volume'
                        }, inplace=True)
                    logger.info(f"✅ Fetched {len(df)} candles from MetaAPI Libertex for {commodity_id}")
                    return df
        
        return None
    except Exception as e:
        logger.warning(f"MetaAPI candles unavailable for {commodity_id}: {e}")
        return None


async def fetch_historical_ohlcv_async(commodity_id: str, timeframe: str = "1d", period: str = "1mo"):
    """
    Fetch historical OHLCV data with timeframe selection (Async version)
    Hybrid approach: MetaAPI (preferred) → yfinance with extended cache
    
    Args:
        commodity_id: Commodity identifier (e.g., 'GOLD', 'WTI_CRUDE')
        timeframe: Interval - '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1wk', '1mo'
        period: Data period - '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'
    
    Returns:
        pandas DataFrame with OHLCV data and indicators
    """
    try:
        if commodity_id not in COMMODITIES:
            logger.error(f"Unknown commodity: {commodity_id}")
            return None
        
        # Check cache first (extended to 24 hours for yfinance data)
        cache_key = f"{commodity_id}_{timeframe}_{period}"
        now = datetime.now()
        
        if cache_key in _ohlcv_cache and cache_key in _cache_expiry:
            if now < _cache_expiry[cache_key]:
                logger.info(f"Returning cached data for {commodity_id}")
                return _ohlcv_cache[cache_key]
        
        commodity = COMMODITIES[commodity_id]
        
        # Priority 1: Try MetaAPI for supported commodities (Gold, Silver, Platinum, WTI, Brent)
        import asyncio
        metaapi_supported = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE"]
        
        if commodity_id in metaapi_supported:
            try:
                # Map period to number of candles
                period_to_limit = {
                    '1d': 24, '5d': 120, '1mo': 720, '3mo': 2160,
                    '6mo': 4320, '1y': 8760, '2y': 17520, '5y': 43800, 'max': 1000
                }
                limit = period_to_limit.get(period, 720)
                
                # Convert timeframe for MetaAPI
                tf_map = {'1d': '1h', '1wk': '4h', '1mo': '1d'}
                metaapi_tf = tf_map.get(timeframe, timeframe)
                
                metaapi_data = await fetch_metaapi_candles(commodity_id, metaapi_tf, limit)
                if metaapi_data is not None and not metaapi_data.empty:
                    # Cache for 1 hour (MetaAPI data is fresh)
                    _ohlcv_cache[cache_key] = metaapi_data
                    _cache_expiry[cache_key] = now + timedelta(hours=1)
                    return metaapi_data
                else:
                    logger.info(f"MetaAPI unavailable for {commodity_id}, falling back to yfinance")
            except Exception as e:
                logger.warning(f"MetaAPI fetch failed for {commodity_id}: {e}, using yfinance")
        
        # Priority 2: yfinance with extended caching (24h)
        ticker = yf.Ticker(commodity["symbol"])
        
        # Timeframe mapping
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '4h', '1d': '1d', '1wk': '1wk', '1mo': '1mo'
        }
        
        # Period validation
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            period = '1mo'
        
        interval = interval_map.get(timeframe, '1d')
        
        # Get historical data with specified timeframe
        logger.info(f"Fetching {commodity['name']} data: period={period}, interval={interval}")
        
        # Add delay to avoid rate limiting
        time.sleep(0.5)
        
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty or len(hist) == 0:
            logger.warning(f"No data received for {commodity['name']}")
            return None
        
        # Add indicators
        hist = calculate_indicators(hist)
        
        # Cache successful result (24 hours for yfinance to avoid rate limiting)
        _ohlcv_cache[cache_key] = hist
        _cache_expiry[cache_key] = now + timedelta(hours=24)
        
        return hist
    except Exception as e:
        logger.error(f"Error fetching historical data for {commodity_id}: {e}")
        # If rate limited, try to return cached data even if expired
        if cache_key in _ohlcv_cache:
            logger.warning(f"Rate limited, returning stale cached data for {commodity_id}")
            return _ohlcv_cache[cache_key]
        return None



def fetch_historical_ohlcv(commodity_id: str, timeframe: str = "1d", period: str = "1mo"):
    """
    Synchronous wrapper for fetch_historical_ohlcv_async
    For backwards compatibility with synchronous code
    """
    import asyncio
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context - return a future
            logger.warning(f"fetch_historical_ohlcv called from async context - use fetch_historical_ohlcv_async instead")
            # Create a new thread to run the async function
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetch_historical_ohlcv_async(commodity_id, timeframe, period))
                return future.result()
        else:
            # We're in a sync context - use asyncio.run
            return asyncio.run(fetch_historical_ohlcv_async(commodity_id, timeframe, period))
    except RuntimeError:
        # No event loop - use asyncio.run
        return asyncio.run(fetch_historical_ohlcv_async(commodity_id, timeframe, period))


def calculate_indicators(df):
    """Calculate technical indicators"""
    try:
        # Safety check
        if df is None or df.empty:
            logger.warning("Cannot calculate indicators on None or empty DataFrame")
            return None
        
        # Check if required column exists
        if 'Close' not in df.columns:
            logger.error("DataFrame missing 'Close' column")
            return None
        
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
        return None  # Return None on error instead of broken df


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


async def calculate_position_size(balance: float, price: float, db, max_risk_percent: float = 20.0, free_margin: float = None, platform: str = "MT5") -> float:
    """Calculate position size ensuring max portfolio risk per platform and considering free margin"""
    try:
        # Get all open positions from database FOR THIS PLATFORM ONLY
        open_trades = await db.trades.find({"status": "OPEN", "mode": platform}).to_list(100)
        
        # Calculate total exposure from open positions ON THIS PLATFORM
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
        
        logger.info(f"[{platform}] Position size: {lot_size} lots (Balance: {balance:.2f}, Free Margin: {free_margin}, Price: {price:.2f}, Exposure: {total_exposure:.2f}/{max_portfolio_value:.2f})")
        
        return lot_size
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.001  # Minimum fallback
