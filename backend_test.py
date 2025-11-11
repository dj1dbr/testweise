#!/usr/bin/env python3
"""
Rohstoff Trader Backend API Test Suite
Tests MT5 connection, symbol mapping, and trade execution after fixes
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RohstoffTraderTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        logger.info(f"{status} {test_name}: {details}")
        
    async def make_request(self, method: str, endpoint: str, data: Dict = None) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"Making {method} request to: {url}")
            
            if method.upper() == "GET":
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_data = await response.json()
                    return response.status == 200, response_data
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_data = await response.json()
                    return response.status == 200, response_data
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return False, {"error": str(e)}
    
    async def test_api_root(self):
        """Test basic API connectivity"""
        success, data = await self.make_request("GET", "/api/")
        expected_message = "Rohstoff Trader API"
        
        if success and data.get("message") == expected_message:
            self.log_test_result("API Root Connectivity", True, f"API responding correctly: {data.get('message')}")
        else:
            self.log_test_result("API Root Connectivity", False, f"Unexpected response: {data}")
    
    async def test_mt5_account_info(self):
        """Test MT5 account information retrieval"""
        success, data = await self.make_request("GET", "/api/mt5/account")
        
        if success:
            required_fields = ["balance", "equity", "currency", "broker"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                balance = data.get("balance", 0)
                broker = data.get("broker", "Unknown")
                currency = data.get("currency", "Unknown")
                self.log_test_result(
                    "MT5 Account Info", 
                    True, 
                    f"Account retrieved: Balance={balance} {currency}, Broker={broker}",
                    data
                )
            else:
                self.log_test_result(
                    "MT5 Account Info", 
                    False, 
                    f"Missing required fields: {missing_fields}",
                    data
                )
        else:
            self.log_test_result("MT5 Account Info", False, f"Failed to get account info: {data}")
    
    async def test_mt5_status(self):
        """Test MT5 connection status"""
        success, data = await self.make_request("GET", "/api/mt5/status")
        
        if success:
            connected = data.get("connected", False)
            account_id = data.get("account_id", "")
            mode = data.get("mode", "")
            
            if connected and account_id:
                self.log_test_result(
                    "MT5 Connection Status", 
                    True, 
                    f"Connected: {connected}, Account: {account_id}, Mode: {mode}",
                    data
                )
            else:
                self.log_test_result(
                    "MT5 Connection Status", 
                    False, 
                    f"Connection issues: Connected={connected}, Account={account_id}",
                    data
                )
        else:
            self.log_test_result("MT5 Connection Status", False, f"Failed to get status: {data}")
    
    async def test_mt5_symbols(self):
        """Test MT5 symbols retrieval and verify commodity symbols"""
        success, data = await self.make_request("GET", "/api/mt5/symbols")
        
        if success:
            total_symbols = data.get("total_symbols", 0)
            commodity_symbols = data.get("commodity_symbols", [])
            all_symbols = data.get("all_symbols", [])
            
            # Check for key commodity symbols that should be available
            expected_symbols = ["WTI_F6", "XAUUSD", "XAGUSD", "BRENT_F6"]
            found_symbols = []
            missing_symbols = []
            
            for symbol in expected_symbols:
                if symbol in all_symbols:
                    found_symbols.append(symbol)
                else:
                    missing_symbols.append(symbol)
            
            if total_symbols > 2000 and "WTI_F6" in all_symbols:
                self.log_test_result(
                    "MT5 Symbols Retrieval", 
                    True, 
                    f"Retrieved {total_symbols} symbols, {len(commodity_symbols)} commodities. Found: {found_symbols}",
                    {"total": total_symbols, "found_symbols": found_symbols, "missing": missing_symbols}
                )
            else:
                self.log_test_result(
                    "MT5 Symbols Retrieval", 
                    False, 
                    f"Symbol issues: Total={total_symbols}, Missing key symbols: {missing_symbols}",
                    data
                )
        else:
            self.log_test_result("MT5 Symbols Retrieval", False, f"Failed to get symbols: {data}")
    
    async def test_mt5_positions(self):
        """Test MT5 positions retrieval"""
        success, data = await self.make_request("GET", "/api/mt5/positions")
        
        if success:
            positions = data.get("positions", [])
            self.log_test_result(
                "MT5 Positions", 
                True, 
                f"Retrieved {len(positions)} open positions",
                {"position_count": len(positions), "positions": positions}
            )
        else:
            self.log_test_result("MT5 Positions", False, f"Failed to get positions: {data}")
    
    async def test_commodities_list(self):
        """Test commodities list endpoint"""
        success, data = await self.make_request("GET", "/api/commodities")
        
        if success:
            commodities = data.get("commodities", {})
            
            # Check for key commodities and their MT5 symbols
            key_commodities = {
                "WTI_CRUDE": "WTI_F6",
                "GOLD": "XAUUSD",
                "SILVER": "XAGUSD",
                "BRENT_CRUDE": "BRENT_F6"
            }
            
            correct_mappings = []
            incorrect_mappings = []
            
            for commodity, expected_mt5_symbol in key_commodities.items():
                if commodity in commodities:
                    actual_mt5_symbol = commodities[commodity].get("mt5_symbol")
                    if actual_mt5_symbol == expected_mt5_symbol:
                        correct_mappings.append(f"{commodity}→{actual_mt5_symbol}")
                    else:
                        incorrect_mappings.append(f"{commodity}→{actual_mt5_symbol} (expected {expected_mt5_symbol})")
                else:
                    incorrect_mappings.append(f"{commodity} missing")
            
            if len(correct_mappings) >= 3 and not incorrect_mappings:
                self.log_test_result(
                    "Commodities Symbol Mapping", 
                    True, 
                    f"Correct mappings: {correct_mappings}",
                    {"correct": correct_mappings, "total_commodities": len(commodities)}
                )
            else:
                self.log_test_result(
                    "Commodities Symbol Mapping", 
                    False, 
                    f"Mapping issues - Correct: {correct_mappings}, Incorrect: {incorrect_mappings}",
                    data
                )
        else:
            self.log_test_result("Commodities Symbol Mapping", False, f"Failed to get commodities: {data}")
    
    async def test_settings_get(self):
        """Test settings retrieval"""
        success, data = await self.make_request("GET", "/api/settings")
        
        if success:
            enabled_commodities = data.get("enabled_commodities", [])
            mode = data.get("mode", "PAPER")
            
            if "WTI_CRUDE" in enabled_commodities and "GOLD" in enabled_commodities:
                self.log_test_result(
                    "Settings Retrieval", 
                    True, 
                    f"Mode: {mode}, Enabled commodities: {len(enabled_commodities)}",
                    {"mode": mode, "enabled_count": len(enabled_commodities)}
                )
            else:
                self.log_test_result(
                    "Settings Retrieval", 
                    False, 
                    f"Missing key commodities in enabled list: {enabled_commodities}",
                    data
                )
        else:
            self.log_test_result("Settings Retrieval", False, f"Failed to get settings: {data}")
    
    async def test_settings_update_mt5_mode(self):
        """Test updating settings to MT5 mode"""
        settings_data = {
            "mode": "MT5",
            "enabled_commodities": ["GOLD", "SILVER", "WTI_CRUDE", "BRENT_CRUDE"]
        }
        
        success, data = await self.make_request("POST", "/api/settings", settings_data)
        
        if success:
            updated_mode = data.get("mode", "")
            if updated_mode == "MT5":
                self.log_test_result(
                    "Settings Update MT5 Mode", 
                    True, 
                    f"Successfully updated to MT5 mode",
                    {"mode": updated_mode}
                )
            else:
                self.log_test_result(
                    "Settings Update MT5 Mode", 
                    False, 
                    f"Mode not updated correctly: {updated_mode}",
                    data
                )
        else:
            self.log_test_result("Settings Update MT5 Mode", False, f"Failed to update settings: {data}")
    
    async def test_market_data_all(self):
        """Test market data for all commodities"""
        success, data = await self.make_request("GET", "/api/market/all")
        
        if success:
            markets = data.get("markets", {})
            enabled_commodities = data.get("enabled_commodities", [])
            
            # Check if we have market data for key commodities
            key_commodities = ["WTI_CRUDE", "GOLD"]
            found_data = []
            missing_data = []
            
            for commodity in key_commodities:
                if commodity in markets and markets[commodity].get("price"):
                    found_data.append(f"{commodity}=${markets[commodity]['price']}")
                else:
                    missing_data.append(commodity)
            
            if len(found_data) >= 1:
                self.log_test_result(
                    "Market Data All", 
                    True, 
                    f"Market data available: {found_data}",
                    {"markets_count": len(markets), "enabled_count": len(enabled_commodities)}
                )
            else:
                self.log_test_result(
                    "Market Data All", 
                    False, 
                    f"Missing market data for: {missing_data}",
                    data
                )
        else:
            self.log_test_result("Market Data All", False, f"Failed to get market data: {data}")
    
    async def test_manual_trade_wti_crude(self):
        """Test manual trade execution for WTI_CRUDE (CRITICAL TEST)"""
        # Use query parameters instead of JSON body
        endpoint = "/api/trades/execute?trade_type=BUY&price=60.5&commodity=WTI_CRUDE&quantity=0.01"
        
        success, data = await self.make_request("POST", endpoint)
        
        if success:
            trade_info = data.get("trade", {})
            mt5_ticket = data.get("mt5_ticket")
            
            if mt5_ticket and trade_info.get("commodity") == "WTI_CRUDE":
                self.log_test_result(
                    "Manual Trade WTI_CRUDE", 
                    True, 
                    f"Trade executed successfully - MT5 Ticket: {mt5_ticket}",
                    {"mt5_ticket": mt5_ticket, "commodity": trade_info.get("commodity")}
                )
            else:
                self.log_test_result(
                    "Manual Trade WTI_CRUDE", 
                    False, 
                    f"Trade execution issues - Ticket: {mt5_ticket}, Data: {trade_info}",
                    data
                )
        else:
            error_msg = data.get("detail", str(data))
            if "ERR_MARKET_UNKNOWN_SYMBOL" in error_msg:
                self.log_test_result(
                    "Manual Trade WTI_CRUDE", 
                    False, 
                    f"CRITICAL: Symbol mapping error - {error_msg}",
                    data
                )
            else:
                self.log_test_result(
                    "Manual Trade WTI_CRUDE", 
                    False, 
                    f"Trade execution failed: {error_msg}",
                    data
                )
    
    async def test_manual_trade_gold(self):
        """Test manual trade execution for GOLD"""
        # Use query parameters instead of JSON body
        endpoint = "/api/trades/execute?trade_type=BUY&price=3990&commodity=GOLD&quantity=0.01"
        
        success, data = await self.make_request("POST", endpoint)
        
        if success:
            trade_info = data.get("trade", {})
            mt5_ticket = data.get("mt5_ticket")
            
            if mt5_ticket and trade_info.get("commodity") == "GOLD":
                self.log_test_result(
                    "Manual Trade GOLD", 
                    True, 
                    f"Trade executed successfully - MT5 Ticket: {mt5_ticket}",
                    {"mt5_ticket": mt5_ticket, "commodity": trade_info.get("commodity")}
                )
            else:
                self.log_test_result(
                    "Manual Trade GOLD", 
                    False, 
                    f"Trade execution issues - Ticket: {mt5_ticket}",
                    data
                )
        else:
            error_msg = data.get("detail", str(data))
            self.log_test_result(
                "Manual Trade GOLD", 
                False, 
                f"Trade execution failed: {error_msg}",
                data
            )
    
    async def test_trades_list(self):
        """Test trades list retrieval"""
        success, data = await self.make_request("GET", "/api/trades/list")
        
        if success:
            trades = data.get("trades", [])
            self.log_test_result(
                "Trades List", 
                True, 
                f"Retrieved {len(trades)} trades",
                {"trades_count": len(trades)}
            )
        else:
            self.log_test_result("Trades List", False, f"Failed to get trades: {data}")
    
    async def test_platforms_status(self):
        """Test multi-platform status endpoint"""
        success, data = await self.make_request("GET", "/api/platforms/status")
        
        if success:
            platforms = data.get("platforms", {})
            active_platforms = data.get("active_platforms", [])
            
            # Check if we have 3 platforms
            expected_platforms = ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
            found_platforms = [p for p in expected_platforms if p in platforms]
            
            if len(platforms) == 3 and len(found_platforms) == 3:
                self.log_test_result(
                    "Platforms Status", 
                    True, 
                    f"Found all 3 platforms: {found_platforms}, Active: {active_platforms}",
                    {"platforms": platforms, "active": active_platforms}
                )
            else:
                self.log_test_result(
                    "Platforms Status", 
                    False, 
                    f"Expected 3 platforms, found {len(platforms)}: {list(platforms.keys())}",
                    data
                )
        else:
            self.log_test_result("Platforms Status", False, f"Failed to get platforms status: {data}")
    
    async def test_mt5_libertex_account(self):
        """Test MT5 Libertex account endpoint"""
        success, data = await self.make_request("GET", "/api/platforms/MT5_LIBERTEX/account")
        
        if success:
            account = data.get("account", {})
            balance = account.get("balance", 0)
            leverage = account.get("leverage", 0)
            currency = account.get("currency", "")
            
            # Expected: Balance 50000 EUR, Leverage 1000
            if balance > 0 and leverage > 0 and currency == "EUR":
                self.log_test_result(
                    "MT5 Libertex Account", 
                    True, 
                    f"Balance: {balance} {currency}, Leverage: {leverage}",
                    {"balance": balance, "leverage": leverage, "currency": currency}
                )
            else:
                self.log_test_result(
                    "MT5 Libertex Account", 
                    False, 
                    f"Unexpected values - Balance: {balance}, Leverage: {leverage}, Currency: {currency}",
                    data
                )
        else:
            error_msg = data.get("detail", str(data))
            self.log_test_result("MT5 Libertex Account", False, f"Failed to get account: {error_msg}", data)
    
    async def test_mt5_icmarkets_account(self):
        """Test MT5 ICMarkets account endpoint"""
        success, data = await self.make_request("GET", "/api/platforms/MT5_ICMARKETS/account")
        
        if success:
            account = data.get("account", {})
            balance = account.get("balance", 0)
            leverage = account.get("leverage", 0)
            currency = account.get("currency", "")
            
            # Expected: Balance ~2204 EUR, Leverage 30
            if balance > 0 and leverage > 0 and currency == "EUR":
                self.log_test_result(
                    "MT5 ICMarkets Account", 
                    True, 
                    f"Balance: {balance} {currency}, Leverage: {leverage}",
                    {"balance": balance, "leverage": leverage, "currency": currency}
                )
            else:
                self.log_test_result(
                    "MT5 ICMarkets Account", 
                    False, 
                    f"Unexpected values - Balance: {balance}, Leverage: {leverage}, Currency: {currency}",
                    data
                )
        else:
            error_msg = data.get("detail", str(data))
            self.log_test_result("MT5 ICMarkets Account", False, f"Failed to get account: {error_msg}", data)
    
    async def test_settings_platforms(self):
        """Test settings endpoint for platform configuration"""
        success, data = await self.make_request("GET", "/api/settings")
        
        if success:
            active_platforms = data.get("active_platforms", None)
            default_platform = data.get("default_platform", None)
            
            # Check if active_platforms is an array and default_platform is defined
            if active_platforms is not None and default_platform is not None:
                self.log_test_result(
                    "Settings Platform Config", 
                    True, 
                    f"Active platforms: {active_platforms}, Default: {default_platform}",
                    {"active_platforms": active_platforms, "default_platform": default_platform}
                )
            else:
                self.log_test_result(
                    "Settings Platform Config", 
                    False, 
                    f"Missing platform config - Active: {active_platforms}, Default: {default_platform}",
                    data
                )
        else:
            self.log_test_result("Settings Platform Config", False, f"Failed to get settings: {data}")
    
    async def test_commodities_multi_platform_symbols(self):
        """Test commodities endpoint for multi-platform symbol mappings"""
        success, data = await self.make_request("GET", "/api/commodities")
        
        if success:
            commodities = data.get("commodities", {})
            
            # Check WTI_CRUDE specifically
            wti = commodities.get("WTI_CRUDE", {})
            libertex_symbol = wti.get("mt5_libertex_symbol")
            icmarkets_symbol = wti.get("mt5_icmarkets_symbol")
            
            # Expected: USOILCash (Libertex), WTI_F6 (ICMarkets)
            if libertex_symbol == "USOILCash" and icmarkets_symbol == "WTI_F6":
                self.log_test_result(
                    "Commodities Multi-Platform Symbols", 
                    True, 
                    f"WTI_CRUDE: Libertex={libertex_symbol}, ICMarkets={icmarkets_symbol}",
                    {"wti_libertex": libertex_symbol, "wti_icmarkets": icmarkets_symbol}
                )
            else:
                self.log_test_result(
                    "Commodities Multi-Platform Symbols", 
                    False, 
                    f"Incorrect symbols - Libertex: {libertex_symbol} (expected USOILCash), ICMarkets: {icmarkets_symbol} (expected WTI_F6)",
                    {"wti": wti}
                )
        else:
            self.log_test_result("Commodities Multi-Platform Symbols", False, f"Failed to get commodities: {data}")
    
    async def run_all_tests(self):
        """Run all backend tests in sequence"""
        logger.info("🚀 Starting Rohstoff Trader Backend API Tests - Multi-Platform Edition")
        logger.info(f"Testing against: {self.base_url}")
        
        # Basic connectivity tests
        await self.test_api_root()
        
        # Multi-Platform Tests (NEW - PRIORITY)
        logger.info("\n=== MULTI-PLATFORM TESTS ===")
        await self.test_platforms_status()
        await self.test_mt5_libertex_account()
        await self.test_mt5_icmarkets_account()
        await self.test_settings_platforms()
        await self.test_commodities_multi_platform_symbols()
        
        # Legacy MT5 Connection Tests
        logger.info("\n=== LEGACY MT5 TESTS ===")
        await self.test_mt5_account_info()
        await self.test_mt5_status()
        await self.test_mt5_symbols()
        await self.test_mt5_positions()
        
        # Settings Tests
        logger.info("\n=== SETTINGS TESTS ===")
        await self.test_settings_get()
        await self.test_settings_update_mt5_mode()
        
        # Market Data Tests
        logger.info("\n=== MARKET DATA TESTS ===")
        await self.test_commodities_list()
        await self.test_market_data_all()
        
        # Manual Trade Execution Tests (MOST IMPORTANT)
        logger.info("\n=== TRADE EXECUTION TESTS ===")
        await self.test_manual_trade_wti_crude()
        await self.test_manual_trade_gold()
        
        # Additional tests
        logger.info("\n=== ADDITIONAL TESTS ===")
        await self.test_trades_list()
        
        # Summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        logger.info("\n" + "="*80)
        logger.info("🏁 TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  - {result['test']}: {result['details']}")
        
        logger.info("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["success"]:
                logger.info(f"  - {result['test']}: {result['details']}")
        
        logger.info("="*80)

async def main():
    """Main test execution"""
    # Backend URL from environment
    backend_url = "https://trade-hub-116.preview.emergentagent.com"
    
    async with RohstoffTraderTester(backend_url) as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())