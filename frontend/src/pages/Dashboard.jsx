import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, BarChart3, Settings, RefreshCw, Play, Pause, Zap, ZapOff } from 'lucide-react';
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
  const [historicalData, setHistoricalData] = useState([]);
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [settings, setSettings] = useState(null);
  const [balance, setBalance] = useState(10000); // Simulated balance
  const [mt5Account, setMt5Account] = useState(null); // Real MT5 account data
  const [mt5Connected, setMt5Connected] = useState(false);
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
        refreshMarketData(); // This will trigger backend to fetch new data
        fetchTrades();
        fetchStats();
        updateBalance();
        fetchMT5Account(); // Fetch real MT5 data
      }
    }, 10000);  // Every 10 seconds

    return () => clearInterval(liveInterval);
  }, [autoRefresh]);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      refreshMarketData(), // Use refresh instead of just fetching cached data
      fetchHistoricalData(),
      fetchTrades(),
      fetchStats(),
      fetchSettings(),
      fetchMT5Account() // Fetch real MT5 account data
    ]);
    setLoading(false);
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

  const handleManualTrade = async (type) => {
    if (!marketData) return;
    
    try {
      await axios.post(`${API}/trades/execute?trade_type=${type}&price=${marketData.price}&quantity=1`);
      toast.success(`${type} Order ausgeführt`);
      fetchTrades();
      fetchStats();
    } catch (error) {
      toast.error('Fehler beim Ausführen der Order');
    }
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
    } catch (error) {
      toast.error('Fehler beim Speichern');
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
                WTI Smart Trader
              </h1>
              {gpt5Active && (
                <Badge className="bg-gradient-to-r from-purple-600 to-pink-600 text-white flex items-center gap-1 px-3 py-1 animate-pulse" data-testid="gpt5-active-badge">
                  <Zap className="w-4 h-4" />
                  GPT-5 AKTIV
                </Badge>
              )}
              {!gpt5Active && settings?.auto_trading && (
                <Badge className="bg-slate-700 text-slate-400 flex items-center gap-1 px-3 py-1">
                  <ZapOff className="w-4 h-4" />
                  KI Inaktiv
                </Badge>
              )}
            </div>
            <p className="text-base md:text-lg text-slate-400">Automatisierter Rohöl-Handel mit GPT-5 KI</p>
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
                <SettingsForm settings={settings} onSave={handleUpdateSettings} />
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

        {/* Balance Card */}
        <Card className="bg-gradient-to-r from-emerald-900/30 to-cyan-900/30 border-emerald-500/30 p-6 mb-6" data-testid="balance-card">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm text-slate-400">
                  {mt5Connected && settings?.mode === 'MT5' ? 'MT5 Konto' : 'Paper Trading'}
                </p>
                {mt5Connected && settings?.mode === 'MT5' && (
                  <Badge variant="success" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">
                    ✓ Verbunden
                  </Badge>
                )}
                {settings?.mode === 'PAPER' && (
                  <Badge variant="secondary" className="bg-slate-500/20 text-slate-400 border-slate-500/50">
                    Simulation
                  </Badge>
                )}
              </div>
              <h2 className="text-4xl font-bold text-emerald-400" data-testid="current-balance">
                {mt5Account && settings?.mode === 'MT5' 
                  ? `€${balance.toFixed(2)}` 
                  : `$${balance.toFixed(2)}`}
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                {mt5Connected && settings?.mode === 'MT5' ? (
                  <>
                    Equity: €{mt5Account?.equity?.toFixed(2)} | Margin: €{mt5Account?.margin?.toFixed(2)}
                    {mt5Account?.trade_mode && (
                      <span className={mt5Account.trade_mode === 'REAL' ? 'text-amber-400 ml-2' : 'text-blue-400 ml-2'}>
                        [{mt5Account.trade_mode}]
                      </span>
                    )}
                  </>
                ) : (
                  <>
                    Startwert: $10,000.00 | P/L: 
                    <span className={stats?.total_profit_loss >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                      {' '}${stats?.total_profit_loss?.toFixed(2) || '0.00'}
                    </span>
                  </>
                )}
              </p>
            </div>
            <DollarSign className="w-16 h-16 text-emerald-400/20" />
          </div>
        </Card>

        {/* Live Price & Signal Card */}
        <Card className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 border-slate-700/50 backdrop-blur-sm p-6 mb-8 shadow-2xl" data-testid="live-price-card">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-1">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                <p className="text-sm text-slate-400">Live WTI Preis</p>
                {autoRefresh && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                )}
              </div>
              <h2 className="text-5xl font-bold mb-1" style={{ color: '#2dd4bf' }} data-testid="current-price">
                ${marketData?.price?.toFixed(2) || '0.00'}
              </h2>
              <p className="text-xs text-slate-500">
                {marketData?.timestamp ? new Date(marketData.timestamp).toLocaleString('de-DE') : ''}
              </p>
            </div>
            
            <div className="md:col-span-1 flex flex-col justify-center">
              <div className="text-center">
                <p className="text-sm text-slate-400 mb-3">Aktuelles Signal</p>
                <div className={`inline-flex items-center gap-3 px-6 py-3 rounded-xl bg-slate-800/50 border-2 ${marketData?.signal === 'BUY' ? 'border-emerald-500/50' : marketData?.signal === 'SELL' ? 'border-rose-500/50' : 'border-slate-600/50'}`} data-testid="current-signal">
                  <span className={getSignalColor(marketData?.signal)}>
                    {getSignalIcon(marketData?.signal)}
                  </span>
                  <span className={`text-2xl font-bold ${getSignalColor(marketData?.signal)}`}>
                    {marketData?.signal || 'HOLD'}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Trend: <span className={marketData?.trend === 'UP' ? 'text-emerald-400' : marketData?.trend === 'DOWN' ? 'text-rose-400' : 'text-slate-400'}>{marketData?.trend || 'NEUTRAL'}</span>
                </p>
              </div>
            </div>

            <div className="md:col-span-1 flex flex-col justify-center">
              <div className="space-y-3">
                <Button
                  onClick={() => handleManualTrade('BUY')}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3"
                  data-testid="manual-buy-button"
                >
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Manuell KAUFEN
                </Button>
                <Button
                  onClick={() => handleManualTrade('SELL')}
                  className="w-full bg-rose-600 hover:bg-rose-500 text-white font-semibold py-3"
                  data-testid="manual-sell-button"
                >
                  <TrendingDown className="w-4 h-4 mr-2" />
                  Manuell VERKAUFEN
                </Button>
              </div>
            </div>
          </div>
        </Card>

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

        {/* Main Content Tabs */}
        <Tabs defaultValue="chart" className="space-y-6">
          <TabsList className="bg-slate-900/80 border border-slate-700/50 p-1">
            <TabsTrigger value="chart" className="data-[state=active]:bg-cyan-600" data-testid="tab-chart">Chart & Indikatoren</TabsTrigger>
            <TabsTrigger value="trades" className="data-[state=active]:bg-cyan-600" data-testid="tab-trades">Trades</TabsTrigger>
          </TabsList>

          <TabsContent value="chart" className="space-y-6">
            <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4 text-cyan-400">WTI Preisverlauf</h3>
              <PriceChart data={historicalData} marketData={marketData} />
            </Card>

            <IndicatorsPanel marketData={marketData} />
          </TabsContent>

          <TabsContent value="trades">
            <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4 text-cyan-400">Trade Historie</h3>
              <TradesTable trades={trades} onCloseTrade={handleCloseTrade} />
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

const SettingsForm = ({ settings, onSave }) => {
  const [formData, setFormData] = useState(settings || {});

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
            <Label htmlFor="mode">Trading Modus</Label>
            <select
              id="mode"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={formData.mode || 'PAPER'}
              onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
              data-testid="mode-select"
            >
              <option value="PAPER">Paper Trading (Simulation)</option>
              <option value="MT5">MetaTrader 5 (Live)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stop_loss">Stop Loss (%)</Label>
              <Input
                id="stop_loss"
                type="number"
                step="0.1"
                value={formData.stop_loss_percent || 2.0}
                onChange={(e) => setFormData({ ...formData, stop_loss_percent: parseFloat(e.target.value) })}
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
                value={formData.take_profit_percent || 4.0}
                onChange={(e) => setFormData({ ...formData, take_profit_percent: parseFloat(e.target.value) })}
                className="bg-slate-800 border-slate-700"
                data-testid="take-profit-input"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="max_trades">Max. Trades pro Stunde</Label>
            <Input
              id="max_trades"
              type="number"
              value={formData.max_trades_per_hour || 3}
              onChange={(e) => setFormData({ ...formData, max_trades_per_hour: parseInt(e.target.value) })}
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

        {/* MT5 Settings */}
        {formData.mode === 'MT5' && (
          <div className="space-y-4">
            <h4 className="font-semibold text-lg">MetaTrader 5 Credentials</h4>
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
      </div>

      <Button type="submit" className="w-full bg-cyan-600 hover:bg-cyan-500" data-testid="save-settings-button">
        Einstellungen speichern
      </Button>
    </form>
  );
};

export default Dashboard;