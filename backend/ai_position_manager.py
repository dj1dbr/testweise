"""
AI-Powered Position Manager
Überwacht ALLE offenen Positionen (manuell & automatisch) und schließt sie intelligent
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def manage_open_positions(db, current_prices: dict, settings):
    """
    KI-gestützte Positionsverwaltung für ALLE offenen Trades
    Schließt Positionen automatisch bei:
    - Stop Loss erreicht
    - Take Profit erreicht
    - KI-Signal zum Schließen (Trendwende)
    """
    try:
        if not settings or not settings.get('use_ai_analysis'):
            return
        
        # Hole alle offenen Positionen
        open_trades = await db.trades.find({"status": "OPEN"}).to_list(1000)
        
        if not open_trades:
            return
        
        logger.info(f"AI Position Manager: Überwache {len(open_trades)} offene Positionen")
        
        closed_count = 0
        
        for trade in open_trades:
            commodity = trade.get('commodity', 'WTI_CRUDE')
            current_price = current_prices.get(commodity)
            
            if not current_price:
                continue
            
            trade_type = trade.get('type')
            entry_price = trade.get('entry_price')
            stop_loss = trade.get('stop_loss')
            take_profit = trade.get('take_profit')
            quantity = trade.get('quantity', 1.0)
            
            should_close = False
            close_reason = None
            
            # BUY Position Management
            if trade_type == 'BUY':
                # Gewinn berechnen
                profit = (current_price - entry_price) * quantity
                profit_percent = ((current_price - entry_price) / entry_price) * 100
                
                # Take Profit erreicht?
                if take_profit and current_price >= take_profit:
                    should_close = True
                    close_reason = f"Take Profit erreicht (+{profit_percent:.2f}%)"
                
                # Stop Loss erreicht?
                elif stop_loss and current_price <= stop_loss:
                    should_close = True
                    close_reason = f"Stop Loss getroffen ({profit_percent:.2f}%)"
                
                # KI-Signal: Markt dreht, raus mit Gewinn
                elif profit_percent > 1.0:  # Mindestens 1% Gewinn
                    # Hole aktuelles Market Signal
                    market_data = await db.market_data.find_one(
                        {"commodity": commodity},
                        sort=[("timestamp", -1)]
                    )
                    
                    if market_data:
                        signal = market_data.get('signal')
                        trend = market_data.get('trend')
                        
                        # Schließe bei SELL Signal oder Trendwende
                        if signal == 'SELL' or trend == 'DOWN':
                            should_close = True
                            close_reason = f"KI-Signal: Trendwende erkannt (Gewinn sichern: +{profit_percent:.2f}%)"
                
                # Sicherung bei hohem Gewinn (Trailing-ähnlich)
                elif profit_percent > 5.0:
                    should_close = True
                    close_reason = f"Gewinnmitnahme bei +{profit_percent:.2f}%"
            
            # SELL Position Management
            elif trade_type == 'SELL':
                # Gewinn berechnen (bei SELL profitiert man von fallendem Preis)
                profit = (entry_price - current_price) * quantity
                profit_percent = ((entry_price - current_price) / entry_price) * 100
                
                # Take Profit erreicht?
                if take_profit and current_price <= take_profit:
                    should_close = True
                    close_reason = f"Take Profit erreicht (+{profit_percent:.2f}%)"
                
                # Stop Loss erreicht?
                elif stop_loss and current_price >= stop_loss:
                    should_close = True
                    close_reason = f"Stop Loss getroffen ({profit_percent:.2f}%)"
                
                # KI-Signal: Markt dreht, raus mit Gewinn
                elif profit_percent > 1.0:
                    market_data = await db.market_data.find_one(
                        {"commodity": commodity},
                        sort=[("timestamp", -1)]
                    )
                    
                    if market_data:
                        signal = market_data.get('signal')
                        trend = market_data.get('trend')
                        
                        # Schließe bei BUY Signal oder Trendwende
                        if signal == 'BUY' or trend == 'UP':
                            should_close = True
                            close_reason = f"KI-Signal: Trendwende erkannt (Gewinn sichern: +{profit_percent:.2f}%)"
                
                # Sicherung bei hohem Gewinn
                elif profit_percent > 5.0:
                    should_close = True
                    close_reason = f"Gewinnmitnahme bei +{profit_percent:.2f}%"
            
            # Position schließen?
            if should_close:
                profit_loss = (current_price - entry_price) * quantity if trade_type == 'BUY' else (entry_price - current_price) * quantity
                
                await db.trades.update_one(
                    {"id": trade['id']},
                    {
                        "$set": {
                            "status": "CLOSED",
                            "exit_price": current_price,
                            "profit_loss": profit_loss,
                            "closed_at": datetime.now(timezone.utc),
                            "strategy_signal": close_reason
                        }
                    }
                )
                
                closed_count += 1
                logger.info(f"✅ Position geschlossen: {commodity} {trade_type} - {close_reason} (P/L: {profit_loss:.2f})")
        
        if closed_count > 0:
            logger.info(f"AI Position Manager: {closed_count} Positionen geschlossen")
    
    except Exception as e:
        logger.error(f"Error in AI Position Manager: {e}")
