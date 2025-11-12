"""
Auto-Trading Engine - LIVE TICKER MODE
Führt Trades automatisch basierend auf Live-Signalen aus
"""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class AutoTradingEngine:
    def __init__(self, db):
        self.db = db
        self.running = False
        self.last_checked = {}  # Verhindert doppelte Trades
        
    async def start(self):
        """Start auto-trading engine"""
        self.running = True
        logger.info("🚀 Auto-Trading Engine gestartet (LIVE TICKER MODE)")
        
        while self.running:
            try:
                # Prüfe ob Auto-Trading aktiviert ist
                settings = await self.db.trading_settings.find_one({"id": "trading_settings"})
                
                if settings and settings.get('auto_trading'):
                    await self.check_and_execute_trades(settings)
                else:
                    logger.debug("Auto-Trading ist deaktiviert")
                
                # Warte 10 Sekunden (Live-Ticker Mode)
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Auto-Trading Engine Error: {e}")
                await asyncio.sleep(10)
    
    def stop(self):
        """Stop auto-trading engine"""
        self.running = False
        logger.info("⏹️ Auto-Trading Engine gestoppt")
    
    async def check_and_execute_trades(self, settings):
        """Prüft alle Signale und führt Trades aus"""
        try:
            # Hole aktuelle Marktdaten
            from server import latest_market_data
            
            if not latest_market_data:
                return
            
            # Hole offene Trades für Risk-Management
            open_trades = await self.db.trades.find({"status": "OPEN"}).to_list(100)
            
            # Prüfe jede Commodity
            for commodity_id, market_data in latest_market_data.items():
                signal = market_data.get('signal')
                
                # Nur bei klarem BUY/SELL Signal
                if signal not in ['BUY', 'SELL']:
                    continue
                
                # Prüfe ob wir bereits einen Trade für diese Commodity haben
                has_open_trade = any(t.get('commodity') == commodity_id and t.get('status') == 'OPEN' for t in open_trades)
                if has_open_trade:
                    logger.debug(f"⏭️ {commodity_id}: Bereits offener Trade vorhanden")
                    continue
                
                # Prüfe ob wir kürzlich geprüft haben (Cooldown 60 Sekunden)
                last_check = self.last_checked.get(commodity_id)
                if last_check:
                    time_since_check = (datetime.now(timezone.utc) - last_check).total_seconds()
                    if time_since_check < 60:
                        continue
                
                # Prüfe zusätzliche AI-Bedingungen
                if not self._validate_trade_conditions(market_data, signal, settings):
                    logger.info(f"⚠️ {commodity_id}: Signal {signal}, aber Bedingungen nicht erfüllt")
                    continue
                
                # Führe Trade aus!
                await self._execute_auto_trade(commodity_id, signal, market_data, settings, open_trades)
                
                # Markiere als geprüft
                self.last_checked[commodity_id] = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Error in check_and_execute_trades: {e}")
    
    def _validate_trade_conditions(self, market_data, signal, settings):
        """Validiert ob Trade-Bedingungen erfüllt sind"""
        rsi = market_data.get('rsi', 50)
        
        # RSI-Thresholds aus Settings
        rsi_oversold = settings.get('rsi_oversold_threshold', 30)
        rsi_overbought = settings.get('rsi_overbought_threshold', 70)
        
        if signal == 'BUY':
            # BUY: RSI sollte oversold oder neutral sein
            return rsi < rsi_overbought  # Nicht kaufen wenn overbought
        elif signal == 'SELL':
            # SELL: RSI sollte overbought oder neutral sein
            return rsi > rsi_oversold  # Nicht verkaufen wenn oversold
        
        return False
    
    async def _execute_auto_trade(self, commodity_id, signal, market_data, settings, open_trades):
        """Führt automatischen Trade aus"""
        try:
            from commodity_processor import COMMODITIES, calculate_position_size
            from multi_platform_connector import multi_platform
            import uuid
            
            logger.info(f"🤖 AUTO-TRADE: {commodity_id} {signal} Signal erkannt!")
            
            # Hole Commodity Info
            commodity_info = COMMODITIES.get(commodity_id)
            if not commodity_info:
                logger.error(f"Unknown commodity: {commodity_id}")
                return
            
            # Preis
            price = market_data.get('price', 0)
            if price <= 0:
                logger.error(f"Invalid price for {commodity_id}")
                return
            
            # Plattform
            default_platform = settings.get('default_platform', 'MT5_LIBERTEX')
            
            # Hole Balance
            await multi_platform.connect_platform(default_platform)
            if default_platform not in multi_platform.platforms:
                logger.error(f"{default_platform} nicht verbunden")
                return
            
            connector = multi_platform.platforms[default_platform].get('connector')
            if not connector:
                return
            
            account_info = await connector.get_account_info()
            balance = account_info.get('balance', 50000) if account_info else 50000
            free_margin = account_info.get('free_margin')
            
            # Berechne Position Size
            quantity = await calculate_position_size(
                balance=balance,
                price=price,
                db=self.db,
                max_risk_percent=settings.get('max_portfolio_risk_percent', 20.0),
                free_margin=free_margin,
                platform=default_platform
            )
            
            if quantity <= 0:
                logger.warning(f"Position size zu klein für {commodity_id}")
                return
            
            # Stop Loss & Take Profit
            stop_loss_pct = settings.get('stop_loss_percent', 2.0) / 100
            take_profit_pct = settings.get('take_profit_percent', 4.0) / 100
            
            if signal == 'BUY':
                stop_loss = price * (1 - stop_loss_pct)
                take_profit = price * (1 + take_profit_pct)
            else:  # SELL
                stop_loss = price * (1 + stop_loss_pct)
                take_profit = price * (1 - take_profit_pct)
            
            # Symbol
            if default_platform == 'MT5_LIBERTEX':
                symbol = commodity_info.get('mt5_libertex_symbol')
            elif default_platform == 'MT5_ICMARKETS':
                symbol = commodity_info.get('mt5_icmarkets_symbol')
            else:
                symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
            
            if not symbol:
                logger.error(f"No symbol for {commodity_id} on {default_platform}")
                return
            
            # Trade ausführen!
            logger.info(f"📊 Executing: {signal} {quantity} {symbol} @ {price:.2f} on {default_platform}")
            
            result = await connector.place_order(
                symbol=symbol,
                order_type=signal,
                volume=quantity,
                price=price,
                sl=stop_loss,
                tp=take_profit
            )
            
            if result and result.get('success'):
                ticket = result.get('ticket')
                logger.info(f"✅ AUTO-TRADE ERFOLGREICH: {commodity_id} {signal} Ticket #{ticket}")
                
                # Speichere in DB
                trade_doc = {
                    "id": str(uuid.uuid4()),
                    "commodity": commodity_id,
                    "type": signal,
                    "price": price,
                    "quantity": quantity,
                    "mode": default_platform,
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "strategy_signal": f"AUTO-{signal} RSI:{market_data.get('rsi', 50):.1f}",
                    "status": "OPEN",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "closed_at": None,
                    "mt5_ticket": ticket
                }
                
                await self.db.trades.insert_one(trade_doc)
                logger.info(f"💾 Trade gespeichert in DB")
                
            else:
                logger.error(f"❌ Trade fehlgeschlagen: {result}")
                
        except Exception as e:
            logger.error(f"Error executing auto-trade: {e}")


# Global instance
_auto_trading_engine = None

def get_auto_trading_engine(db):
    """Get or create auto-trading engine instance"""
    global _auto_trading_engine
    if _auto_trading_engine is None:
        _auto_trading_engine = AutoTradingEngine(db)
    return _auto_trading_engine
