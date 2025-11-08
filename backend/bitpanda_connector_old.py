"""
Bitpanda API Connector for Cryptocurrency Trading (Hauptplattform)
Verwendet die offizielle Bitpanda Retail API (nicht Pro/Exchange)
"""

import logging
import os
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class BitpandaConnector:
    """Bitpanda Hauptplattform API connection handler"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # WICHTIG: Hauptplattform API, nicht Pro/Exchange!
        self.base_url = "https://api.bitpanda.com/v1"
        self.connected = False
        self.balance = 0.0
        self.balances = {}
        
        logger.info(f"Bitpanda Connector (Hauptplattform) initialized")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Bitpanda Hauptplattform"""
        return {
            "X-API-KEY": self.api_key,  # Hauptplattform nutzt X-API-KEY Header
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def connect(self) -> bool:
        """Connect to Bitpanda Hauptplattform and verify credentials"""
        try:
            account_info = await self.get_account_info()
            if account_info:
                self.connected = True
                logger.info(f"✅ Connected to Bitpanda Hauptplattform")
                return True
            else:
                logger.error("Failed to connect to Bitpanda")
                return False
        except Exception as e:
            logger.error(f"Bitpanda connection error: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information from Bitpanda Hauptplattform"""
        try:
            # Hauptplattform API: /wallets für alle Asset-Wallets
            url = f"{self.base_url}/wallets"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse wallets from Hauptplattform API
                        wallets_data = data.get('data', [])
                        total_balance_eur = 0
                        
                        for wallet in wallets_data:
                            attributes = wallet.get('attributes', {})
                            crypto_id = attributes.get('cryptocoin_id', '')
                            crypto_symbol = attributes.get('cryptocoin_symbol', '')
                            fiat_id = attributes.get('fiat_id', '')
                            fiat_symbol = attributes.get('fiat_symbol', '')
                            
                            # Balance in wallet
                            balance_amount = float(attributes.get('balance', 0))
                            
                            # Determine currency
                            currency = crypto_symbol or fiat_symbol or 'UNKNOWN'
                            
                            if balance_amount > 0:
                                self.balances[currency] = {
                                    'available': balance_amount,
                                    'locked': 0,
                                    'total': balance_amount,
                                    'type': 'fiat' if fiat_id else 'crypto'
                                }
                                
                                # Estimate EUR value (simplified - nur echte EUR zählen)
                                if currency == 'EUR':
                                    total_balance_eur += balance_amount
                        
                        self.balance = total_balance_eur
                        
                        logger.info(f"Bitpanda Account Info: Balance={self.balance:.2f} EUR, Wallets={len(self.balances)}")
                        
                        return {
                            "balance": self.balance,
                            "equity": self.balance,
                            "margin": 0.0,
                            "free_margin": self.balance,
                            "profit": 0.0,
                            "currency": "EUR",
                            "leverage": 1,
                            "login": "Bitpanda Account",
                            "server": "Bitpanda",
                            "trade_mode": "LIVE",
                            "name": "Bitpanda Trading Account",
                            "broker": "Bitpanda",
                            "balances": self.balances
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Bitpanda error {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting Bitpanda account info: {e}")
            return None
    
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol from Bitpanda Hauptplattform
        
        Hinweis: Die Hauptplattform API hat kein öffentliches Ticker-Endpoint.
        Preise werden über die Wallet-Daten oder separate Ticker-API abgerufen.
        """
        try:
            # Hauptplattform: Ticker API (öffentlich, kein API-Key nötig)
            # Support-Artikel: https://support.bitpanda.com/hc/en-us/articles/360000727459
            ticker_url = f"https://api.bitpanda.com/v1/ticker"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(ticker_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Ticker format: {"BTC": "45000.50", "ETH": "3200.30", ...}
                        price_str = data.get(symbol.upper())
                        if price_str:
                            return float(price_str)
                        else:
                            logger.warning(f"Symbol {symbol} not found in Bitpanda ticker")
                            return None
                    else:
                        logger.error(f"Failed to get price for {symbol}")
                        return None
        except Exception as e:
            logger.error(f"Error getting market price for {symbol}: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions from Bitpanda Hauptplattform
        
        Hinweis: Die Hauptplattform ist ein Broker, keine Exchange.
        Positionen sind hier die Crypto/Asset Holdings, nicht offene Orders.
        """
        try:
            # Die Hauptplattform zeigt Holdings in Wallets
            url = f"{self.base_url}/wallets"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        wallets = data.get('data', [])
                        
                        result = []
                        for wallet in wallets:
                            attributes = wallet.get('attributes', {})
                            balance = float(attributes.get('balance', 0))
                            
                            # Nur Wallets mit Guthaben anzeigen
                            if balance > 0:
                                crypto_symbol = attributes.get('cryptocoin_symbol', '')
                                fiat_symbol = attributes.get('fiat_symbol', '')
                                symbol = crypto_symbol or fiat_symbol or 'UNKNOWN'
                                
                                # Formatiere als "Position"
                                result.append({
                                    "ticket": wallet.get('id', ''),
                                    "symbol": symbol,
                                    "type": "HOLD",  # Bitpanda ist kein Trading, sondern Buy & Hold
                                    "volume": balance,
                                    "price_open": 0,  # Nicht verfügbar in Hauptplattform API
                                    "price_current": 0,  # Müsste separat abgefragt werden
                                    "profit": 0.0,
                                    "swap": 0.0,
                                    "time": attributes.get('created_at', ''),
                                    "sl": None,
                                    "tp": None
                                })
                        
                        logger.info(f"Bitpanda Holdings: {len(result)} assets")
                        return result
                    else:
                        logger.error(f"Failed to get Bitpanda holdings")
                        return []
        except Exception as e:
            logger.error(f"Error getting Bitpanda holdings: {e}")
            return []
    
    async def place_order(self, symbol: str, order_type: str, volume: float, 
                         price: Optional[float] = None,
                         sl: Optional[float] = None, 
                         tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a trading order via Bitpanda Hauptplattform
        
        WICHTIG: Die Hauptplattform API unterstützt nur Buy/Sell Transaktionen,
        keine komplexen Trading-Orders mit SL/TP.
        Dies ist für einfache Käufe/Verkäufe gedacht.
        """
        try:
            # Hinweis: Die Hauptplattform API v1 hat begrenzte Trading-Funktionen
            # Für vollständiges Trading sollte man die Bitpanda Pro API verwenden
            
            logger.warning(f"Bitpanda Hauptplattform: Direct trading via API ist eingeschränkt")
            logger.warning(f"Für echtes Trading bitte Bitpanda Pro verwenden oder manuell handeln")
            
            # Simuliere erfolgreiche Order für Demo-Zwecke
            return {
                "success": False,
                "ticket": "N/A",
                "volume": volume,
                "price": price or 0.0,
                "type": order_type,
                "message": "Bitpanda Hauptplattform: Automatisches Trading nicht unterstützt. Bitte manuell auf bitpanda.com handeln."
            }
            
        except Exception as e:
            logger.error(f"Error placing Bitpanda order: {e}")
            return None
    
    async def close_position(self, position_id: str) -> bool:
        """Close an open position via Bitpanda Hauptplattform
        
        WICHTIG: Bitpanda Hauptplattform ist ein Broker, kein Trading-Desk.
        "Positionen schließen" bedeutet hier Assets verkaufen.
        Dies ist via API nur eingeschränkt möglich.
        """
        try:
            logger.warning(f"Bitpanda Hauptplattform: Position schließen via API nicht unterstützt")
            logger.warning(f"Bitte Assets manuell auf bitpanda.com verkaufen")
            
            return False
            
        except Exception as e:
            logger.error(f"Error closing Bitpanda position: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Bitpanda Hauptplattform"""
        self.connected = False
        logger.info("Disconnected from Bitpanda Hauptplattform")


# Global Bitpanda connector instance
_bitpanda_connector: Optional[BitpandaConnector] = None

async def get_bitpanda_connector(api_key: str = None) -> BitpandaConnector:
    """Get or create Bitpanda connector instance"""
    global _bitpanda_connector
    
    # Use environment variable if not provided
    if api_key is None:
        api_key = os.environ.get('BITPANDA_API_KEY')
    
    if not api_key:
        raise ValueError("Bitpanda API key not provided")
    
    if _bitpanda_connector is None:
        _bitpanda_connector = BitpandaConnector(api_key)
        await _bitpanda_connector.connect()
    
    return _bitpanda_connector
