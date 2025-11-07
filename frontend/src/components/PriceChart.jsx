import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';

const PriceChart = ({ data, commodityName = 'Commodity', isOHLCV = false }) => {
  // Debug: Log data to console
  console.log(`PriceChart für ${commodityName}:`, {
    dataPoints: data?.length,
    isOHLCV,
    firstItem: data?.[0],
    lastItem: data?.[data.length - 1]
  });

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] text-slate-500">
        <p>Keine Daten verfügbar</p>
      </div>
    );
  }

  // Format time based on data length (detect if intraday or daily)
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    if (data.length > 100) {
      // Long period - show date
      return date.toLocaleDateString('de-DE', { day: '2-digit', month: 'short' });
    } else if (data.length > 20) {
      // Medium period - show date and time
      return date.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', hour: '2-digit' });
    } else {
      // Short period - show time only
      return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    }
  };

  const chartData = data.map(item => {
    // Handle both old format (item.price) and new OHLCV format (item.close)
    const price = isOHLCV ? item.close : (item.price || item.close);
    
    return {
      time: formatTime(item.timestamp),
      price: price,
      high: item.high,
      low: item.low,
      open: item.open,
      sma: item.sma_20,
      ema: item.ema_20
    };
  });

  return (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
        <XAxis 
          dataKey="time" 
          stroke="#94a3b8" 
          style={{ fontSize: '12px' }}
          tick={{ fill: '#94a3b8' }}
        />
        <YAxis 
          stroke="#94a3b8" 
          style={{ fontSize: '12px' }}
          tick={{ fill: '#94a3b8' }}
          domain={['auto', 'auto']}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1e293b', 
            border: '1px solid #475569',
            borderRadius: '8px',
            color: '#e4e8f0'
          }}
          labelStyle={{ color: '#94a3b8' }}
        />
        {/* Legend entfernt - nur Preis wird angezeigt */}
        <Area 
          type="monotone" 
          dataKey="price" 
          stroke="#2dd4bf" 
          strokeWidth={3}
          fill="url(#priceGradient)" 
          name={`${commodityName} Preis`}
        />
        {/* SMA und EMA Linien entfernt - nur Preis wird angezeigt */}
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default PriceChart;