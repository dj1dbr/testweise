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
    
    # Extract settings properly (handle both dict and None)
    auto_trading = settings.get('auto_trading', False) if settings else False
    use_ai = settings.get('use_ai_analysis', False) if settings else False
    risk_per_trade = settings.get('risk_per_trade_percent', 2) if settings else 2
    max_portfolio = settings.get('max_portfolio_risk_percent', 20) if settings else 20
    platform = settings.get('default_platform', 'MT5_LIBERTEX') if settings else 'MT5_LIBERTEX'
    stop_loss = settings.get('stop_loss_percent', 2) if settings else 2
    take_profit = settings.get('take_profit_percent', 4) if settings else 4
    
    context = f"""
Du bist ein intelligenter Trading-Assistent für die Rohstoff-Trading-Plattform.

AKTUELLE TRADING-EINSTELLUNGEN:
- Auto-Trading: {'✅ AKTIV' if auto_trading else '❌ INAKTIV'}
- AI-Analyse: {'✅ AKTIV' if use_ai else '❌ INAKTIV'}
- Risiko pro Trade: {risk_per_trade}%
- Max Portfolio Risiko: {max_portfolio}%
- Standard-Plattform: {platform}
- Stop Loss: {stop_loss}%
- Take Profit: {take_profit}%

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
    else:
        context += "\n(Keine offenen Trades)"
    
    context += """

DEINE ROLLE & ANWEISUNGEN:
- Antworte KURZ und PRÄZISE (max 3-4 Sätze, außer bei detaillierten Analysen)
- Wenn der Benutzer "Ja" oder "OK" sagt, führe die vorher vorgeschlagene Aktion aus
- Erkenne Kontext aus vorherigen Nachrichten
- Bei Fragen wie "Wann tradest du?" → Erkläre KURZ die Entry-Bedingungen basierend auf aktuellen Signalen
- Nutze die AKTUELLEN Settings (siehe oben) - nicht raten!
- Wenn Auto-Trading AKTIV ist, sage das klar
- Antworte auf DEUTSCH

Du kannst:
1. Marktanalysen geben (basierend auf RSI, Signalen)
2. Erklären, warum Trades ausgeführt/nicht ausgeführt wurden
3. Trading-Empfehlungen geben
4. Settings überprüfen und erklären
"""
    
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
        if ai_provider == "ollama":
            # Ollama
            response = await chat.send_message(full_message)
        else:
            # Emergentintegrations - send_message is async
            from emergentintegrations.llm.chat import UserMessage
            user_msg = UserMessage(text=full_message)
            
            # send_message returns AssistantMessage - await it!
            response_obj = await chat.send_message(user_msg)
            
            # Extract text from response
            if hasattr(response_obj, 'text'):
                response = response_obj.text
            elif isinstance(response_obj, str):
                response = response_obj
            else:
                response = str(response_obj)
        
        logger.info(f"✅ AI Response generated (length: {len(response)})")
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
