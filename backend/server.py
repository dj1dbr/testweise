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
from datetime import datetime, timezone
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
latest_market_data = None
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

# Commodity definitions
COMMODITIES = {
    "WTI_CRUDE": {"name": "WTI Crude Oil", "symbol": "CL=F", "mt5_symbol": "USOIL", "category": "Energie"},
    "BRENT_CRUDE": {"name": "Brent Crude Oil", "symbol": "BZ=F", "mt5_symbol": "UKOIL", "category": "Energie"},
    "GOLD": {"name": "Gold", "symbol": "GC=F", "mt5_symbol": "XAUUSD", "category": "Edelmetalle"},
    "SILVER": {"name": "Silber", "symbol": "SI=F", "mt5_symbol": "XAGUSD", "category": "Edelmetalle"},
    "PLATINUM": {"name": "Platin", "symbol": "PL=F", "mt5_symbol": "XPTUSD", "category": "Edelmetalle"},
    "PALLADIUM": {"name": "Palladium", "symbol": "PA=F", "mt5_symbol": "XPDUSD", "category": "Edelmetalle"},
    "COPPER": {"name": "Kupfer", "symbol": "HG=F", "mt5_symbol": "COPPER", "category": "Industriemetalle"},
    "ALUMINUM": {"name": "Aluminium", "symbol": "ALI=F", "mt5_symbol": "ALUMINUM", "category": "Industriemetalle"},
    "NATURAL_GAS": {"name": "Natural Gas", "symbol": "NG=F", "mt5_symbol": "NATURALGAS", "category": "Energie"},
    "HEATING_OIL": {"name": "Heizöl", "symbol": "HO=F", "mt5_symbol": "HEATINGOIL", "category": "Energie"},
    "WHEAT": {"name": "Weizen", "symbol": "ZW=F", "mt5_symbol": "WHEAT", "category": "Agrar"},
    "CORN": {"name": "Mais", "symbol": "ZC=F", "mt5_symbol": "CORN", "category": "Agrar"},
    "SOYBEANS": {"name": "Sojabohnen", "symbol": "ZS=F", "mt5_symbol": "SOYBEANS", "category": "Agrar"},
    "COFFEE": {"name": "Kaffee", "symbol": "KC=F", "mt5_symbol": "COFFEE", "category": "Agrar"}
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
    mode: Literal["PAPER", "MT5"] = "PAPER"
    entry_price: float
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_signal: Optional[str] = None
    closed_at: Optional[datetime] = None

class TradingSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = "trading_settings"
    mode: Literal["PAPER", "MT5"] = "PAPER"
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
    enabled_commodities: List[str] = ["WTI_CRUDE"]  # List of enabled commodity IDs
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None

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

async def get_ai_analysis(market_data: dict, df: pd.DataFrame) -> dict:
    """Get AI analysis for trading decision"""
    global ai_chat
    
    if not ai_chat:
        logger.warning("AI chat not initialized, using standard technical analysis")
        return None
    
    try:
        # Prepare market context
        latest = df.iloc[-1]
        last_5 = df.tail(5)
        
        analysis_prompt = f"""Analyze the following WTI crude oil market data and provide a trading recommendation:

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
            
            logger.info(f"AI Recommendation: {ai_recommendation.get('signal')} (Confidence: {ai_recommendation.get('confidence')}%)")
            logger.info(f"AI Reasoning: {ai_recommendation.get('reasoning')}")
            
            return ai_recommendation
        else:
            logger.warning(f"Could not parse AI response as JSON: {response_text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting AI analysis: {e}")
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
        
        logger.info("Market data processing complete for all commodities")
        
    except Exception as e:
        logger.error(f"Error processing market data: {e}")


async def process_commodity_market_data(commodity_id: str, settings):
    """Process market data for a specific commodity"""
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
        enabled = settings.get('enabled_commodities', ["WTI_CRUDE"]) if settings else ["WTI_CRUDE"]
        
        results = {}
        for commodity_id in enabled:
            market_data = await db.market_data.find_one(
                {"commodity": commodity_id},
                {"_id": 0},
                sort=[("timestamp", -1)]
            )
            if market_data:
                results[commodity_id] = market_data
        
        return {"markets": results, "enabled_commodities": enabled}
    except Exception as e:
        logger.error(f"Error fetching all markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/current", response_model=MarketData)
async def get_current_market():
    """Get current market data with indicators"""
    if latest_market_data is None:
        # Fetch data synchronously if not available
        await process_market_data()
    
    if latest_market_data is None:
        raise HTTPException(status_code=503, detail="Market data not available")
    
    return latest_market_data

@api_router.get("/market/history")
async def get_market_history(limit: int = 100):
    """Get historical market data"""
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

@api_router.post("/trades/execute")
async def execute_trade(trade_type: str, price: float, quantity: float = 1.0):
    """Manually execute a trade"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            settings = TradingSettings().model_dump()
        
        stop_loss = price * (1 - settings.get('stop_loss_percent', 2.0) / 100)
        take_profit = price * (1 + settings.get('take_profit_percent', 4.0) / 100)
        
        trade = Trade(
            type=trade_type.upper(),
            price=price,
            quantity=quantity,
            mode=settings.get('mode', 'PAPER'),
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_signal="Manual"
        )
        
        doc = trade.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        await db.trades.insert_one(doc)
        
        return {"success": True, "trade": trade}
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
        
        trades = await db.trades.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
        
        # Convert timestamps
        for trade in trades:
            if isinstance(trade['timestamp'], str):
                trade['timestamp'] = datetime.fromisoformat(trade['timestamp']).isoformat()
            if trade.get('closed_at') and isinstance(trade['closed_at'], str):
                trade['closed_at'] = datetime.fromisoformat(trade['closed_at']).isoformat()
        
        return {"trades": trades}
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trades/stats", response_model=TradeStats)
async def get_trade_stats():
    """Get trading statistics"""
    try:
        all_trades = await db.trades.find({}, {"_id": 0}).to_list(10000)
        
        total_trades = len(all_trades)
        open_positions = len([t for t in all_trades if t['status'] == 'OPEN'])
        closed_positions = len([t for t in all_trades if t['status'] == 'CLOSED'])
        
        closed_trades = [t for t in all_trades if t['status'] == 'CLOSED' and t.get('profit_loss') is not None]
        total_profit_loss = sum([t['profit_loss'] for t in closed_trades])
        
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
        doc = settings.model_dump()
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
    
    # Fetch initial market data
    await process_market_data()
    
    # NOTE: Background scheduler disabled due to asyncio event loop conflicts
    # Frontend will poll the /api/market/refresh endpoint instead
    logger.info("API ready - market data available via /api/market/current and /api/market/refresh")
    logger.info("AI analysis enabled for intelligent trading decisions")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    client.close()
    logger.info("Application shutdown complete")