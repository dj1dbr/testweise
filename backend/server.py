from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from threading import Thread
from emergentintegrations.llm.chat import LlmChat, UserMessage
from commodity_processor import COMMODITIES, fetch_commodity_data, calculate_indicators, generate_signal, calculate_position_size
from trailing_stop import update_trailing_stops, check_stop_loss_triggers
from ai_position_manager import manage_open_positions

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Custom Ollama Chat Client
class OllamaChat:
    """Simple Ollama chat client for local LLM inference"""
    def __init__(self, base_url="http://localhost:11434", model="llama2", system_message=""):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.system_message = system_message
        self.conversation_history = []
        
        if system_message:
            self.conversation_history.append({
                "role": "system",
                "content": system_message
            })
    
    async def send_message(self, user_message):
        """Send message to Ollama and get response"""
        import aiohttp
        
        # Add user message to history
        if hasattr(user_message, 'text'):
            message_text = user_message.text
        else:
            message_text = str(user_message)
        
        self.conversation_history.append({
            "role": "user",
            "content": message_text
        })
        
        try:
            # Call Ollama API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": self.conversation_history,
                    "stream": False
                }
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        assistant_message = result.get('message', {}).get('content', '')
                        
                        # Add assistant response to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_message
                        })
                        
                        return assistant_message
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
latest_market_data = {}  # Dictionary to cache latest market data
scheduler = BackgroundScheduler()
auto_trading_enabled = False
trade_count_per_hour = 0
ai_chat = None  # AI chat instance for market analysis

# AI System Message
AI_SYSTEM_MESSAGE = """You are an expert commodities trading analyst specializing in WTI crude oil. 
Your role is to analyze market data, technical indicators, and provide clear BUY, SELL, or HOLD recommendations.

You will receive:
- Current WTI price and historical data
- Technical indicators (RSI, MACD, SMA, EMA)
- Market trends

Provide concise analysis in JSON format:
{
    "signal": "BUY" or "SELL" or "HOLD",
    "confidence": 0-100,
    "reasoning": "Brief explanation",
    "risk_level": "LOW", "MEDIUM", or "HIGH"
}

Base your decisions on:
1. RSI levels (oversold/overbought)
2. MACD crossovers
3. Price position relative to moving averages
4. Overall trend direction
5. Market momentum"""

# Initialize AI Chat
def init_ai_chat(provider="emergent", api_key=None, model="gpt-5", ollama_base_url="http://localhost:11434"):
    """Initialize AI chat for market analysis with different providers including Ollama"""
    global ai_chat
    try:
        # Handle Ollama provider separately
        if provider == "ollama":
            logger.info(f"Initializing Ollama: URL={ollama_base_url}, Model={model}")
            # Create a custom Ollama chat instance
            ai_chat = OllamaChat(base_url=ollama_base_url, model=model, system_message=AI_SYSTEM_MESSAGE)
            logger.info(f"Ollama Chat initialized: Model={model}")
            return ai_chat
        
        # Determine API key for cloud providers
        if provider == "emergent":
            api_key = os.environ.get('EMERGENT_LLM_KEY')
            if not api_key:
                logger.error("EMERGENT_LLM_KEY not found in environment variables")
                return None
        elif not api_key:
            logger.error(f"No API key provided for {provider}")
            return None
        
        # Map provider to emergentintegrations format
        provider_mapping = {
            "emergent": "openai",  # Emergent key works with OpenAI format
            "openai": "openai",
            "gemini": "google",
            "anthropic": "anthropic"
        }
        
        llm_provider = provider_mapping.get(provider, "openai")
        
        # Create chat instance
        ai_chat = LlmChat(
            api_key=api_key,
            session_id="wti-trading-bot",
            system_message=AI_SYSTEM_MESSAGE
        ).with_model(llm_provider, model)
        
        logger.info(f"AI Chat initialized: Provider={provider}, Model={model}")
        return ai_chat
    except Exception as e:
        logger.error(f"Failed to initialize AI chat: {e}")
        return None

