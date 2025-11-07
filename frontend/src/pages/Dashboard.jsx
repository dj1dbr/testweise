import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, BarChart3, Settings, RefreshCw, Play, Pause, Zap, ZapOff, AlertCircle, ChevronLeft, ChevronRight, LineChart } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import PriceChart from '../components/PriceChart';
import TradesTable from '../components/TradesTable';
import IndicatorsPanel from '../components/IndicatorsPanel';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [marketData, setMarketData] = useState(null);
  const [allMarkets, setAllMarkets] = useState({});  // All commodity markets
  const [commodities, setCommodities] = useState({}); // Commodity definitions
  const [currentCommodityIndex, setCurrentCommodityIndex] = useState(0); // For carousel
  const [historicalData, setHistoricalData] = useState([]);
  const [selectedCommodity, setSelectedCommodity] = useState(null); // For chart modal
  const [chartModalOpen, setChartModalOpen] = useState(false);
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [settings, setSettings] = useState(null);
  const [balance, setBalance] = useState(10000); // Simulated balance
  const [mt5Account, setMt5Account] = useState(null); // Real MT5 account data
  const [mt5Connected, setMt5Connected] = useState(false);
  const [totalExposure, setTotalExposure] = useState(0); // Total exposure for 20% limit
  const [gpt5Active, setGpt5Active] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [aiProcessing, setAiProcessing] = useState(false);

  useEffect(() => {
    fetchAllData();
    
    // Live ticker - refresh market data every 10 seconds
    const liveInterval = setInterval(() => {
      if (autoRefresh) {
        fetchAllMarkets(); // Fetch all commodity markets
        refreshMarketData(); // This will trigger backend to fetch new data
        fetchTrades();
        fetchStats();
        updateBalance();
        // Fetch account data based on mode
        if (settings?.mode === 'MT5') {
          fetchMT5Account();
        } else if (settings?.mode === 'BITPANDA') {
          fetchBitpandaAccount();
        }
      }
    }, 10000);  // Every 10 seconds

    return () => clearInterval(liveInterval);
  }, [autoRefresh, settings?.mode]);

  // Load historical data for selected commodity in modal
  useEffect(() => {
    if (chartModalOpen && selectedCommodity) {
      const loadChartData = async () => {
        try {
          const response = await axios.get(`${API}/market/history?commodity=${selectedCommodity.id}&limit=100`);
          setHistoricalData(response.data);
        } catch (error) {
          console.error('Error loading chart data:', error);
        }
      };
      loadChartData();
    }
  }, [chartModalOpen, selectedCommodity]);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchCommodities(),
      fetchAllMarkets(),
      refreshMarketData(), // Use refresh instead of just fetching cached data
      fetchHistoricalData(),
      fetchTrades(),
      fetchStats(),
      fetchSettings(),
      fetchAccountData() // Unified account data fetching
    ]);
    setLoading(false);
  };

  const fetchAccountData = async () => {
    // Fetch account data based on current mode
    if (settings?.mode === 'MT5') {
      await fetchMT5Account();
    } else if (settings?.mode === 'BITPANDA') {
      await fetchBitpandaAccount();
    } else {
      // Paper trading - no external account needed
      await fetchStats();
      updateBalance();
    }
  };

  const fetchCommodities = async () => {
    try {
      const response = await axios.get(`${API}/commodities`);
      setCommodities(response.data.commodities || {});
    } catch (error) {
      console.error('Error fetching commodities:', error);
    }
  };

  const fetchAllMarkets = async () => {
    try {
      const response = await axios.get(`${API}/market/all`);
      setAllMarkets(response.data.markets || {});
    } catch (error) {
      console.error('Error fetching all markets:', error);
    }
  };
  
  const calculateTotalExposure = () => {
    // Calculate actual exposure from open trades
    const openTrades = trades.filter(t => t.status === 'OPEN');
    const exposure = openTrades.reduce((sum, trade) => {
      return sum + (trade.entry_price * trade.quantity);
    }, 0);
    setTotalExposure(exposure);
  };

  const fetchMarketData = async () => {
    try {
      const response = await axios.get(`${API}/market/current`);
      setMarketData(response.data);
    } catch (error) {
      console.error('Error fetching market data:', error);
    }
  };

  const refreshMarketData = async () => {
    try {
      setAiProcessing(true);
      // Call refresh endpoint to fetch new data from Yahoo Finance
      await axios.post(`${API}/market/refresh`);
      // Then get the updated data
      const response = await axios.get(`${API}/market/current`);
      setMarketData(response.data);
      // Also refresh historical data
      await fetchHistoricalData();
    } catch (error) {
      console.error('Error refreshing market data:', error);
    } finally {
      setAiProcessing(false);
    }
  };

  const fetchHistoricalData = async () => {
    try {
      const response = await axios.get(`${API}/market/history?limit=50`);
      setHistoricalData(response.data.data || []);
    } catch (error) {
      console.error('Error fetching historical data:', error);
    }
  };

  const fetchTrades = async () => {
    try {
      const response = await axios.get(`${API}/trades/list`);
      setTrades(response.data.trades || []);
      // Calculate exposure after loading trades
      const openTrades = (response.data.trades || []).filter(t => t.status === 'OPEN');
      const exposure = openTrades.reduce((sum, trade) => {
        return sum + (trade.entry_price * trade.quantity);
      }, 0);
      setTotalExposure(exposure);
    } catch (error) {
      console.error('Error fetching trades:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/trades/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings`);
      setSettings(response.data);
      setGpt5Active(response.data.use_gpt5 && response.data.auto_trading);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const updateBalance = () => {
    // Use real MT5 balance if connected and mode is MT5, otherwise calculate from paper trading
    if (mt5Connected && mt5Account && settings?.mode === 'MT5') {
      setBalance(mt5Account.balance);
    } else if (settings?.mode === 'PAPER') {
      // Calculate balance based on trades P/L for paper trading
      if (stats) {
        const newBalance = 10000 + (stats.total_profit_loss || 0);
        setBalance(newBalance);
      }
    }
  };

  const fetchMT5Account = async () => {
    try {
      const response = await axios.get(`${API}/mt5/account`);
      setMt5Account(response.data);
      setMt5Connected(true);
      // Always update balance immediately when MT5 data is fetched
      setBalance(response.data.balance);
    } catch (error) {
      console.error('Error fetching MT5 account:', error);
      setMt5Connected(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/market/refresh`);
      await fetchAllData();
      toast.success('Marktdaten aktualisiert');
    } catch (error) {
      toast.error('Fehler beim Aktualisieren');
    }
    setRefreshing(false);
  };

  const handleManualTrade = async (type, commodityId = 'WTI_CRUDE') => {
    const market = commodityId ? allMarkets[commodityId] : marketData;
    if (!market) {
      toast.error('Marktdaten nicht verfügbar');
      return;
    }
    
    try {
      await axios.post(`${API}/trades/execute?trade_type=${type}&price=${market.price}&quantity=1&commodity=${commodityId}`);
      toast.success(`${type} Order für ${commodities[commodityId]?.name || commodityId} ausgeführt`);
      fetchTrades();
      fetchStats();
      fetchAllMarkets();
    } catch (error) {
      toast.error('Fehler beim Ausführen der Order');
    }
  };

  const handleDeleteTrade = async (tradeId, tradeName) => {
    if (!window.confirm(`Trade "${tradeName}" wirklich löschen?`)) {
      return;
    }
    
    try {
      const response = await axios.delete(`${API}/trades/${tradeId}`);
      if (response.data.success) {
        toast.success('✅ Trade gelöscht!');
        fetchTrades();
        fetchStats();
      }
    } catch (error) {
      console.error('Error deleting trade:', error);
      toast.error(`❌ Fehler: ${error.response?.data?.detail || error.message}`);
    }
  };

  // Carousel navigation
  const enabledCommodities = Object.keys(allMarkets);
  const currentCommodityId = enabledCommodities[currentCommodityIndex];
  const currentMarket = allMarkets[currentCommodityId];
  
  const nextCommodity = () => {
    setCurrentCommodityIndex((prev) => (prev + 1) % enabledCommodities.length);
  };
  
  const prevCommodity = () => {
    setCurrentCommodityIndex((prev) => (prev - 1 + enabledCommodities.length) % enabledCommodities.length);
  };

  const handleCloseTrade = async (tradeId) => {
    if (!marketData) return;
    
    try {
      await axios.post(`${API}/trades/close/${tradeId}?exit_price=${marketData.price}`);
      toast.success('Position geschlossen');
      fetchTrades();
      fetchStats();
    } catch (error) {
      toast.error('Fehler beim Schließen der Position');
    }
  };

  const handleUpdateSettings = async (newSettings) => {
    try {
      await axios.post(`${API}/settings`, newSettings);
      setSettings(newSettings);
      setGpt5Active(newSettings.use_ai_analysis && newSettings.auto_trading);
      toast.success('Einstellungen gespeichert');
      setSettingsOpen(false);
      
      // Reload balance based on platform
      if (newSettings.mode === 'MT5') {
        await fetchMT5Account();
      } else if (newSettings.mode === 'BITPANDA') {
        await fetchBitpandaAccount();
      } else {
        // Paper trading - calculate from stats
        await fetchStats();
        updateBalance();
      }
    } catch (error) {
      toast.error('Fehler beim Speichern');
    }
  };
  
  const fetchBitpandaAccount = async () => {
    try {
      const response = await axios.get(`${API}/bitpanda/account`);
      setMt5Account(response.data); // Use same state for unified handling
      setMt5Connected(true);
      // Update balance with Bitpanda data
      if (settings?.mode === 'BITPANDA') {
        setBalance(response.data.balance);
      }
    } catch (error) {
      console.error('Error fetching Bitpanda account:', error);
      setMt5Connected(false);
      toast.error('Bitpanda Verbindung fehlgeschlagen - Prüfen Sie API Key');
    }
  };

  const getSignalColor = (signal) => {
    if (signal === 'BUY') return 'text-emerald-400';
    if (signal === 'SELL') return 'text-rose-400';
    return 'text-slate-400';
  };

  const getSignalIcon = (signal) => {
    if (signal === 'BUY') return <TrendingUp className="w-5 h-5" />;
    if (signal === 'SELL') return <TrendingDown className="w-5 h-5" />;
    return <Minus className="w-5 h-5" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin mx-auto mb-4 text-cyan-400" />
          <p className="text-lg">Lade Marktdaten...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <div className="max-w-[1800px] mx-auto mb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold" style={{ color: '#2dd4bf' }} data-testid="dashboard-title">
                Rohstoff Trader
              </h1>
              {gpt5Active && (
                <Badge className="bg-gradient-to-r from-purple-600 to-pink-600 text-white flex items-center gap-1 px-3 py-1 animate-pulse" data-testid="gpt5-active-badge">
                  <Zap className="w-4 h-4" />
                  KI AKTIV
                </Badge>
              )}
              {!gpt5Active && settings?.auto_trading && (
                <Badge className="bg-slate-700 text-slate-400 flex items-center gap-1 px-3 py-1">
                  <ZapOff className="w-4 h-4" />
                  KI Inaktiv
                </Badge>
              )}
            </div>
            <p className="text-base md:text-lg text-slate-400">Multi-Commodity Trading mit KI-Analyse</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Label className="text-sm text-slate-400">Live-Ticker</Label>
              <Switch
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>
            <Button
              onClick={handleRefresh}
              disabled={refreshing}
              variant="outline"
              className="border-cyan-500/30 hover:bg-cyan-500/10 hover:border-cyan-400"
              data-testid="refresh-button"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Aktualisieren
            </Button>
            <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="border-slate-600 hover:bg-slate-700" data-testid="settings-button">
                  <Settings className="w-4 h-4 mr-2" />
                  Einstellungen
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-2xl">Trading Einstellungen</DialogTitle>
                </DialogHeader>
                <SettingsForm settings={settings} onSave={handleUpdateSettings} commodities={commodities} balance={balance} />
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto">
        {/* AI Status Indicator */}
        {settings?.use_ai_analysis && (
          <Card className={`p-4 mb-6 border-2 transition-all duration-300 ${
            aiProcessing 
              ? 'bg-gradient-to-r from-purple-900/40 to-pink-900/40 border-purple-500/50 animate-pulse' 
              : 'bg-slate-900/60 border-slate-700/30'
          }`} data-testid="ai-status-indicator">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`relative flex h-3 w-3 ${aiProcessing ? '' : 'opacity-40'}`}>
                  {aiProcessing && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                  )}
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${
                    aiProcessing ? 'bg-purple-500' : 'bg-slate-500'
                  }`}></span>
                </div>
                <div>
                  <p className="text-sm font-semibold flex items-center gap-2">
                    <Zap className={`w-4 h-4 ${aiProcessing ? 'text-purple-400' : 'text-slate-500'}`} />
                    KI-Analyse Status
                  </p>
                  <p className="text-xs text-slate-400">
                    {aiProcessing ? (
                      <span className="text-purple-300">🤖 KI analysiert Marktdaten...</span>
                    ) : (
                      <span>Bereit für Analyse | Provider: {settings?.ai_provider || 'emergent'}</span>
                    )}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <Badge variant="outline" className={`${
                  aiProcessing 
                    ? 'border-purple-500/50 text-purple-300 bg-purple-900/30' 
                    : 'border-slate-600 text-slate-400'
                }`}>
                  {aiProcessing ? 'AKTIV' : 'BEREIT'}
                </Badge>
                {settings?.ai_provider === 'ollama' && (
                  <p className="text-xs text-slate-500 mt-1">🏠 Lokal auf Ihrem Mac</p>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Platform Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {/* MT5 Balance Card */}
          <Card className="bg-gradient-to-br from-blue-900/20 to-slate-900/90 border-blue-700/50 backdrop-blur-sm p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings?.mode === 'MT5'}
                  onChange={(e) => {
                    if (e.target.checked) {
                      handleUpdateSettings({ ...settings, mode: 'MT5' });
                    }
                  }}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <h3 className="text-lg font-bold text-blue-400">🔷 MT5 Konto</h3>
                {mt5Connected && settings?.mode === 'MT5' && (
                  <Badge className="bg-emerald-600 text-white text-xs">Aktiv</Badge>
                )}
              </div>
              <DollarSign className="w-10 h-10 text-blue-400/20" />
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-slate-400">Balance</p>
                <p className="text-2xl font-bold text-white">
                  {mt5Connected ? `€${mt5Account?.balance?.toFixed(2) || '0.00'}` : '€0.00'}
                </p>
              </div>
              {mt5Connected && (
                <>
                  <div className="text-xs text-slate-400">
                    Equity: €{mt5Account?.equity?.toFixed(2)} | Freie Margin: €{mt5Account?.free_margin?.toFixed(2)}
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Portfolio-Risiko (MT5):</span>
                      <span className={
                        (totalExposure / (mt5Account?.balance || 1)) * 100 > (settings?.max_portfolio_risk_percent || 20)
                          ? 'text-red-400 font-semibold'
                          : 'text-green-400'
                      }>
                        {((totalExposure / (mt5Account?.balance || 1)) * 100).toFixed(1)}% / {settings?.max_portfolio_risk_percent || 20}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          (totalExposure / (mt5Account?.balance || 1)) * 100 > (settings?.max_portfolio_risk_percent || 20)
                            ? 'bg-red-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(((totalExposure / (mt5Account?.balance || 1)) * 100 / (settings?.max_portfolio_risk_percent || 20)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Offene Positionen: €{totalExposure.toFixed(2)}
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* Bitpanda Balance Card */}
          <Card className="bg-gradient-to-br from-green-900/20 to-slate-900/90 border-green-700/50 backdrop-blur-sm p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings?.mode === 'BITPANDA'}
                  onChange={(e) => {
                    if (e.target.checked) {
                      handleUpdateSettings({ ...settings, mode: 'BITPANDA' });
                    }
                  }}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <h3 className="text-lg font-bold text-green-400">🟢 Bitpanda</h3>
                {settings?.mode === 'BITPANDA' && (
                  <Badge className="bg-emerald-600 text-white text-xs">Aktiv</Badge>
                )}
              </div>
              <DollarSign className="w-10 h-10 text-green-400/20" />
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-slate-400">Balance</p>
                <p className="text-2xl font-bold text-white">€0.00</p>
              </div>
              <div className="text-xs text-slate-400">
                Nur lokal auf Mac verfügbar
              </div>
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-400">Portfolio-Risiko (Bitpanda):</span>
                  <span className="text-slate-500">0.0% / 20%</span>
                </div>
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '0%' }} />
                </div>
              </div>
              <div className="text-xs text-slate-400">
                Offene Positionen: €0.00
              </div>
            </div>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="cards" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="cards">📊 Rohstoffe</TabsTrigger>
            <TabsTrigger value="trades">📈 Trades ({trades.length})</TabsTrigger>
            <TabsTrigger value="charts">📉 Charts</TabsTrigger>
          </TabsList>

          {/* Tab 1: Commodity Cards */}
          <TabsContent value="cards">
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
          {Object.entries(allMarkets).map(([commodityId, market]) => {
            const commodity = commodities[commodityId];
            if (!commodity) return null;
            
            return (
              <Card key={commodityId} className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 border-slate-700/50 backdrop-blur-sm p-4 shadow-2xl" data-testid={`commodity-card-${commodityId}`}>
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-cyan-400" />
                      <h3 className="text-lg font-semibold text-slate-200">{commodity.name}</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      {autoRefresh && (
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                      )}
                      <button
                        onClick={() => {
                          setSelectedCommodity({id: commodityId, ...commodity, marketData: allMarkets[commodityId]});
                          setChartModalOpen(true);
                        }}
                        className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
                        title="Chart anzeigen"
                      >
                        <LineChart className="w-5 h-5 text-cyan-400" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">{commodity.category}</p>
                  {settings?.mode === 'MT5' && !['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM'].includes(commodityId) && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-green-400 bg-green-500/10 border border-green-500/30 rounded px-2 py-1">
                      <AlertCircle className="w-3 h-3" />
                      <span>✓ Auf Bitpanda handelbar</span>
                    </div>
                  )}
                  {settings?.mode === 'BITPANDA' && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-green-400 bg-green-500/10 border border-green-500/30 rounded px-2 py-1">
                      <AlertCircle className="w-3 h-3" />
                      <span>✓ Handelbar</span>
                    </div>
                  )}
                </div>
                
                <div className="mb-3">
                  <h2 className="text-2xl font-bold mb-0.5" style={{ color: '#2dd4bf' }} data-testid={`price-${commodityId}`}>
                    ${market.price?.toFixed(2) || '0.00'}
                  </h2>
                  <p className="text-xs text-slate-500">{commodity.unit}</p>
                </div>
                
                <div className="flex items-center justify-between mb-3">
                  <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border ${market.signal === 'BUY' ? 'border-emerald-500/50' : market.signal === 'SELL' ? 'border-rose-500/50' : 'border-slate-600/50'}`}>
                    <span className={getSignalColor(market.signal)}>
                      {getSignalIcon(market.signal)}
                    </span>
                    <span className={`text-sm font-bold ${getSignalColor(market.signal)}`}>
                      {market.signal || 'HOLD'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400">
                    {market.trend === 'UP' && <TrendingUp className="w-4 h-4 text-emerald-400 inline" />}
                    {market.trend === 'DOWN' && <TrendingDown className="w-4 h-4 text-rose-400 inline" />}
                    {market.trend === 'NEUTRAL' && <Minus className="w-4 h-4 text-slate-400 inline" />}
                  </div>
                </div>
                
                <div className="mt-3 flex gap-2">
                  <Button
                    onClick={() => handleManualTrade('BUY', commodityId)}
                    size="sm"
                    className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    <TrendingUp className="w-3 h-3 mr-1" />
                    KAUFEN
                  </Button>
                  <Button
                    onClick={() => handleManualTrade('SELL', commodityId)}
                    size="sm"
                    className="flex-1 bg-rose-600 hover:bg-rose-500 text-white"
                  >
                    <TrendingDown className="w-3 h-3 mr-1" />
                    VERKAUFEN
                  </Button>
                </div>
              </Card>
            );
          })}
            </div>
          </TabsContent>

          {/* Tab 2: Trades */}
          <TabsContent value="trades">
            <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4 text-cyan-400">Trade Historie</h3>
              {trades.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <p>Noch keine Trades vorhanden</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-800/50 border-b border-slate-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-300">Rohstoff</th>
                        <th className="px-4 py-3 text-left text-slate-300">Typ</th>
                        <th className="px-4 py-3 text-right text-slate-300">Einstieg</th>
                        <th className="px-4 py-3 text-right text-slate-300">Aktuell</th>
                        <th className="px-4 py-3 text-right text-slate-300">Menge</th>
                        <th className="px-4 py-3 text-right text-slate-300">P&L</th>
                        <th className="px-4 py-3 text-center text-slate-300">Plattform</th>
                        <th className="px-4 py-3 text-center text-slate-300">Status</th>
                        <th className="px-4 py-3 text-center text-slate-300">Aktion</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((trade) => {
                        const commodity = commodities[trade.commodity];
                        const currentPrice = allMarkets[trade.commodity]?.price || trade.entry_price;
                        const pl = trade.status === 'OPEN' 
                          ? (trade.type === 'BUY' ? currentPrice - trade.entry_price : trade.entry_price - currentPrice) * trade.quantity
                          : trade.profit_loss || 0;
                        
                        return (
                          <tr key={trade.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                            <td className="px-4 py-3 text-slate-200">{commodity?.name || trade.commodity}</td>
                            <td className="px-4 py-3">
                              <Badge className={trade.type === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                                {trade.type}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right text-slate-200">${trade.entry_price?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">${currentPrice?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">{trade.quantity}</td>
                            <td className={`px-4 py-3 text-right font-semibold ${pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {pl >= 0 ? '+' : ''}{pl.toFixed(2)} €
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge className={trade.mode === 'MT5' ? 'bg-blue-600' : 'bg-green-600'}>
                                {trade.mode}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge className={trade.status === 'OPEN' ? 'bg-yellow-600' : 'bg-gray-600'}>
                                {trade.status}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={() => handleDeleteTrade(trade.id, `${commodity?.name || trade.commodity} ${trade.type}`)}
                                className="text-red-400 hover:text-red-300 text-xs"
                                title="Trade löschen"
                              >
                                🗑️ Löschen
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </TabsContent>

          {/* Tab 3: Charts */}
          <TabsContent value="charts">
            <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4 text-cyan-400">Markt Charts</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {Object.entries(allMarkets).slice(0, 4).map(([commodityId, market]) => {
                  const commodity = commodities[commodityId];
                  if (!commodity) return null;
                  
                  return (
                    <Card key={commodityId} className="bg-slate-800/50 border-slate-700 p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-semibold text-slate-200">{commodity.name}</h4>
                        <button
                          onClick={() => {
                            setSelectedCommodity({id: commodityId, ...commodity, marketData: market});
                            setChartModalOpen(true);
                          }}
                          className="text-cyan-400 hover:text-cyan-300"
                        >
                          <LineChart className="w-5 h-5" />
                        </button>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-cyan-400">
                          ${market.price?.toFixed(2) || '0.00'}
                        </p>
                        <p className="text-sm text-slate-400">{commodity.unit}</p>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </Card>
          </TabsContent>
        </Tabs>
        
        {/* Portfolio Exposure Warning */}
        {totalExposure > (balance * 0.2) && (
          <Card className="bg-amber-900/20 border-amber-500/50 p-4 mb-8">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-amber-400" />
              <div className="flex-1">
                <h4 className="font-semibold text-amber-400">Portfolio-Risiko-Warnung</h4>
                <p className="text-sm text-slate-300 mb-2">
                  <strong>Offene Positionen:</strong> €{totalExposure.toFixed(2)} ({((totalExposure / balance) * 100).toFixed(1)}% Ihrer Balance)
                </p>
                <p className="text-xs text-slate-400">
                  • Ihre Balance: €{balance.toFixed(2)}<br/>
                  • Empfohlenes Maximum (20%): €{(balance * 0.2).toFixed(2)}<br/>
                  • Sie sollten Positionen reduzieren, um Risiko zu minimieren
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-total-trades">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Gesamt Trades</p>
              <BarChart3 className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{stats?.total_trades || 0}</p>
            <p className="text-xs text-slate-500 mt-1">
              Offen: {stats?.open_positions || 0} | Geschlossen: {stats?.closed_positions || 0}
            </p>
          </Card>

          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-profit-loss">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Gewinn / Verlust</p>
              <DollarSign className="w-5 h-5 text-cyan-400" />
            </div>
            <p className={`text-3xl font-bold ${stats?.total_profit_loss >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              ${stats?.total_profit_loss?.toFixed(2) || '0.00'}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Win: {stats?.winning_trades || 0} | Loss: {stats?.losing_trades || 0}
            </p>
          </Card>

          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-win-rate">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Trefferquote</p>
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{stats?.win_rate?.toFixed(1) || '0.0'}%</p>
            <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
              <div
                className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${stats?.win_rate || 0}%` }}
              />
            </div>
          </Card>

          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="trading-mode-card">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Trading Modus</p>
              {settings?.auto_trading ? <Play className="w-5 h-5 text-emerald-400" /> : <Pause className="w-5 h-5 text-slate-400" />}
            </div>
            <p className="text-2xl font-bold text-white mb-1">{settings?.mode || 'PAPER'}</p>
            <p className={`text-sm ${settings?.auto_trading ? 'text-emerald-400' : 'text-slate-400'}`}>
              {settings?.auto_trading ? 'Auto-Trading Aktiv' : 'Manueller Modus'}
            </p>
          </Card>
        </div>

        {/* Old tabs section removed - now using new 3-tab structure above */}
      </div>

      {/* Chart Modal */}
      <Dialog open={chartModalOpen} onOpenChange={setChartModalOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] bg-slate-900 border-slate-700 overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-cyan-400 flex items-center gap-2">
              <LineChart className="w-6 h-6" />
              {selectedCommodity?.name} - Detaillierte Analyse
            </DialogTitle>
          </DialogHeader>
          
          {selectedCommodity && (
            <div className="space-y-6 mt-4">
              {/* Price Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Aktueller Preis</p>
                  <p className="text-2xl font-bold text-white">
                    ${selectedCommodity.marketData?.price?.toFixed(2) || 'N/A'}
                  </p>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">24h Änderung</p>
                  <p className={`text-2xl font-bold ${selectedCommodity.marketData?.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {selectedCommodity.marketData?.change24h >= 0 ? '+' : ''}{selectedCommodity.marketData?.change24h?.toFixed(2) || 'N/A'}%
                  </p>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Signal</p>
                  <Badge className={
                    selectedCommodity.marketData?.signal === 'BUY' ? 'bg-green-600' :
                    selectedCommodity.marketData?.signal === 'SELL' ? 'bg-red-600' :
                    'bg-slate-600'
                  }>
                    {selectedCommodity.marketData?.signal || 'HOLD'}
                  </Badge>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Trend</p>
                  <div className="flex items-center gap-2">
                    {selectedCommodity.marketData?.trend === 'UP' && <TrendingUp className="w-5 h-5 text-green-400" />}
                    {selectedCommodity.marketData?.trend === 'DOWN' && <TrendingDown className="w-5 h-5 text-red-400" />}
                    {selectedCommodity.marketData?.trend === 'NEUTRAL' && <Minus className="w-5 h-5 text-slate-400" />}
                    <span className="font-semibold">{selectedCommodity.marketData?.trend || 'NEUTRAL'}</span>
                  </div>
                </div>
              </div>

              {/* Large Chart */}
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <h3 className="text-lg font-semibold mb-4 text-cyan-400">Preisverlauf (100 Tage)</h3>
                {historicalData.length > 0 ? (
                  <div className="h-96">
                    <PriceChart data={historicalData} commodityName={selectedCommodity.name} />
                  </div>
                ) : (
                  <div className="h-96 flex items-center justify-center text-slate-400">
                    Lade Chart-Daten...
                  </div>
                )}
              </Card>

              {/* Technical Indicators */}
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <h3 className="text-lg font-semibold mb-4 text-cyan-400">Technische Indikatoren</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">RSI</p>
                    <p className="text-xl font-bold">{selectedCommodity.marketData?.rsi?.toFixed(2) || 'N/A'}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {selectedCommodity.marketData?.rsi > 70 ? 'Überkauft' :
                       selectedCommodity.marketData?.rsi < 30 ? 'Überverkauft' : 'Neutral'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">MACD</p>
                    <p className="text-xl font-bold">{selectedCommodity.marketData?.macd?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">SMA 20</p>
                    <p className="text-xl font-bold">${selectedCommodity.marketData?.sma_20?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">EMA 20</p>
                    <p className="text-xl font-bold">${selectedCommodity.marketData?.ema_20?.toFixed(2) || 'N/A'}</p>
                  </div>
                </div>
              </Card>

              {/* Commodity Info */}
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <h3 className="text-lg font-semibold mb-4 text-cyan-400">Informationen</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Kategorie</p>
                    <p className="text-base font-semibold">{selectedCommodity.category}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Einheit</p>
                    <p className="text-base font-semibold">{selectedCommodity.unit || selectedCommodity.marketData?.unit || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Verfügbar auf</p>
                    <div className="flex gap-2">
                      {['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM'].includes(selectedCommodity.id) ? (
                        <>
                          <Badge className="bg-blue-600">MT5</Badge>
                          <Badge className="bg-green-600">Bitpanda</Badge>
                        </>
                      ) : (
                        <Badge className="bg-green-600">Bitpanda</Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Letztes Update</p>
                    <p className="text-base font-semibold">
                      {selectedCommodity.marketData?.timestamp ? 
                        new Date(selectedCommodity.marketData.timestamp).toLocaleString('de-DE') : 'N/A'}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Trading Actions */}
              <div className="flex gap-4">
                <Button
                  onClick={() => {
                    setChartModalOpen(false);
                    handleManualTrade('BUY', selectedCommodity.id);
                  }}
                  className="flex-1 bg-green-600 hover:bg-green-500"
                >
                  <TrendingUp className="w-4 h-4 mr-2" />
                  KAUFEN
                </Button>
                <Button
                  onClick={() => {
                    setChartModalOpen(false);
                    handleManualTrade('SELL', selectedCommodity.id);
                  }}
                  className="flex-1 bg-red-600 hover:bg-red-500"
                >
                  <TrendingDown className="w-4 h-4 mr-2" />
                  VERKAUFEN
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const SettingsForm = ({ settings, onSave, commodities, balance }) => {
  const [formData, setFormData] = useState(settings || { enabled_commodities: ['WTI_CRUDE'] });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const aiProviderModels = {
    emergent: ['gpt-5', 'gpt-4-turbo', 'gpt-4'],
    openai: ['gpt-5', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
    gemini: ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
    ollama: ['llama2', 'llama3', 'mistral', 'mixtral', 'codellama', 'phi', 'neural-chat', 'starling-lm', 'orca-mini']
  };

  const currentProvider = formData.ai_provider || 'emergent';
  const availableModels = aiProviderModels[currentProvider] || ['gpt-5'];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        {/* AI Analysis Section */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg flex items-center gap-2">
            <Zap className="w-5 h-5 text-cyan-400" />
            KI-Analyse Einstellungen
          </h4>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="use_ai_analysis" className="text-base">KI-Analyse verwenden</Label>
            <Switch
              id="use_ai_analysis"
              checked={formData.use_ai_analysis !== false}
              onCheckedChange={(checked) => setFormData({ ...formData, use_ai_analysis: checked })}
              data-testid="ai-analysis-switch"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="ai_provider">KI Provider</Label>
            <select
              id="ai_provider"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={currentProvider}
              onChange={(e) => setFormData({ 
                ...formData, 
                ai_provider: e.target.value,
                ai_model: aiProviderModels[e.target.value][0] // Reset to first model of new provider
              })}
              data-testid="ai-provider-select"
            >
              <option value="emergent">Emergent LLM Key (Universal)</option>
              <option value="openai">OpenAI API</option>
              <option value="gemini">Google Gemini API</option>
              <option value="anthropic">Anthropic Claude API</option>
              <option value="ollama">Ollama (Lokal)</option>
            </select>
            <p className="text-xs text-slate-500">
              {currentProvider === 'emergent' && '✨ Emergent Universal Key - Funktioniert mit OpenAI, Gemini & Claude'}
              {currentProvider === 'openai' && '🔑 Eigene OpenAI API Key verwenden'}
              {currentProvider === 'gemini' && '🔑 Eigene Google Gemini API Key verwenden'}
              {currentProvider === 'anthropic' && '🔑 Eigene Anthropic API Key verwenden'}
              {currentProvider === 'ollama' && '🏠 Lokales LLM auf Ihrem Mac (Ollama erforderlich)'}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="ai_model">KI Model</Label>
            <select
              id="ai_model"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={formData.ai_model || availableModels[0]}
              onChange={(e) => setFormData({ ...formData, ai_model: e.target.value })}
              data-testid="ai-model-select"
            >
              {availableModels.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>

          {/* API Key fields based on provider */}
          {currentProvider === 'openai' && (
            <div className="space-y-2">
              <Label htmlFor="openai_api_key">OpenAI API Key</Label>
              <Input
                id="openai_api_key"
                type="password"
                value={formData.openai_api_key || ''}
                onChange={(e) => setFormData({ ...formData, openai_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="sk-..."
              />
              <p className="text-xs text-slate-500">Holen Sie sich Ihren API Key auf platform.openai.com</p>
            </div>
          )}

          {currentProvider === 'gemini' && (
            <div className="space-y-2">
              <Label htmlFor="gemini_api_key">Google Gemini API Key</Label>
              <Input
                id="gemini_api_key"
                type="password"
                value={formData.gemini_api_key || ''}
                onChange={(e) => setFormData({ ...formData, gemini_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="AIza..."
              />
              <p className="text-xs text-slate-500">Holen Sie sich Ihren API Key auf aistudio.google.com</p>
            </div>
          )}

          {currentProvider === 'anthropic' && (
            <div className="space-y-2">
              <Label htmlFor="anthropic_api_key">Anthropic API Key</Label>
              <Input
                id="anthropic_api_key"
                type="password"
                value={formData.anthropic_api_key || ''}
                onChange={(e) => setFormData({ ...formData, anthropic_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="sk-ant-..."
              />
              <p className="text-xs text-slate-500">Holen Sie sich Ihren API Key auf console.anthropic.com</p>
            </div>
          )}

          {currentProvider === 'ollama' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ollama_base_url">Ollama Server URL</Label>
                <Input
                  id="ollama_base_url"
                  type="text"
                  value={formData.ollama_base_url || 'http://localhost:11434'}
                  onChange={(e) => setFormData({ ...formData, ollama_base_url: e.target.value })}
                  className="bg-slate-800 border-slate-700"
                  placeholder="http://localhost:11434"
                />
                <p className="text-xs text-slate-500">Standard Ollama URL ist http://localhost:11434</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="ollama_model">Ollama Model</Label>
                <select
                  id="ollama_model"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
                  value={formData.ollama_model || 'llama2'}
                  onChange={(e) => {
                    setFormData({ 
                      ...formData, 
                      ollama_model: e.target.value,
                      ai_model: e.target.value 
                    });
                  }}
                  data-testid="ollama-model-select"
                >
                  {aiProviderModels.ollama.map(model => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">
                  Stellen Sie sicher, dass das Modell mit 'ollama pull {formData.ollama_model || 'llama2'}' installiert ist
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Trading Settings */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg">Trading Einstellungen</h4>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="auto_trading" className="text-base">Auto-Trading aktivieren</Label>
            <Switch
              id="auto_trading"
              checked={formData.auto_trading || false}
              onCheckedChange={(checked) => setFormData({ ...formData, auto_trading: checked })}
              data-testid="auto-trading-switch"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="mode">Aktive Plattform</Label>
            <select
              id="mode"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={formData.mode || 'MT5'}
              onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
              data-testid="mode-select"
            >
              <option value="MT5">🔷 MetaTrader 5 (11 Rohstoffe)</option>
              <option value="BITPANDA">🟢 Bitpanda (Krypto & Rohstoffe)</option>
            </select>
            <p className="text-xs text-slate-500">
              {formData.mode === 'MT5' && 'Echtes Trading über MetaTrader 5 - 11 Rohstoffe verfügbar'}
              {formData.mode === 'BITPANDA' && 'Echtes Trading über Bitpanda - Alle Rohstoffe verfügbar'}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="default_platform">Standard-Plattform für neue Trades</Label>
            <select
              id="default_platform"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={formData.default_platform || 'MT5'}
              onChange={(e) => setFormData({ ...formData, default_platform: e.target.value })}
            >
              <option value="MT5">🔷 MetaTrader 5</option>
              <option value="BITPANDA">🟢 Bitpanda</option>
            </select>
            <p className="text-xs text-slate-500">
              Plattform, die für neue automatische Trades verwendet wird
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stop_loss">Stop Loss (%)</Label>
              <Input
                id="stop_loss"
                type="number"
                step="0.1"
                min="0.1"
                value={formData.stop_loss_percent ?? 2.0}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormData({ ...formData, stop_loss_percent: val === '' ? '' : parseFloat(val) || 2.0 });
                }}
                onBlur={(e) => {
                  if (e.target.value === '') {
                    setFormData({ ...formData, stop_loss_percent: 2.0 });
                  }
                }}
                className="bg-slate-800 border-slate-700"
                data-testid="stop-loss-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="take_profit">Take Profit (%)</Label>
              <Input
                id="take_profit"
                type="number"
                step="0.1"
                min="0.1"
                value={formData.take_profit_percent ?? 4.0}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormData({ ...formData, take_profit_percent: val === '' ? '' : parseFloat(val) || 4.0 });
                }}
                onBlur={(e) => {
                  if (e.target.value === '') {
                    setFormData({ ...formData, take_profit_percent: 4.0 });
                  }
                }}
                className="bg-slate-800 border-slate-700"
                data-testid="take-profit-input"
              />
            </div>
          </div>

          {/* Trailing Stop Settings */}
          <div className="space-y-4 mt-6">
            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <div className="flex-1">
                <Label htmlFor="trailing_stop" className="text-base font-semibold">Trailing Stop aktivieren</Label>
                <p className="text-sm text-slate-400 mt-1">
                  Stop Loss folgt automatisch dem Preis und sichert Gewinne ab
                </p>
              </div>
              <Switch
                id="trailing_stop"
                checked={formData.use_trailing_stop || false}
                onCheckedChange={(checked) => setFormData({ ...formData, use_trailing_stop: checked })}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>

            {formData.use_trailing_stop && (
              <div className="space-y-2 pl-4">
                <Label htmlFor="trailing_distance">Trailing Stop Distanz (%)</Label>
                <Input
                  id="trailing_distance"
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="10"
                  value={formData.trailing_stop_distance || 1.5}
                  onChange={(e) => setFormData({ ...formData, trailing_stop_distance: parseFloat(e.target.value) })}
                  className="bg-slate-800 border-slate-700"
                  placeholder="z.B. 1.5"
                />
                <p className="text-xs text-slate-500">
                  Stop Loss hält {formData.trailing_stop_distance || 1.5}% Abstand zum aktuellen Preis
                </p>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="max_trades">Max. Trades pro Stunde</Label>
            <Input
              id="max_trades"
              type="number"
              min="1"
              value={formData.max_trades_per_hour ?? 3}
              onChange={(e) => {
                const val = e.target.value;
                setFormData({ ...formData, max_trades_per_hour: val === '' ? '' : parseInt(val) || 3 });
              }}
              onBlur={(e) => {
                // Set default value on blur if empty
                if (e.target.value === '') {
                  setFormData({ ...formData, max_trades_per_hour: 3 });
                }
              }}
              className="bg-slate-800 border-slate-700"
              data-testid="max-trades-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="position_size">Positionsgröße</Label>
            <Input
              id="position_size"
              type="number"
              step="0.1"
              value={formData.position_size || 1.0}
              onChange={(e) => setFormData({ ...formData, position_size: parseFloat(e.target.value) })}
              className="bg-slate-800 border-slate-700"
              data-testid="position-size-input"
            />
          </div>
        </div>

        {/* Commodity Selection */}
        <div className="space-y-4 mt-6">
          <h4 className="font-semibold text-lg">Rohstoff-Auswahl</h4>
          <p className="text-sm text-slate-400">Wählen Sie die Rohstoffe aus, die gehandelt werden sollen:</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(commodities).map(([id, commodity]) => (
              <div key={id} className="flex items-center space-x-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <input
                  type="checkbox"
                  id={`commodity_${id}`}
                  checked={formData.enabled_commodities?.includes(id) || false}
                  onChange={(e) => {
                    const enabled = formData.enabled_commodities || ['WTI_CRUDE'];
                    if (e.target.checked) {
                      setFormData({ ...formData, enabled_commodities: [...enabled, id] });
                    } else {
                      setFormData({ ...formData, enabled_commodities: enabled.filter(c => c !== id) });
                    }
                  }}
                  className="w-4 h-4 text-emerald-600 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                />
                <label htmlFor={`commodity_${id}`} className="flex-1 cursor-pointer">
                  <div className="font-medium text-slate-200">{commodity.name}</div>
                  <div className="text-xs text-slate-500">{commodity.category} • {commodity.unit}</div>
                </label>
              </div>
            ))}
          </div>
          
          <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 text-amber-400 mb-2">
              <AlertCircle className="w-4 h-4" />
              <span className="font-medium">Portfolio-Risiko</span>
            </div>
            <p className="text-sm text-slate-400">
              Max. 20% des Gesamtguthabens ({(balance * 0.2).toFixed(2)} EUR) für alle offenen Positionen zusammen
            </p>
          </div>
        </div>

        {/* MT5 Settings */}
        {formData.mode === 'MT5' && (
          <div className="space-y-4 mt-6">
            <h4 className="font-semibold text-lg flex items-center gap-2">
              <span className="text-2xl">🔷</span>
              MetaTrader 5 Credentials
            </h4>
            <div className="space-y-2">
              <Label htmlFor="mt5_login">MT5 Login</Label>
              <Input
                id="mt5_login"
                type="text"
                value={formData.mt5_login || ''}
                onChange={(e) => setFormData({ ...formData, mt5_login: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="MT5 Account Login"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mt5_password">MT5 Passwort</Label>
              <Input
                id="mt5_password"
                type="password"
                value={formData.mt5_password || ''}
                onChange={(e) => setFormData({ ...formData, mt5_password: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="MT5 Account Passwort"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mt5_server">MT5 Server</Label>
              <Input
                id="mt5_server"
                type="text"
                value={formData.mt5_server || ''}
                onChange={(e) => setFormData({ ...formData, mt5_server: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="MT5 Server Adresse"
              />
            </div>
          </div>
        )}

        {/* Bitpanda Settings */}
        {formData.mode === 'BITPANDA' && (
          <div className="space-y-4 mt-6">
            <h4 className="font-semibold text-lg flex items-center gap-2">
              <span className="text-2xl">🟢</span>
              Bitpanda Pro Credentials
            </h4>
            <div className="space-y-2">
              <Label htmlFor="bitpanda_email">Bitpanda Email</Label>
              <Input
                id="bitpanda_email"
                type="email"
                value={formData.bitpanda_email || ''}
                onChange={(e) => setFormData({ ...formData, bitpanda_email: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="ihre.email@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="bitpanda_api_key">Bitpanda API Key</Label>
              <Input
                id="bitpanda_api_key"
                type="password"
                value={formData.bitpanda_api_key || ''}
                onChange={(e) => setFormData({ ...formData, bitpanda_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="Ihr Bitpanda API Key"
              />
              <p className="text-xs text-slate-500">
                Erstellen Sie einen API Key in Ihrem Bitpanda Pro Account unter Einstellungen → API Keys
              </p>
            </div>
          </div>
        )}
      </div>

      <Button type="submit" className="w-full bg-cyan-600 hover:bg-cyan-500" data-testid="save-settings-button">
        Einstellungen speichern
      </Button>
    </form>
  );
};

export default Dashboard;