"""
Multi-Platform Connector - Manages multiple MT5 accounts and platforms
Supports: MT5 Libertex, MT5 ICMarkets, and Bitpanda
"""

import logging
import os
from typing import Optional, Dict, List, Any
from metaapi_connector import MetaAPIConnector
from bitpanda_connector import BitpandaConnector

logger = logging.getLogger(__name__)

class MultiPlatformConnector:
    """Manages connections to multiple trading platforms"""
    
    def __init__(self):
        self.platforms = {}
        self.metaapi_token = os.environ.get('METAAPI_TOKEN', '')
        
        # Initialize MT5 Libertex (Default/Primary)
        self.platforms['MT5_LIBERTEX'] = {
            'type': 'MT5',
            'name': 'MT5 Libertex',
            'account_id': os.environ.get('METAAPI_ACCOUNT_ID', '142e1085-f20b-437e-93c7-b87a0e639a30'),
            'region': 'london',
            'connector': None,
            'active': False,
            'balance': 0.0
        }
        
        # Initialize MT5 ICMarkets (Secondary)
        self.platforms['MT5_ICMARKETS'] = {
            'type': 'MT5',
            'name': 'MT5 ICMarkets',
            'account_id': os.environ.get('METAAPI_ICMARKETS_ACCOUNT_ID', 'd2605e89-7bc2-4144-9f7c-951edd596c39'),
            'region': 'london',
            'connector': None,
            'active': False,
            'balance': 0.0
        }
        
        # Initialize Bitpanda
        self.platforms['BITPANDA'] = {
            'type': 'BITPANDA',
            'name': 'Bitpanda',
            'api_key': os.environ.get('BITPANDA_API_KEY', ''),
            'connector': None,
            'active': False,
            'balance': 0.0
        }
        
        logger.info("MultiPlatformConnector initialized with 3 platforms")
    
    async def connect_platform(self, platform_name: str) -> bool:
        """Connect to a specific platform"""
        try:
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return False
            
            platform = self.platforms[platform_name]
            
            if platform['type'] == 'MT5':
                # Create MetaAPI connector
                connector = MetaAPIConnector(
                    account_id=platform['account_id'],
                    token=self.metaapi_token
                )
                
                # Set region-specific base URL
                if platform['region'] == 'london':
                    connector.base_url = "https://mt-client-api-v1.london.agiliumtrade.ai"
                elif platform['region'] == 'new-york':
                    connector.base_url = "https://mt-client-api-v1.new-york.agiliumtrade.ai"
                elif platform['region'] == 'singapore':
                    connector.base_url = "https://mt-client-api-v1.singapore.agiliumtrade.ai"
                
                # Connect
                success = await connector.connect()
                if success:
                    platform['connector'] = connector
                    platform['active'] = True
                    platform['balance'] = connector.balance
                    logger.info(f"✅ Connected to {platform_name}: Balance={connector.balance}")
                    return True
                else:
                    logger.error(f"Failed to connect to {platform_name}")
                    return False
                    
            elif platform['type'] == 'BITPANDA':
                # Create Bitpanda connector
                connector = BitpandaConnector(api_key=platform['api_key'])
                success = await connector.connect()
                if success:
                    platform['connector'] = connector
                    platform['active'] = True
                    platform['balance'] = connector.balance
                    logger.info(f"✅ Connected to {platform_name}: Balance={connector.balance}")
                    return True
                else:
                    logger.error(f"Failed to connect to {platform_name}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to {platform_name}: {e}")
            return False
    
    async def disconnect_platform(self, platform_name: str) -> bool:
        """Disconnect from a specific platform"""
        try:
            if platform_name in self.platforms:
                platform = self.platforms[platform_name]
                platform['active'] = False
                platform['connector'] = None
                logger.info(f"Disconnected from {platform_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disconnecting from {platform_name}: {e}")
            return False
    
    async def get_account_info(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Get account information for a specific platform"""
        try:
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            if not platform['active'] or not platform['connector']:
                # Try to connect first
                await self.connect_platform(platform_name)
            
            if platform['connector']:
                return await platform['connector'].get_account_info()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info for {platform_name}: {e}")
            return None
    
    async def execute_trade(self, platform_name: str, symbol: str, action: str, 
                           volume: float, stop_loss: float = None, 
                           take_profit: float = None) -> Optional[Dict[str, Any]]:
        """Execute a trade on a specific platform"""
        try:
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            if not platform['active'] or not platform['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return None
            
            # Route to appropriate connector
            if platform['type'] == 'MT5':
                return await platform['connector'].execute_trade(
                    symbol=symbol,
                    action=action,
                    volume=volume,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            elif platform['type'] == 'BITPANDA':
                return await platform['connector'].execute_trade(
                    symbol=symbol,
                    side=action.lower(),
                    amount=volume
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing trade on {platform_name}: {e}")
            return None
    
    async def get_open_positions(self, platform_name: str) -> List[Dict[str, Any]]:
        """Get open positions for a specific platform"""
        try:
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return []
            
            platform = self.platforms[platform_name]
            
            if not platform['active'] or not platform['connector']:
                return []
            
            return await platform['connector'].get_positions()
            
        except Exception as e:
            logger.error(f"Error getting positions for {platform_name}: {e}")
            return []
    
    def get_active_platforms(self) -> List[str]:
        """Get list of currently active platforms"""
        return [name for name, platform in self.platforms.items() if platform['active']]
    
    def get_platform_status(self) -> Dict[str, Any]:
        """Get status of all platforms"""
        return {
            name: {
                'active': platform['active'],
                'balance': platform['balance'],
                'name': platform['name']
            }
            for name, platform in self.platforms.items()
        }

# Global instance
multi_platform = MultiPlatformConnector()