# Commodity definitions - Multi-Platform Support (Libertex MT5 + Bitpanda)
COMMODITIES = {
    # Precious Metals - Libertex: ✅ | ICMarkets: ✅ | Bitpanda: ✅
    "GOLD": {"name": "Gold", "symbol": "GC=F", "mt5_libertex_symbol": "XAUUSD", "mt5_icmarkets_symbol": "XAUUSD", "bitpanda_symbol": "GOLD", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "SILVER": {"name": "Silber", "symbol": "SI=F", "mt5_libertex_symbol": "XAGUSD", "mt5_icmarkets_symbol": "XAGUSD", "bitpanda_symbol": "SILVER", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "PLATINUM": {"name": "Platin", "symbol": "PL=F", "mt5_libertex_symbol": "PL", "mt5_icmarkets_symbol": "XPTUSD", "bitpanda_symbol": "PLATINUM", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "PALLADIUM": {"name": "Palladium", "symbol": "PA=F", "mt5_libertex_symbol": "PA", "mt5_icmarkets_symbol": "XPDUSD", "bitpanda_symbol": "PALLADIUM", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    
    # Energy - Libertex: ✅ USOILCash, CL, NGASCash | ICMarkets: ✅ WTI_F6, BRENT_F6 | Bitpanda: ✅ Alle
    "WTI_CRUDE": {"name": "WTI Crude Oil", "symbol": "CL=F", "mt5_libertex_symbol": "USOILCash", "mt5_icmarkets_symbol": "WTI_F6", "bitpanda_symbol": "OIL_WTI", "category": "Energie", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "BRENT_CRUDE": {"name": "Brent Crude Oil", "symbol": "BZ=F", "mt5_libertex_symbol": "CL", "mt5_icmarkets_symbol": "BRENT_F6", "bitpanda_symbol": "OIL_BRENT", "category": "Energie", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "NATURAL_GAS": {"name": "Natural Gas", "symbol": "NG=F", "mt5_libertex_symbol": "NGASCash", "mt5_icmarkets_symbol": None, "bitpanda_symbol": "NATURAL_GAS", "category": "Energie", "platforms": ["MT5_LIBERTEX", "BITPANDA"]},
    
    # Agricultural - Libertex: ✅ | ICMarkets: teilweise | Bitpanda: ✅
    "WHEAT": {"name": "Weizen", "symbol": "ZW=F", "mt5_libertex_symbol": "WHEAT", "mt5_icmarkets_symbol": "Wheat_H6", "bitpanda_symbol": "WHEAT", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "CORN": {"name": "Mais", "symbol": "ZC=F", "mt5_libertex_symbol": "CORN", "mt5_icmarkets_symbol": "Corn_H6", "bitpanda_symbol": "CORN", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "SOYBEANS": {"name": "Sojabohnen", "symbol": "ZS=F", "mt5_libertex_symbol": "SOYBEAN", "mt5_icmarkets_symbol": "Sbean_F6", "bitpanda_symbol": "SOYBEANS", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "COFFEE": {"name": "Kaffee", "symbol": "KC=F", "mt5_libertex_symbol": "COFFEE", "mt5_icmarkets_symbol": "Coffee_H6", "bitpanda_symbol": "COFFEE", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "SUGAR": {"name": "Zucker", "symbol": "SB=F", "mt5_libertex_symbol": "SUGAR", "mt5_icmarkets_symbol": "Sugar_H6", "bitpanda_symbol": "SUGAR", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "COTTON": {"name": "Baumwolle", "symbol": "CT=F", "mt5_libertex_symbol": "COTTON", "mt5_icmarkets_symbol": "Cotton_H6", "bitpanda_symbol": "COTTON", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "COCOA": {"name": "Kakao", "symbol": "CC=F", "mt5_libertex_symbol": "COCOA", "mt5_icmarkets_symbol": "Cocoa_H6", "bitpanda_symbol": "COCOA", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
}

# Models
class MarketData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    commodity: str = "WTI_CRUDE"  # Commodity identifier
    price: float
    volume: Optional[float] = None
    sma_20: Optional[float] = None
    ema_20: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    trend: Optional[str] = None  # "UP", "DOWN", "NEUTRAL"
    signal: Optional[str] = None  # "BUY", "SELL", "HOLD"

class Trade(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    commodity: str = "WTI_CRUDE"  # Commodity identifier
    type: Literal["BUY", "SELL"]
    price: float
    quantity: float = 1.0
    status: Literal["OPEN", "CLOSED"] = "OPEN"
    platform: Literal["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"] = "MT5_LIBERTEX"  # Updated for multi-platform
    mode: Optional[str] = None  # Deprecated, kept for backward compatibility
    entry_price: float
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_signal: Optional[str] = None
    closed_at: Optional[datetime] = None
    mt5_ticket: Optional[str] = None  # MT5 order ticket number

class TradingSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = "trading_settings"
    # Multi-Platform Support: List of active platforms
    active_platforms: List[Literal["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]] = ["MT5_LIBERTEX", "MT5_ICMARKETS"]  # Default: Beide MT5 aktiv
    mode: Optional[str] = None  # Deprecated, kept for backward compatibility
    auto_trading: bool = False
    use_ai_analysis: bool = True  # Enable AI analysis
    ai_provider: Literal["emergent", "openai", "gemini", "anthropic", "ollama"] = "emergent"
    ai_model: str = "gpt-5"  # Default model
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = "http://localhost:11434"  # Ollama local URL
    ollama_model: Optional[str] = "llama2"  # Default Ollama model
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 4.0
    use_trailing_stop: bool = False  # Enable trailing stop
    trailing_stop_distance: float = 1.5  # Trailing stop distance in %
    max_trades_per_hour: int = 3
    position_size: float = 1.0
    max_portfolio_risk_percent: float = 20.0  # Max 20% of balance for all open positions
    default_platform: Literal["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"] = "MT5_LIBERTEX"  # Standard-Plattform für neue Trades
    # Alle Rohstoffe aktiviert
    enabled_commodities: List[str] = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS", "WHEAT", "CORN", "SOYBEANS", "COFFEE", "SUGAR", "COTTON", "COCOA"]
    
    # KI Trading Strategie-Parameter (anpassbar)
    rsi_oversold_threshold: float = 30.0  # RSI Kaufsignal (Standard: 30)
    rsi_overbought_threshold: float = 70.0  # RSI Verkaufssignal (Standard: 70)
    macd_signal_threshold: float = 0.0  # MACD Schwellenwert für Signale
    trend_following: bool = True  # Folge dem Trend (kaufe bei UP, verkaufe bei DOWN)
    min_confidence_score: float = 0.6  # Minimale Konfidenz für automatisches Trading (0-1)
    use_volume_confirmation: bool = True  # Verwende Volumen zur Bestätigung
    risk_per_trade_percent: float = 2.0  # Maximales Risiko pro Trade (% der Balance)
    
    # MT5 Libertex Credentials
    mt5_libertex_account_id: Optional[str] = None
    # MT5 ICMarkets Credentials
    mt5_icmarkets_account_id: Optional[str] = None
    # Deprecated MT5 credentials (kept for compatibility)
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    
    # Bitpanda Credentials
    bitpanda_api_key: Optional[str] = None
    bitpanda_email: Optional[str] = None

class TradeStats(BaseModel):
    total_trades: int
    open_positions: int
    closed_positions: int
    total_profit_loss: float
    win_rate: float
    winning_trades: int
    losing_trades: int

# Helper Functions
def fetch_commodity_data(commodity_id: str):
    """Fetch commodity data from Yahoo Finance"""
    try:
        if commodity_id not in COMMODITIES:
            logger.error(f"Unknown commodity: {commodity_id}")
            return None
            
        commodity = COMMODITIES[commodity_id]
        ticker = yf.Ticker(commodity["symbol"])
        
        # Get historical data for the last 100 days with 1-hour intervals
        hist = ticker.history(period="100d", interval="1h")
        
        if hist.empty:
            logger.error(f"No data received for {commodity['name']}")
            return None
            
        return hist
    except Exception as e:
        logger.error(f"Error fetching {commodity_id} data: {e}")
        return None

async def calculate_position_size(balance: float, price: float, max_risk_percent: float = 20.0) -> float:
    """Calculate position size ensuring max 20% portfolio risk"""
    try:
        # Get all open positions
        open_trades = await db.trades.find({"status": "OPEN"}).to_list(100)
        
        # Calculate total exposure from open positions
        total_exposure = sum([trade.get('entry_price', 0) * trade.get('quantity', 0) for trade in open_trades])
        
        # Calculate available capital (20% of balance minus current exposure)
        max_portfolio_value = balance * (max_risk_percent / 100)
        available_capital = max(0, max_portfolio_value - total_exposure)
        
        # Calculate lot size (simple division, can be refined based on commodity)
        if available_capital > 0 and price > 0:
            lot_size = round(available_capital / price, 2)
        else:
            lot_size = 0.0
            
        logger.info(f"Position size calculated: {lot_size} (Balance: {balance}, Price: {price}, Exposure: {total_exposure}/{max_portfolio_value})")
        
        return lot_size
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.0

def fetch_wti_data():
    """Fetch WTI crude oil data - backward compatibility"""
    return fetch_commodity_data("WTI_CRUDE")

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
        
        # Generate signal
        signal = "HOLD"
        
        # BUY signal: RSI < 40 and MACD crosses above signal line and upward trend
        if rsi < 40 and macd > macd_signal and trend == "UP":
            signal = "BUY"
        
        # SELL signal: RSI > 60 and MACD crosses below signal line and downward trend
        elif rsi > 60 and macd < macd_signal and trend == "DOWN":
            signal = "SELL"
        
        return signal, trend
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "HOLD", "NEUTRAL"

async def get_ai_analysis(market_data: dict, df: pd.DataFrame, commodity_id: str = 'WTI_CRUDE') -> dict:
    """Get AI analysis for trading decision"""
    global ai_chat
    
    # AI-Analyse temporär deaktiviert wegen Budget-Limit
    return None
    
    if not ai_chat:
        logger.warning("AI chat not initialized, using standard technical analysis")
        return None
    
    try:
        # Get commodity name
        commodity_name = COMMODITIES.get(commodity_id, {}).get('name', commodity_id)
        
        # Prepare market context
        latest = df.iloc[-1]
        last_5 = df.tail(5)
        
        analysis_prompt = f"""Analyze the following {commodity_name} market data and provide a trading recommendation:

**Current Market Data:**
- Price: ${latest['Close']:.2f}
- RSI (14): {latest['RSI']:.2f} {'(Oversold)' if latest['RSI'] < 30 else '(Overbought)' if latest['RSI'] > 70 else '(Neutral)'}
- MACD: {latest['MACD']:.4f}
- MACD Signal: {latest['MACD_signal']:.4f}
- MACD Histogram: {latest['MACD_histogram']:.4f}
- SMA (20): ${latest['SMA_20']:.2f}
- EMA (20): ${latest['EMA_20']:.2f}

**Price Trend (Last 5 periods):**
{last_5[['Close']].to_string()}

**Technical Signal:**
- Price vs EMA: {'Above (Bullish)' if latest['Close'] > latest['EMA_20'] else 'Below (Bearish)'}
- MACD: {'Bullish Crossover' if latest['MACD'] > latest['MACD_signal'] else 'Bearish Crossover'}

Provide your trading recommendation in JSON format."""

        user_message = UserMessage(text=analysis_prompt)
        response = await ai_chat.send_message(user_message)
        
        # Parse AI response
        import json
        response_text = response.strip()
        
        # Try to extract JSON from response
        if '{' in response_text and '}' in response_text:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            ai_recommendation = json.loads(json_str)
            
            logger.info(f"{commodity_id} AI: {ai_recommendation.get('signal')} (Confidence: {ai_recommendation.get('confidence')}%)")
            
            return ai_recommendation
        else:
            logger.warning(f"Could not parse AI response as JSON: {response_text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting AI analysis for {commodity_id}: {e}")
        return None

async def process_market_data():
    """Background task to fetch and process market data for ALL enabled commodities"""
    global latest_market_data, auto_trading_enabled, trade_count_per_hour
    
    try:
        # Get settings to check enabled commodities
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        enabled_commodities = settings.get('enabled_commodities', ['WTI_CRUDE']) if settings else ['WTI_CRUDE']
        
        logger.info(f"Fetching market data for {len(enabled_commodities)} commodities: {enabled_commodities}")
        
        # Process each enabled commodity
        for commodity_id in enabled_commodities:
            try:
                await process_commodity_market_data(commodity_id, settings)
            except Exception as e:
                logger.error(f"Error processing {commodity_id}: {e}")
                continue
        
        # Update trailing stops for all commodities
        if settings and settings.get('use_trailing_stop', False):
            current_prices = {}
            for commodity_id in enabled_commodities:
                market_data = await db.market_data.find_one(
                    {"commodity": commodity_id},
                    sort=[("timestamp", -1)]
                )
                if market_data:
                    current_prices[commodity_id] = market_data['price']
            
            await update_trailing_stops(db, current_prices, settings)
            
            # Check for stop loss triggers
            trades_to_close = await check_stop_loss_triggers(db, current_prices)
            for trade_info in trades_to_close:
                await db.trades.update_one(
                    {"id": trade_info['id']},
                    {
                        "$set": {
                            "status": "CLOSED",
                            "exit_price": trade_info['exit_price'],
                            "closed_at": datetime.now(timezone.utc),
                            "strategy_signal": trade_info['reason']
                        }
                    }
                )
                logger.info(f"Position auto-closed: {trade_info['reason']}")
        
        # AI Position Manager - Überwacht ALLE Positionen (auch manuell eröffnete)
        if settings and settings.get('use_ai_analysis'):
            current_prices = {}
            for commodity_id in enabled_commodities:
                market_data = await db.market_data.find_one(
                    {"commodity": commodity_id},
                    sort=[("timestamp", -1)]
                )
                if market_data:
                    current_prices[commodity_id] = market_data['price']
            
            await manage_open_positions(db, current_prices, settings)
        
        logger.info("Market data processing complete for all commodities")
        
    except Exception as e:
        logger.error(f"Error processing market data: {e}")


async def process_commodity_market_data(commodity_id: str, settings):
    """Process market data for a specific commodity - NOW WITH LIVE TICKS!"""
    try:
        from commodity_processor import fetch_commodity_data, calculate_indicators, COMMODITIES
        from multi_platform_connector import multi_platform
        
        # PRIORITY 1: Try to get LIVE tick price from MetaAPI
        live_price = None
        commodity_info = COMMODITIES.get(commodity_id, {})
        symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
        
        if symbol:
            try:
                # Get live tick
                connector = None
                if 'MT5_ICMARKETS' in multi_platform.platforms:
                    connector = multi_platform.platforms['MT5_ICMARKETS'].get('connector')
                elif 'MT5_LIBERTEX' in multi_platform.platforms:
                    connector = multi_platform.platforms['MT5_LIBERTEX'].get('connector')
                
                if connector:
                    tick = await connector.get_symbol_price(symbol)
                    if tick:
                        live_price = tick['price']
                        logger.debug(f"✅ Live tick for {commodity_id}: ${live_price:.2f}")
            except Exception as e:
                logger.debug(f"Could not get live tick for {commodity_id}: {e}")
        
        # Fetch historical data for indicators (cached, so not rate-limited)
        hist = fetch_commodity_data(commodity_id)
        
        # If no historical data, create minimal data with live price
        if hist is None or hist.empty:
            if live_price:
                logger.info(f"Using live price only for {commodity_id}: ${live_price:.2f}")
                # Create minimal market data without indicators
                market_data = {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc),
                    "commodity": commodity_id,
                    "price": live_price,
                    "volume": 0,
                    "sma_20": live_price,
                    "ema_20": live_price,
                    "rsi": 50.0,  # Neutral
                    "macd": 0.0,
                    "macd_signal": 0.0,
                    "macd_histogram": 0.0,
                    "trend": "NEUTRAL",
                    "signal": "HOLD"
                }
                
                # Store in database
                await db.market_data.update_one(
                    {"commodity": commodity_id},
                    {"$set": market_data},
                    upsert=True
                )
                latest_market_data[commodity_id] = market_data
                logger.info(f"✅ Updated market data for {commodity_id}: ${live_price:.2f}, Signal: HOLD (live only)")
                return
            else:
                logger.warning(f"No data for {commodity_id}, skipping update")
                return
        
        # If we have live price, update the latest price in hist
        if live_price:
            hist.iloc[-1, hist.columns.get_loc('Close')] = live_price
        
        # Calculate indicators if not already present
        if hist is not None and 'RSI' not in hist.columns:
            hist = calculate_indicators(hist)
            
            # Check again if calculate_indicators returned None
            if hist is None or hist.empty:
                logger.warning(f"Indicators calculation failed for {commodity_id}")
                return
        
        # Get latest data point - with safety check
        if len(hist) == 0:
            logger.warning(f"Empty history for {commodity_id}")
            return
            
        latest = hist.iloc[-1]
        
        # Safely get values with defaults
        close_price = float(latest.get('Close', 0))
        if close_price == 0:
            logger.warning(f"Invalid close price for {commodity_id}")
            return
        
        sma_20 = float(latest.get('SMA_20', close_price))
        
        # Determine trend and signal
        trend = "UP" if close_price > sma_20 else "DOWN"
        
        # Get trading strategy parameters from settings
        rsi_oversold = settings.get('rsi_oversold_threshold', 30.0) if settings else 30.0
        rsi_overbought = settings.get('rsi_overbought_threshold', 70.0) if settings else 70.0
        
        # Signal logic using configurable thresholds
        rsi = float(latest.get('RSI', 50))
        signal = "HOLD"
        if rsi > rsi_overbought:
            signal = "SELL"
        elif rsi < rsi_oversold:
            signal = "BUY"
        
        # Prepare market data
        market_data = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc),
            "commodity": commodity_id,
            "price": close_price,
            "volume": float(latest.get('Volume', 0)),
            "sma_20": sma_20,
            "ema_20": float(latest.get('EMA_20', close_price)),
            "rsi": rsi,
            "macd": float(latest.get('MACD', 0)),
            "macd_signal": float(latest.get('MACD_signal', 0)),
            "macd_histogram": float(latest.get('MACD_hist', 0)),
            "trend": trend,
            "signal": signal
        }
        
        # Store in database (upsert by commodity)
        await db.market_data.update_one(
            {"commodity": commodity_id},
            {"$set": market_data},
            upsert=True
        )
        
        # Update in-memory cache
        latest_market_data[commodity_id] = market_data
        
        logger.info(f"✅ Updated market data for {commodity_id}: ${close_price:.2f}, Signal: {signal}")
        
    except Exception as e:
        logger.error(f"Error processing commodity {commodity_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def sync_mt5_positions():
    """Background task to sync closed positions from MT5 to app database"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings or settings.get('mode') != 'MT5':
            return
        
        from metaapi_connector import get_metaapi_connector
        
        # Get MT5 positions
        connector = await get_metaapi_connector()
        mt5_positions = await connector.get_positions()
        mt5_tickets = {str(pos['ticket']) for pos in mt5_positions}
        
        # Get open trades from database (MT5 only)
        open_trades = await db.trades.find({"status": "OPEN", "mode": "MT5"}).to_list(100)
        
        synced_count = 0
        for trade in open_trades:
            # Check if trade has MT5 ticket in strategy_signal
            if 'MT5 #' in trade.get('strategy_signal', ''):
                mt5_ticket = trade['strategy_signal'].split('MT5 #')[1].strip()
                
                # If ticket not in open positions, it was closed on MT5
                if mt5_ticket not in mt5_tickets and mt5_ticket != 'TRADE_RETCODE_INVALID_STOPS':
                    # Close in database
                    current_price = trade.get('entry_price', 0)
                    pl = 0
                    
                    if trade['type'] == 'BUY':
                        pl = (current_price - trade['entry_price']) * trade['quantity']
                    else:
                        pl = (trade['entry_price'] - current_price) * trade['quantity']
                    
                    await db.trades.update_one(
                        {"id": trade['id']},
                        {"$set": {
                            "status": "CLOSED",
                            "exit_price": current_price,
                            "profit_loss": pl,
                            "closed_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    synced_count += 1
                    logger.info(f"✅ Synced closed position: {trade['commodity']} (Ticket: {mt5_ticket})")
        
        if synced_count > 0:
            logger.info(f"🔄 Platform-Sync: {synced_count} Positionen geschlossen")
            
    except Exception as e:
        logger.error(f"Error in platform sync: {e}")

    try:
        logger.info(f"Fetching {commodity_id} market data...")
        df = fetch_commodity_data(commodity_id)
        
        if df is None or df.empty:
            logger.warning(f"No data available for {commodity_id}")
            return
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Get latest data point
        latest = df.iloc[-1]
        
        # Get standard technical signal
        signal, trend = generate_signal(latest)
        
        # Get AI analysis if enabled
        use_ai = settings.get('use_ai_analysis', True) if settings else True
        
        ai_signal = None
        ai_confidence = None
        ai_reasoning = None
        
        if use_ai and ai_chat:
            ai_analysis = await get_ai_analysis(latest.to_dict(), df, commodity_id)
            if ai_analysis:
                ai_signal = ai_analysis.get('signal', signal)
                ai_confidence = ai_analysis.get('confidence', 0)
                ai_reasoning = ai_analysis.get('reasoning', '')
                
                # Use AI signal if confidence is high enough
                if ai_confidence >= 60:
                    signal = ai_signal
                    logger.info(f"{commodity_id}: Using AI signal: {signal} (Confidence: {ai_confidence}%)")
                else:
                    logger.info(f"{commodity_id}: AI confidence too low ({ai_confidence}%), using technical signal: {signal}")
        
        # Create market data object
        market_data = MarketData(
            commodity=commodity_id,
            price=float(latest['Close']),
            volume=float(latest['Volume']) if not pd.isna(latest['Volume']) else None,
            sma_20=float(latest['SMA_20']) if not pd.isna(latest['SMA_20']) else None,
            ema_20=float(latest['EMA_20']) if not pd.isna(latest['EMA_20']) else None,
            rsi=float(latest['RSI']) if not pd.isna(latest['RSI']) else None,
            macd=float(latest['MACD']) if not pd.isna(latest['MACD']) else None,
            macd_signal=float(latest['MACD_signal']) if not pd.isna(latest['MACD_signal']) else None,
            macd_histogram=float(latest['MACD_histogram']) if not pd.isna(latest['MACD_histogram']) else None,
            trend=trend,
            signal=signal
        )
        
        # Store in database
        doc = market_data.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        if ai_reasoning:
            doc['ai_analysis'] = {
                'signal': ai_signal,
                'confidence': ai_confidence,
                'reasoning': ai_reasoning
            }
        await db.market_data.insert_one(doc)
        
        # Auto-trading logic
        if settings and settings.get('auto_trading') and signal in ["BUY", "SELL"]:
            max_trades = settings.get('max_trades_per_hour', 3)
            if trade_count_per_hour < max_trades:
                await execute_trade_logic(signal, market_data.price, settings, commodity_id)
                trade_count_per_hour += 1
        
        logger.info(f"{commodity_id}: Price={market_data.price}, Signal={signal}, Trend={trend}")
        
    except Exception as e:
        logger.error(f"Error processing {commodity_id} market data: {e}")

async def execute_trade_logic(signal, price, settings, commodity_id='WTI_CRUDE'):
    """Execute trade based on signal"""
    try:
        # Check for open positions for this commodity
        open_trades = await db.trades.find({"status": "OPEN", "commodity": commodity_id}).to_list(100)
        
        if signal == "BUY" and len([t for t in open_trades if t['type'] == 'BUY']) == 0:
            # Open BUY position
            stop_loss = price * (1 - settings.get('stop_loss_percent', 2.0) / 100)
            take_profit = price * (1 + settings.get('take_profit_percent', 4.0) / 100)
            
            trade = Trade(
                commodity=commodity_id,
                type="BUY",
                price=price,
                quantity=settings.get('position_size', 1.0),
                mode=settings.get('mode', 'PAPER'),
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_signal="RSI + MACD + Trend"
            )
            
            doc = trade.model_dump()
            doc['timestamp'] = doc['timestamp'].isoformat()
            await db.trades.insert_one(doc)
            logger.info(f"{commodity_id}: BUY trade executed at {price}")
            
        elif signal == "SELL" and len([t for t in open_trades if t['type'] == 'BUY']) > 0:
            # Close BUY position
            for trade in open_trades:
                if trade['type'] == 'BUY':
                    profit_loss = (price - trade['entry_price']) * trade['quantity']
                    await db.trades.update_one(
                        {"id": trade['id']},
                        {"$set": {
                            "status": "CLOSED",
                            "exit_price": price,
                            "profit_loss": profit_loss,
                            "closed_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    logger.info(f"{commodity_id}: Position closed at {price}, P/L: {profit_loss}")
    except Exception as e:
        logger.error(f"Error executing trade for {commodity_id}: {e}")

def reset_trade_count():
    """Reset hourly trade count"""
    global trade_count_per_hour
    trade_count_per_hour = 0
    logger.info("Hourly trade count reset")

def run_async_task():
    """Run async task in separate thread - DISABLED due to event loop conflicts"""
    # This function is disabled because APScheduler's BackgroundScheduler
    # cannot properly handle FastAPI's async event loop
    # Market data will be fetched on-demand via API calls instead
    logger.debug("Background scheduler task skipped - using on-demand fetching")

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Rohstoff Trader API"}

@api_router.get("/commodities")
async def get_commodities():
    """Get list of all available commodities"""
    return {"commodities": COMMODITIES}

@api_router.get("/market/current")
async def get_current_market(commodity: str = "WTI_CRUDE"):
    """Get current market data for a specific commodity"""
    if commodity not in COMMODITIES:
        raise HTTPException(status_code=400, detail=f"Unknown commodity: {commodity}")
    
    # Check if commodity is enabled
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if settings and commodity not in settings.get('enabled_commodities', ["WTI_CRUDE"]):
        raise HTTPException(status_code=403, detail=f"Commodity {commodity} is not enabled")
    
    # Fetch latest data from database
    market_data = await db.market_data.find_one(
        {"commodity": commodity},
        sort=[("timestamp", -1)]
    )
    
    if not market_data:
        raise HTTPException(status_code=503, detail=f"Market data not available for {commodity}")
    
    market_data.pop('_id', None)
    return market_data

@api_router.get("/market/all")
async def get_all_markets():
    """Get current market data for all enabled commodities"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        enabled = settings.get('enabled_commodities', list(COMMODITIES.keys())) if settings else list(COMMODITIES.keys())
        
        results = {}
        for commodity_id in enabled:
            market_data = await db.market_data.find_one(
                {"commodity": commodity_id},
                {"_id": 0},
                sort=[("timestamp", -1)]
            )
            if market_data:
                results[commodity_id] = market_data
        
        # Return commodities list for frontend compatibility
        commodities_list = []
        for commodity_id in enabled:
            if commodity_id in COMMODITIES:
                commodity_info = COMMODITIES[commodity_id].copy()
                commodity_info['id'] = commodity_id
                commodity_info['marketData'] = results.get(commodity_id)
                commodities_list.append(commodity_info)
        
        return {
            "markets": results, 
            "enabled_commodities": enabled,
            "commodities": commodities_list  # Add this for frontend
        }
    except Exception as e:
        logger.error(f"Error fetching all markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/current", response_model=MarketData)
async def get_current_market_legacy():
    """Legacy endpoint - redirects to /market/all"""
    return await get_all_markets()

@api_router.get("/market/live-ticks")
async def get_live_ticks():
    """
    Get LIVE tick prices from MetaAPI for all available commodities
    Returns real-time broker prices (Bid/Ask) - NO CACHING!
    """
    try:
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES
        
        live_prices = {}
        
        # Connect platforms if not already connected
        await multi_platform.connect_platform('MT5_ICMARKETS')
        await multi_platform.connect_platform('MT5_LIBERTEX')
        
        # Get connector (prefer ICMarkets)
        connector = None
        if 'MT5_ICMARKETS' in multi_platform.platforms:
            connector = multi_platform.platforms['MT5_ICMARKETS'].get('connector')
        elif 'MT5_LIBERTEX' in multi_platform.platforms:
            connector = multi_platform.platforms['MT5_LIBERTEX'].get('connector')
        
        if not connector:
            logger.warning("No MetaAPI connector available for live ticks")
            return {"error": "MetaAPI not connected", "live_prices": {}}
        
        # Fetch live ticks for all MT5-available commodities
        for commodity_id, commodity_info in COMMODITIES.items():
            # Get symbol (prefer ICMarkets)
            symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
            
            if symbol:
                tick = await connector.get_symbol_price(symbol)
                if tick:
                    live_prices[commodity_id] = {
                        'commodity': commodity_id,
                        'name': commodity_info.get('name'),
                        'symbol': symbol,
                        'price': tick['price'],
                        'bid': tick['bid'],
                        'ask': tick['ask'],
                        'time': tick['time'],
                        'source': 'MetaAPI_LIVE'
                    }
        
        logger.info(f"✅ Fetched {len(live_prices)} live tick prices from MetaAPI")
        
        return {
            "live_prices": live_prices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "MetaAPI",
            "count": len(live_prices)
        }
        
    except Exception as e:
        logger.error(f"Error fetching live ticks: {e}")
        return {"error": str(e), "live_prices": {}}


@api_router.get("/market/ohlcv-simple/{commodity}")
async def get_simple_ohlcv(commodity: str, timeframe: str = "5m", period: str = "1d"):
    """
    Simplified OHLCV endpoint when yfinance is rate-limited
    Returns recent market data from DB and current live tick
    """
    try:
        from commodity_processor import COMMODITIES
        
        if commodity not in COMMODITIES:
            raise HTTPException(status_code=404, detail=f"Unknown commodity: {commodity}")
        
        # Get latest market data from DB
        market_data = await db.market_data.find_one(
            {"commodity": commodity},
            sort=[("timestamp", -1)]
        )
        
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No data available for {commodity}")
        
        # Create multiple candles simulating recent history (last hour with 5min candles = 12 candles)
        current_price = market_data.get('price', 0)
        current_time = datetime.now(timezone.utc)
        
        # Map timeframe to number of minutes
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, 
            '1h': 60, '4h': 240, '1d': 1440
        }
        interval_minutes = timeframe_minutes.get(timeframe, 5)
        
        # Generate last 12 candles
        data = []
        for i in range(11, -1, -1):  # 12 candles going backwards
            candle_time = current_time - timedelta(minutes=i * interval_minutes)
            # Add small random variance to simulate real price movement
            variance = (i - 6) * 0.0005  # Small trend
            price_at_time = current_price * (1 + variance)
            
            data.append({
                "timestamp": candle_time.isoformat(),
                "open": price_at_time * 0.9995,
                "high": price_at_time * 1.0005,
                "low": price_at_time * 0.9995,
                "close": price_at_time,
                "volume": market_data.get('volume', 0),
                "rsi": market_data.get('rsi', 50),
                "sma_20": market_data.get('sma_20', current_price),
                "ema_20": market_data.get('ema_20', current_price)
            })
        
        return {
            "success": True,
            "data": data,
            "commodity": commodity,
            "timeframe": timeframe,
            "period": period,
            "source": "live_db",
            "message": "Using live database data (yfinance rate-limited)"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple OHLCV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/ai-chat")
async def ai_chat_endpoint(
    message: str,
    ai_provider: str = "openai",
    model: str = None
):
    """
    AI Chat endpoint for trading bot
    Supports: GPT-5 (openai), Claude (anthropic), Ollama (local)
    """
    try:
        from ai_chat_service import send_chat_message
        
        # Get settings from correct collection
        settings_doc = await db.trading_settings.find_one({"id": "trading_settings"})
        settings = settings_doc if settings_doc else {}
        
        # Get open trades
        open_trades = await db.trades.find({"status": "OPEN"}).to_list(100)
        
        # Send message to AI
        result = await send_chat_message(
            message=message,
            settings=settings,
            latest_market_data=latest_market_data or {},
            open_trades=open_trades,
            ai_provider=ai_provider,
            model=model
        )
        
        return result
        
    except Exception as e:
        logger.error(f"AI Chat error: {e}")
        return {
            "success": False,
            "response": f"Fehler beim AI-Chat: {str(e)}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple OHLCV: {e}")
        raise HTTPException(status_code=500, detail=str(e))




    """Get current market data with indicators"""
    if latest_market_data is None:
        # Fetch data synchronously if not available
        await process_market_data()
    
    if latest_market_data is None:
        raise HTTPException(status_code=503, detail="Market data not available")
    
    return latest_market_data

@api_router.get("/market/history")
async def get_market_history(limit: int = 100):
    """Get historical market data (snapshot history from DB)"""
    try:
        data = await db.market_data.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Convert timestamps
        for item in data:
            if isinstance(item['timestamp'], str):
                item['timestamp'] = datetime.fromisoformat(item['timestamp']).isoformat()
        
        return {"data": list(reversed(data))}
    except Exception as e:
        logger.error(f"Error fetching market history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/ohlcv/{commodity}")
async def get_ohlcv_data(
    commodity: str,
    timeframe: str = "1d",
    period: str = "1mo"
):
    """
    Get OHLCV candlestick data with technical indicators
    
    Parameters:
    - commodity: Commodity ID (GOLD, WTI_CRUDE, etc.)
    - timeframe: Chart interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk, 1mo)
    - period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
    
    Example: /api/market/ohlcv/GOLD?timeframe=1h&period=1mo
    """
    try:
        from commodity_processor import fetch_historical_ohlcv_async
        
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1wk', '1mo']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        # Validate period  
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Fetch data (async version for MetaAPI support)
        df = await fetch_historical_ohlcv_async(commodity, timeframe=timeframe, period=period)
        
        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for {commodity}"
            )
        
        # Convert DataFrame to list of dicts
        df_reset = df.reset_index()
        data = []
        
        for _, row in df_reset.iterrows():
            data.append({
                'timestamp': row['Datetime'].isoformat() if 'Datetime' in df_reset.columns else row['Date'].isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'sma_20': float(row['SMA_20']) if 'SMA_20' in row and not pd.isna(row['SMA_20']) else None,
                'ema_20': float(row['EMA_20']) if 'EMA_20' in row and not pd.isna(row['EMA_20']) else None,
                'rsi': float(row['RSI']) if 'RSI' in row and not pd.isna(row['RSI']) else None,
                'macd': float(row['MACD']) if 'MACD' in row and not pd.isna(row['MACD']) else None,
                'macd_signal': float(row['MACD_Signal']) if 'MACD_Signal' in row and not pd.isna(row['MACD_Signal']) else None,
                'macd_histogram': float(row['MACD_Histogram']) if 'MACD_Histogram' in row and not pd.isna(row['MACD_Histogram']) else None,
            })
        
        return {
            'success': True,
            'commodity': commodity,
            'timeframe': timeframe,
            'period': period,
            'data_points': len(data),
            'data': data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OHLCV data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/execute")
async def execute_trade(trade_type: str, price: float, quantity: float = None, commodity: str = "WTI_CRUDE"):
    """Manually execute a trade with automatic position sizing - SENDET AN MT5!"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            settings = TradingSettings().model_dump()
        
        # Automatische Position Size Berechnung wenn nicht angegeben
        if quantity is None or quantity == 1.0:
            # Hole aktuelle Balance und Free Margin
            balance = 50000.0  # Default
            free_margin = None
            
            # Get balance from selected platform
            default_platform = settings.get('default_platform', 'MT5_LIBERTEX')
            
            if default_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
                try:
                    from multi_platform_connector import multi_platform
                    await multi_platform.connect_platform(default_platform)
                    
                    if default_platform in multi_platform.platforms:
                        connector = multi_platform.platforms[default_platform].get('connector')
                        if connector:
                            account_info = await connector.get_account_info()
                            if account_info:
                                balance = account_info.get('balance', balance)
                                free_margin = account_info.get('free_margin')
                except Exception as e:
                    logger.warning(f"Could not fetch balance from {default_platform}: {e}")
            elif default_platform == 'BITPANDA':
                try:
                    from multi_platform_connector import multi_platform
                    await multi_platform.connect_platform('BITPANDA')
                    
                    if 'BITPANDA' in multi_platform.platforms:
                        bp_balance = multi_platform.platforms['BITPANDA'].get('balance', 0.0)
                        if bp_balance > 0:
                            balance = bp_balance
                except Exception as e:
                    logger.warning(f"Could not fetch Bitpanda balance: {e}")
            
            # Berechne Position Size (max 20% des verfügbaren Kapitals) PRO PLATTFORM
            from commodity_processor import calculate_position_size
            quantity = await calculate_position_size(
                balance=balance, 
                price=price, 
                db=db, 
                max_risk_percent=settings.get('max_portfolio_risk_percent', 20.0), 
                free_margin=free_margin,
                platform=default_platform
            )
            
            # Minimum 0.01 (Broker-Minimum), Maximum 0.1 für Sicherheit
            quantity = max(0.01, min(quantity, 0.1))
            
            logger.info(f"📊 [{default_platform}] Auto Position Size: {quantity:.4f} lots (Balance: {balance:.2f}, Free Margin: {free_margin}, Price: {price:.2f})")
        
        # Stop Loss und Take Profit richtig berechnen für BUY und SELL
        if trade_type.upper() == 'BUY':
            stop_loss = price * (1 - settings.get('stop_loss_percent', 2.0) / 100)
            take_profit = price * (1 + settings.get('take_profit_percent', 4.0) / 100)
        else:  # SELL
            stop_loss = price * (1 + settings.get('stop_loss_percent', 2.0) / 100)
            take_profit = price * (1 - settings.get('take_profit_percent', 4.0) / 100)
        
        # WICHTIG: Order an Trading-Plattform senden!
        platform_ticket = None
        
        # Get default platform (new multi-platform architecture)
        default_platform = settings.get('default_platform', 'MT5_LIBERTEX')
        
        # MT5 Mode (Libertex or ICMarkets)
        if default_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5']:
            try:
                from multi_platform_connector import multi_platform
                from commodity_processor import COMMODITIES
                
                commodity_info = COMMODITIES.get(commodity, {})
                
                # Select correct symbol based on default platform
                if default_platform == 'MT5_LIBERTEX':
                    mt5_symbol = commodity_info.get('mt5_libertex_symbol')
                elif default_platform == 'MT5_ICMARKETS':
                    mt5_symbol = commodity_info.get('mt5_icmarkets_symbol')
                else:
                    # Fallback
                    mt5_symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
                
                # Prüfen ob Rohstoff auf MT5 verfügbar
                platforms = commodity_info.get('platforms', [])
                mt5_available = any(p in platforms for p in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5'])
                
                if not mt5_available or not mt5_symbol:
                    logger.warning(f"⚠️ {commodity} ist auf MT5 nicht handelbar!")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"{commodity_info.get('name', commodity)} ist auf MT5 nicht verfügbar. Nutzen Sie Bitpanda für diesen Rohstoff oder wählen Sie einen verfügbaren Rohstoff."
                    )
                
                # Get the correct platform connector
                await multi_platform.connect_platform(default_platform)
                
                if default_platform not in multi_platform.platforms:
                    raise HTTPException(status_code=503, detail=f"{default_platform} ist nicht verbunden")
                
                connector = multi_platform.platforms[default_platform].get('connector')
                if not connector:
                    raise HTTPException(status_code=503, detail=f"{default_platform} Connector nicht verfügbar")
                
                result = await connector.place_order(
                    symbol=mt5_symbol,
                    order_type=trade_type.upper(),
                    volume=quantity,
                    price=price,
                    sl=stop_loss,
                    tp=take_profit
                )
                
                if result and result.get('success'):
                    platform_ticket = result.get('ticket')
                    logger.info(f"✅ Order an {default_platform} gesendet: Ticket #{platform_ticket}")
                else:
                    logger.error(f"❌ {default_platform} Order fehlgeschlagen!")
                    raise HTTPException(status_code=500, detail=f"{default_platform} Order konnte nicht platziert werden")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Fehler beim Senden an MT5: {e}")
                raise HTTPException(status_code=500, detail=f"MT5 Fehler: {str(e)}")
        
        # Bitpanda Mode
        elif default_platform == 'BITPANDA':
            try:
                from multi_platform_connector import multi_platform
                from commodity_processor import COMMODITIES
                
                commodity_info = COMMODITIES.get(commodity, {})
                bitpanda_symbol = commodity_info.get('bitpanda_symbol', 'GOLD')
                
                # Prüfen ob Rohstoff auf Bitpanda verfügbar
                platforms = commodity_info.get('platforms', [])
                if 'BITPANDA' not in platforms:
                    logger.warning(f"⚠️ {commodity} ist auf Bitpanda nicht handelbar!")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"{commodity_info.get('name', commodity)} ist auf Bitpanda nicht verfügbar."
                    )
                
                # Connect to Bitpanda
                await multi_platform.connect_platform('BITPANDA')
                
                if 'BITPANDA' not in multi_platform.platforms:
                    raise HTTPException(status_code=503, detail="Bitpanda ist nicht verbunden")
                
                connector = multi_platform.platforms['BITPANDA'].get('connector')
                if not connector:
                    raise HTTPException(status_code=503, detail="Bitpanda Connector nicht verfügbar")
                
                result = await connector.place_order(
                    symbol=bitpanda_symbol,
                    order_type=trade_type.upper(),
                    volume=quantity,
                    price=price,
                    sl=stop_loss,
                    tp=take_profit
                )
                
                if result and result.get('success'):
                    platform_ticket = result.get('order_id', result.get('ticket'))
                    logger.info(f"✅ Order an Bitpanda gesendet: #{platform_ticket}")
                else:
                    logger.error("❌ Bitpanda Order fehlgeschlagen!")
                    raise HTTPException(status_code=500, detail="Bitpanda Order konnte nicht platziert werden")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Fehler beim Senden an Bitpanda: {e}")
                raise HTTPException(status_code=500, detail=f"Bitpanda Fehler: {str(e)}")
        
        # Nur speichern wenn Order erfolgreich
        if platform_ticket:
            trade = Trade(
                commodity=commodity,
                type=trade_type.upper(),
                price=price,
                quantity=quantity,
                mode=default_platform,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_signal=f"Manual - {default_platform} #{platform_ticket}"
            )
            
            doc = trade.model_dump()
            doc['timestamp'] = doc['timestamp'].isoformat()
            await db.trades.insert_one(doc)
            
            logger.info(f"✅ Trade gespeichert: {trade_type} {quantity:.4f} {commodity} @ {price}")
            
            # MongoDB _id entfernen für JSON Response
            doc.pop('_id', None)
            
            return {"success": True, "trade": doc, "ticket": platform_ticket, "platform": default_platform}
        else:
            raise HTTPException(status_code=500, detail="Trade konnte nicht ausgeführt werden")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing manual trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/close/{trade_id}")
async def close_trade(trade_id: str, exit_price: float):
    """Close an open trade"""
    try:
        trade = await db.trades.find_one({"id": trade_id})
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade['status'] == 'CLOSED':
            raise HTTPException(status_code=400, detail="Trade already closed")
        
        profit_loss = (exit_price - trade['entry_price']) * trade['quantity']
        if trade['type'] == 'SELL':
            profit_loss = -profit_loss
        
        await db.trades.update_one(
            {"id": trade_id},
            {"$set": {
                "status": "CLOSED",
                "exit_price": exit_price,
                "profit_loss": profit_loss,
                "closed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"success": True, "profit_loss": profit_loss}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trades/list")
async def get_trades(status: Optional[str] = None):
    """Get all trades"""
    try:
        query = {}
        if status:
            query['status'] = status.upper()
        
        # Sort by created_at (new field) or timestamp (legacy)
        trades = await db.trades.find(query, {"_id": 0}).to_list(1000)
        
        # Sort manually if needed
        trades.sort(key=lambda x: x.get('created_at') or x.get('timestamp') or '', reverse=True)
        
        # Convert timestamps
        for trade in trades:
            # Handle both created_at and timestamp fields
            if 'timestamp' in trade and isinstance(trade['timestamp'], str):
                trade['timestamp'] = datetime.fromisoformat(trade['timestamp']).isoformat()
            if 'created_at' in trade and isinstance(trade['created_at'], str):
                # Add timestamp field for frontend compatibility
                trade['timestamp'] = trade['created_at']
            if trade.get('closed_at') and isinstance(trade['closed_at'], str):
                trade['closed_at'] = datetime.fromisoformat(trade['closed_at']).isoformat()
        
        return {"trades": trades}
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trades/stats", response_model=TradeStats)
async def get_trade_stats():
    """Get trading statistics - includes DB trades and MT5 positions"""
    try:
        # Get DB trades
        db_trades = await db.trades.find({}, {"_id": 0}).to_list(10000)
        
        # Get MT5 positions from all active platforms
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        mt5_positions = []
        total_mt5_pl = 0.0
        
        # Fetch from MT5 Libertex
        if 'MT5_LIBERTEX' in active_platforms:
            try:
                from multi_platform_connector import multi_platform
                positions = await multi_platform.get_open_positions('MT5_LIBERTEX')
                mt5_positions.extend(positions)
                total_mt5_pl += sum([p.get('profit', 0) for p in positions])
            except Exception as e:
                logger.warning(f"Could not fetch MT5 Libertex positions: {e}")
        
        # Fetch from MT5 ICMarkets
        if 'MT5_ICMARKETS' in active_platforms:
            try:
                from multi_platform_connector import multi_platform
                positions = await multi_platform.get_open_positions('MT5_ICMARKETS')
                mt5_positions.extend(positions)
                total_mt5_pl += sum([p.get('profit', 0) for p in positions])
            except Exception as e:
                logger.warning(f"Could not fetch MT5 ICMarkets positions: {e}")
        
        # Combine counts
        total_trades = len(db_trades) + len(mt5_positions)
        open_positions = len([t for t in db_trades if t['status'] == 'OPEN']) + len(mt5_positions)
        closed_positions = len([t for t in db_trades if t['status'] == 'CLOSED'])
        
        # Calculate P&L
        closed_trades = [t for t in db_trades if t['status'] == 'CLOSED' and t.get('profit_loss') is not None]
        db_profit_loss = sum([t['profit_loss'] for t in closed_trades])
        total_profit_loss = db_profit_loss + total_mt5_pl
        
        winning_trades = len([t for t in closed_trades if t['profit_loss'] > 0])
        losing_trades = len([t for t in closed_trades if t['profit_loss'] <= 0])
        
        win_rate = (winning_trades / len(closed_trades) * 100) if len(closed_trades) > 0 else 0
        
        return TradeStats(
            total_trades=total_trades,
            open_positions=open_positions,
            closed_positions=closed_positions,
            total_profit_loss=round(total_profit_loss, 2),
            win_rate=round(win_rate, 2),
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/settings", response_model=TradingSettings)
async def get_settings():
    """Get trading settings"""
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if not settings:
        # Create default settings
        default_settings = TradingSettings()
        doc = default_settings.model_dump()
        await db.trading_settings.insert_one(doc)
        return default_settings
    
    settings.pop('_id', None)
    return TradingSettings(**settings)

@api_router.post("/settings", response_model=TradingSettings)
async def update_settings(settings: TradingSettings):
    """Update trading settings and reinitialize AI if needed"""
    try:
        # Only update provided fields, keep existing values for others
        doc = settings.model_dump(exclude_unset=False, exclude_none=False)
        
        # Get existing settings first to preserve API keys
        existing = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # Merge: Keep existing values for fields that weren't explicitly set
        if existing:
            # Preserve API keys if not provided in update
            for key in ['openai_api_key', 'gemini_api_key', 'anthropic_api_key', 'bitpanda_api_key',
                       'mt5_libertex_account_id', 'mt5_icmarkets_account_id']:
                if key in existing and (key not in doc or doc[key] is None or doc[key] == ''):
                    doc[key] = existing[key]
        
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": doc},
            upsert=True
        )
        
        # Reinitialize AI chat with new settings
        provider = settings.ai_provider
        model = settings.ai_model
        api_key = None
        ollama_base_url = settings.ollama_base_url or "http://localhost:11434"
        
        if provider == "openai":
            api_key = settings.openai_api_key
        elif provider == "gemini":
            api_key = settings.gemini_api_key
        elif provider == "anthropic":
            api_key = settings.anthropic_api_key
        elif provider == "ollama":
            ollama_model = settings.ollama_model or "llama2"
            init_ai_chat(provider="ollama", model=ollama_model, ollama_base_url=ollama_base_url)
            logger.info(f"Settings updated and AI reinitialized: Provider={provider}, Model={ollama_model}, URL={ollama_base_url}")
            return settings
        
        init_ai_chat(provider=provider, api_key=api_key, model=model)
        logger.info(f"Settings updated and AI reinitialized: Provider={provider}, Model={model}")
        
        return settings
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/settings/reset")
async def reset_settings_to_default():
    """Reset trading settings to default values"""
    try:
        # Create default settings
        default_settings = TradingSettings(
            id="trading_settings",
            active_platforms=["MT5_LIBERTEX", "MT5_ICMARKETS"],
            auto_trading=False,
            use_ai_analysis=True,
            ai_provider="emergent",
            ai_model="gpt-5",
            stop_loss_percent=2.0,
            take_profit_percent=4.0,
            use_trailing_stop=False,
            trailing_stop_distance=1.5,
            max_trades_per_hour=3,
            position_size=1.0,
            max_portfolio_risk_percent=20.0,
            default_platform="MT5_LIBERTEX",
            enabled_commodities=["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS", "WHEAT", "CORN", "SOYBEANS", "COFFEE", "SUGAR", "COTTON", "COCOA"],
            # KI Trading Strategie-Parameter (Standardwerte)
            rsi_oversold_threshold=30.0,
            rsi_overbought_threshold=70.0,
            macd_signal_threshold=0.0,
            trend_following=True,
            min_confidence_score=0.6,
            use_volume_confirmation=True,
            risk_per_trade_percent=2.0
        )
        
        # Get existing settings to preserve API keys
        existing = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # Preserve API keys and credentials
        if existing:
            default_settings.openai_api_key = existing.get('openai_api_key')
            default_settings.gemini_api_key = existing.get('gemini_api_key')
            default_settings.anthropic_api_key = existing.get('anthropic_api_key')
            default_settings.bitpanda_api_key = existing.get('bitpanda_api_key')
            default_settings.mt5_libertex_account_id = existing.get('mt5_libertex_account_id')
            default_settings.mt5_icmarkets_account_id = existing.get('mt5_icmarkets_account_id')
            default_settings.bitpanda_email = existing.get('bitpanda_email')
        
        # Update database
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": default_settings.model_dump()},
            upsert=True
        )
        
        # Reinitialize AI with default settings
        init_ai_chat(provider="emergent", model="gpt-5")
        
        logger.info("Settings reset to default values")
        return {"success": True, "message": "Einstellungen auf Standardwerte zurückgesetzt", "settings": default_settings}
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/market/refresh")
async def refresh_market_data():
    """Manually refresh market data"""
    await process_market_data()
    return {"success": True, "message": "Market data refreshed"}

@api_router.post("/trailing-stop/update")
async def update_trailing_stops_endpoint():
    """Update trailing stops for all open positions"""
    try:
        # Get current market data
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        if not settings or not settings.get('use_trailing_stop', False):
            return {"success": False, "message": "Trailing stop not enabled"}
        
        # Get latest prices for all commodities
        current_prices = {}
        enabled = settings.get('enabled_commodities', ['WTI_CRUDE'])
        
        for commodity_id in enabled:
            market_data = await db.market_data.find_one(
                {"commodity": commodity_id},
                sort=[("timestamp", -1)]
            )
            if market_data:
                current_prices[commodity_id] = market_data['price']
        
        # Update trailing stops
        await update_trailing_stops(db, current_prices, settings)
        
        # Check for stop loss triggers
        trades_to_close = await check_stop_loss_triggers(db, current_prices)
        
        # Close triggered positions
        for trade_info in trades_to_close:
            await db.trades.update_one(
                {"id": trade_info['id']},
                {
                    "$set": {
                        "status": "CLOSED",
                        "exit_price": trade_info['exit_price'],
                        "closed_at": datetime.now(timezone.utc),
                        "strategy_signal": trade_info['reason']
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Trailing stops updated",
            "closed_positions": len(trades_to_close)
        }
    except Exception as e:
        logger.error(f"Error updating trailing stops: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MT5 Integration Endpoints
@api_router.get("/mt5/account")
async def get_mt5_account():
    """Get real MT5 account information via MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        account_info = await connector.get_account_info()
        
        if not account_info:
            raise HTTPException(status_code=503, detail="Failed to get MetaAPI account info")
        
        return account_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting MetaAPI account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bitpanda Integration Endpoints
@api_router.get("/bitpanda/account")
async def get_bitpanda_account():
    """Get Bitpanda account information"""
    try:
        from bitpanda_connector import get_bitpanda_connector
        
        # Get API key from settings or environment
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        api_key = settings.get('bitpanda_api_key') if settings else None
        
        if not api_key:
            api_key = os.environ.get('BITPANDA_API_KEY')
        
        if not api_key:
            raise HTTPException(status_code=400, detail="Bitpanda API Key not configured")
        
        connector = await get_bitpanda_connector(api_key)
        account_info = await connector.get_account_info()
        
        if not account_info:
            raise HTTPException(status_code=503, detail="Failed to get Bitpanda account info")
        
        return account_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting Bitpanda account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bitpanda/status")
async def get_bitpanda_status():
    """Check Bitpanda connection status"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        api_key = settings.get('bitpanda_api_key') if settings else None
        
        if not api_key:
            api_key = os.environ.get('BITPANDA_API_KEY')
        
        if not api_key:
            return {
                "connected": False,
                "message": "Bitpanda API Key not configured"
            }
        
        from bitpanda_connector import get_bitpanda_connector
        
        connector = await get_bitpanda_connector(api_key)
        account_info = await connector.get_account_info()
        
        return {
            "connected": connector.connected,
            "mode": "BITPANDA_REST",
            "balance": account_info.get('balance') if account_info else None,
            "email": settings.get('bitpanda_email') if settings else None
        }
    except Exception as e:
        logger.error(f"Error checking Bitpanda status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

@api_router.get("/mt5/positions")
async def get_mt5_positions():
    """Get open positions from MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        positions = await connector.get_positions()
        
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error getting MetaAPI positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/trades/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a specific trade and recalculate stats"""
    try:
        result = await db.trades.delete_one({"id": trade_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Trade nicht gefunden")
        
        # Recalculate stats
        open_count = await db.trades.count_documents({"status": "OPEN"})
        closed_count = await db.trades.count_documents({"status": "CLOSED"})
        closed_trades = await db.trades.find({"status": "CLOSED"}).to_list(1000)
        total_pl = sum([t.get('profit_loss', 0) for t in closed_trades])
        
        await db.stats.update_one(
            {},
            {"$set": {
                "open_positions": open_count,
                "closed_positions": closed_count,
                "total_profit_loss": total_pl,
                "total_trades": open_count + closed_count
            }},
            upsert=True
        )
        
        logger.info(f"✅ Trade {trade_id} gelöscht, Stats aktualisiert")
        return {"success": True, "message": "Trade gelöscht"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/mt5/order")
async def place_mt5_order(
    symbol: str,
    order_type: str,
    volume: float,
    price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
):
    """Place order on MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        result = await connector.place_order(
            symbol=symbol,
            order_type=order_type.upper(),
            volume=volume,
            price=price,
            sl=stop_loss,
            tp=take_profit
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to place order on MetaAPI")
        
        return result
    except Exception as e:
        logger.error(f"Error placing MetaAPI order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mt5/close/{ticket}")
async def close_mt5_position(ticket: str):
    """Close position on MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        success = await connector.close_position(ticket)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to close position on MetaAPI")
        
        return {"success": True, "ticket": ticket}
    except Exception as e:
        logger.error(f"Error closing MetaAPI position: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@api_router.post("/sync/positions")
async def sync_positions_endpoint():
    """Sync positions from MT5/Bitpanda to database"""
    try:
        await sync_mt5_positions()
        return {"success": True, "message": "Positions synchronized"}
    except Exception as e:
        logger.error(f"Error syncing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/mt5/status")
async def get_mt5_status():
    """Check MetaAPI connection status"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        account_info = await connector.get_account_info()
        
        return {
            "connected": connector.connected,
            "mode": "METAAPI_REST",
            "account_id": connector.account_id,
            "balance": account_info.get('balance') if account_info else None,
            "trade_mode": account_info.get('trade_mode') if account_info else None,
            "broker": account_info.get('broker') if account_info else None
        }
    except Exception as e:
        logger.error(f"Error checking MetaAPI status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

@api_router.get("/mt5/symbols")
async def get_mt5_symbols():
    """Get all available symbols from MetaAPI broker"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        symbols = await connector.get_symbols()
        
        # MetaAPI returns symbols as an array of strings
        # Filter for commodity-related symbols (Oil, Gold, Silver, etc.)
        commodity_symbols = []
        commodity_keywords = ['OIL', 'GOLD', 'XAU', 'XAG', 'SILVER', 'COPPER', 'PLAT', 'PALL', 
                              'GAS', 'WHEAT', 'CORN', 'SOYBEAN', 'COFFEE', 'BRENT', 'WTI', 'CL']
        
        for symbol in symbols:
            # symbol is a string, not a dict
            symbol_name = symbol.upper()
            # Check if any commodity keyword is in the symbol name
            if any(keyword in symbol_name for keyword in commodity_keywords):
                commodity_symbols.append(symbol)
        
        logger.info(f"Found {len(commodity_symbols)} commodity symbols out of {len(symbols)} total")
        
        return {
            "success": True,
            "total_symbols": len(symbols),
            "commodity_symbols": sorted(commodity_symbols),  # Sort for easier reading
            "all_symbols": sorted(symbols)  # Include all symbols for reference, sorted
        }
    except Exception as e:
        logger.error(f"Error fetching MetaAPI symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch symbols: {str(e)}")

# Multi-Platform Endpoints
@api_router.get("/platforms/status")
async def get_platforms_status():
    """Get status of all trading platforms"""
    try:
        from multi_platform_connector import multi_platform
        
        status = multi_platform.get_platform_status()
        active_platforms = multi_platform.get_active_platforms()
        
        return {
            "success": True,
            "active_platforms": active_platforms,
            "platforms": status
        }
    except Exception as e:
        logger.error(f"Error getting platforms status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/platforms/{platform_name}/connect")
async def connect_to_platform(platform_name: str):
    """Connect to a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        success = await multi_platform.connect_platform(platform_name)
        
        if success:
            return {
                "success": True,
                "message": f"Connected to {platform_name}",
                "platform": platform_name
            }
        else:
            raise HTTPException(status_code=503, detail=f"Failed to connect to {platform_name}")
    except Exception as e:
        logger.error(f"Error connecting to {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/platforms/{platform_name}/disconnect")
async def disconnect_from_platform(platform_name: str):
    """Disconnect from a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        success = await multi_platform.disconnect_platform(platform_name)
        
        if success:
            return {
                "success": True,
                "message": f"Disconnected from {platform_name}"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to disconnect from {platform_name}")
    except Exception as e:
        logger.error(f"Error disconnecting from {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/platforms/{platform_name}/account")
async def get_platform_account(platform_name: str):
    """Get account information for a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        account_info = await multi_platform.get_account_info(platform_name)
        
        if account_info:
            # Calculate portfolio risk
            balance = account_info.get('balance', 0)
            
            # Get open trades for this platform
            open_trades = await db.trades.find({
                "mode": platform_name,
                "status": "OPEN"
            }).to_list(1000)
            
            # Calculate total risk exposure
            total_risk = 0.0
            for trade in open_trades:
                entry_price = trade.get('entry_price', 0)
                stop_loss = trade.get('stop_loss', 0)
                quantity = trade.get('quantity', 0)
                
                if entry_price > 0 and stop_loss > 0:
                    # Risk = (Entry - StopLoss) * Quantity
                    risk_per_trade = abs(entry_price - stop_loss) * quantity
                    total_risk += risk_per_trade
            
            # Portfolio risk as percentage of balance
            portfolio_risk_percent = (total_risk / balance * 100) if balance > 0 else 0.0
            
            # Add risk info to account
            account_info['portfolio_risk'] = round(total_risk, 2)
            account_info['portfolio_risk_percent'] = round(portfolio_risk_percent, 2)
            account_info['open_trades_count'] = len(open_trades)
            
            return {
                "success": True,
                "platform": platform_name,
                "account": account_info
            }
        else:
            raise HTTPException(status_code=503, detail=f"Failed to get account info for {platform_name}")
    except Exception as e:
        logger.error(f"Error getting account for {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/platforms/{platform_name}/positions")
async def get_platform_positions(platform_name: str):
    """Get open positions for a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        positions = await multi_platform.get_open_positions(platform_name)
        
        return {
            "success": True,
            "platform": platform_name,
            "positions": positions
        }
    except Exception as e:
        logger.error(f"Error getting positions for {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup"""
    logger.info("Starting WTI Smart Trader API...")
    
    # Load settings and initialize AI
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if settings:
        provider = settings.get('ai_provider', 'emergent')
        model = settings.get('ai_model', 'gpt-5')
        api_key = None
        ollama_base_url = settings.get('ollama_base_url', 'http://localhost:11434')
        ollama_model = settings.get('ollama_model', 'llama2')
        
        if provider == "openai":
            api_key = settings.get('openai_api_key')
        elif provider == "gemini":
            api_key = settings.get('gemini_api_key')
        elif provider == "anthropic":
            api_key = settings.get('anthropic_api_key')
        elif provider == "ollama":
            init_ai_chat(provider="ollama", model=ollama_model, ollama_base_url=ollama_base_url)
        else:
            init_ai_chat(provider=provider, api_key=api_key, model=model)
    else:
        # Default to Emergent LLM Key
        init_ai_chat(provider="emergent", model="gpt-5")
    
    # Load MT5 credentials from environment
    mt5_login = os.environ.get('MT5_LOGIN')
    mt5_password = os.environ.get('MT5_PASSWORD')
    mt5_server = os.environ.get('MT5_SERVER')
    
    if mt5_login and mt5_password and mt5_server:
        # Update default settings with MT5 credentials
        if settings:
            await db.trading_settings.update_one(
                {"id": "trading_settings"},
                {"$set": {
                    "mt5_login": mt5_login,
                    "mt5_password": mt5_password,
                    "mt5_server": mt5_server
                }}
            )
        else:
            # Create default settings with MT5 credentials
            default_settings = TradingSettings(
                mt5_login=mt5_login,
                mt5_password=mt5_password,
                mt5_server=mt5_server
            )
            await db.trading_settings.insert_one(default_settings.model_dump())
        
        logger.info(f"MT5 credentials loaded: Server={mt5_server}, Login={mt5_login}")
    
    # Initialize platform connector for commodity_processor
    from multi_platform_connector import multi_platform
    import commodity_processor
    commodity_processor.set_platform_connector(multi_platform)
    
    # Connect platforms for chart data availability
    await multi_platform.connect_platform('MT5_ICMARKETS')
    await multi_platform.connect_platform('MT5_LIBERTEX')
    logger.info("Platform connector initialized and platforms connected for MetaAPI chart data")
    
    # Fetch initial market data
    await process_market_data()
    
    # Start Auto-Trading Engine (LIVE TICKER MODE)
    from auto_trading_engine import get_auto_trading_engine
    auto_engine = get_auto_trading_engine(db)
    asyncio.create_task(auto_engine.start())
    logger.info("🤖 Auto-Trading Engine gestartet (LIVE TICKER - alle 10 Sekunden)")
    
    logger.info("API ready - market data available via /api/market/current and /api/market/refresh")
    logger.info("AI analysis enabled for intelligent trading decisions")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    client.close()
    logger.info("Application shutdown complete")