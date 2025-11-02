import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';

const PriceChart = ({ data, marketData }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] text-slate-500">
        <p>Keine Daten verfügbar</p>
      </div>
    );
  }

  const chartData = data.map(item => ({
    time: new Date(item.timestamp).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }),
    price: item.price,
    sma: item.sma_20,
    ema: item.ema_20
  }));

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
        <Legend 
          wrapperStyle={{ color: '#94a3b8' }}
          iconType="line"
        />
        <Area 
          type="monotone" 
          dataKey="price" 
          stroke="#2dd4bf" 
          strokeWidth={3}
          fill="url(#priceGradient)" 
          name="WTI Preis"
        />
        <Line 
          type="monotone" 
          dataKey="sma" 
          stroke="#f59e0b" 
          strokeWidth={2}
          dot={false}
          name="SMA (20)"
        />
        <Line 
          type="monotone" 
          dataKey="ema" 
          stroke="#8b5cf6" 
          strokeWidth={2}
          dot={false}
          name="EMA (20)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default PriceChart;