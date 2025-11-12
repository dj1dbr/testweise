"""
AI Chat Service for Trading Bot
Supports: GPT-5, Claude, and Ollama (local)
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize chat instance (will be set on first use)
_chat_instance = None

def get_trading_context(settings, latest_market_data, open_trades):
    """Generate context about current trading state"""
    context = f"""
Du bist ein intelligenter Trading-Assistent für die Rohstoff-Trading-Plattform.

AKTUELLE TRADING-EINSTELLUNGEN:
- Auto-Trading: {'Aktiv' if settings.get('auto_trading') else 'Inaktiv'}
- AI-Analyse: {'Aktiv' if settings.get('use_ai_analysis') else 'Inaktiv'}
- Risiko pro Trade: {settings.get('risk_per_trade_percent', 2)}%
- Max Portfolio Risiko: {settings.get('max_portfolio_risk_percent', 20)}%
- Standard-Plattform: {settings.get('default_platform', 'MT5_LIBERTEX')}
- Stop Loss: {settings.get('stop_loss_percent', 2)}%
- Take Profit: {settings.get('take_profit_percent', 4)}%

MARKTDATEN (Live):
"""
    
    # Add market data for key commodities
    for commodity_id in ['GOLD', 'SILVER', 'WTI_CRUDE', 'BRENT_CRUDE']:
        if commodity_id in latest_market_data:
            data = latest_market_data[commodity_id]
            context += f"\n{commodity_id}: ${data.get('price', 0):.2f}, Signal: {data.get('signal', 'HOLD')}, RSI: {data.get('rsi', 50):.1f}"
    
    context += f"\n\nOFFENE TRADES: {len(open_trades)}"
    if open_trades:
        context += "\n"
        for trade in open_trades[:5]:  # Limit to 5 most recent
            context += f"- {trade.get('commodity')}: {trade.get('type')} {trade.get('quantity')} @ ${trade.get('entry_price')}\n"
    
    context += "\n\nDu kannst Fragen über Trading-Entscheidungen beantworten, Marktanalysen durchführen und erklären, warum bestimmte Trades ausgeführt oder nicht ausgeführt wurden."
    
    return context


async def get_ai_chat_instance(settings, ai_provider="openai", model="gpt-5"):
    """Get or create AI chat instance based on provider"""
    global _chat_instance
    
    try:
        if ai_provider == "ollama":
            # Ollama support for local AI
            import aiohttp
            
            class OllamaChat:
                def __init__(self, base_url="http://localhost:11434"):
                    self.base_url = base_url
                    self.model = model or "llama3"
                    self.history = []
                
                async def send_message(self, message):
                    self.history.append({"role": "user", "content": message})
                    
                    async with aiohttp.ClientSession() as session:
                        payload = {
                            "model": self.model,
                            "messages": self.history,
                            "stream": False
                        }
                        async with session.post(f"{self.base_url}/api/chat", json=payload) as response:
                            if response.status == 200:
                                result = await response.json()
                                assistant_msg = result.get('message', {}).get('content', '')
                                self.history.append({"role": "assistant", "content": assistant_msg})
                                return assistant_msg
                            else:
                                return "Fehler: Ollama nicht erreichbar. Bitte starten Sie Ollama lokal."
            
            return OllamaChat()
        
        else:
            # Use Emergentintegrations for GPT-5/Claude
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            api_key = os.getenv('EMERGENT_LLM_KEY')
            if not api_key:
                raise Exception("EMERGENT_LLM_KEY not found")
            
            # Determine provider and model
            provider_map = {
                "openai": ("openai", model or "gpt-5"),
                "anthropic": ("anthropic", model or "claude-4-sonnet-20250514"),
                "claude": ("anthropic", "claude-4-sonnet-20250514"),
                "gemini": ("gemini", model or "gemini-2.5-pro")
            }
            
            provider, model_name = provider_map.get(ai_provider.lower(), ("openai", "gpt-5"))
            
            system_message = "Du bist ein intelligenter Trading-Assistent. Antworte auf Deutsch, kurz und präzise."
            
            chat = LlmChat(
                api_key=api_key,
                session_id="trading-chat-session",
                system_message=system_message
            ).with_model(provider, model_name)
            
            logger.info(f"✅ AI Chat initialized: {provider}/{model_name}")
            return chat
            
    except Exception as e:
        logger.error(f"Error initializing AI chat: {e}")
        raise


async def send_chat_message(message: str, settings: dict, latest_market_data: dict, open_trades: list, ai_provider: str = "openai", model: str = None):
    """Send a message to the AI and get response"""
    try:
        # Get AI chat instance
        chat = await get_ai_chat_instance(settings, ai_provider, model)
        
        # Add trading context to the message
        context = get_trading_context(settings, latest_market_data, open_trades)
        full_message = f"{context}\n\nBENUTZER FRAGE: {message}"
        
        # Send message based on provider type
        if hasattr(chat, 'send_message'):
            # Ollama or custom chat
            if ai_provider == "ollama":
                response = await chat.send_message(full_message)
            else:
                # Emergentintegrations
                from emergentintegrations.llm.chat import UserMessage
                user_msg = UserMessage(text=full_message)
                response = await chat.send_message(user_msg)
        else:
            response = "AI Chat ist nicht verfügbar"
        
        logger.info(f"AI Response generated (length: {len(response)})")
        return {
            "success": True,
            "response": response,
            "provider": ai_provider,
            "model": model or "default"
        }
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        return {
            "success": False,
            "response": f"Fehler: {str(e)}",
            "provider": ai_provider
        }
