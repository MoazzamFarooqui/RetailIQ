import { useState } from 'react';
import { forecastService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { ErrorState } from '../components/common/LoadingState';
import { formatNumber, formatDate } from '../utils/helpers';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { TrendingUp, Calendar, Brain } from 'lucide-react';

export default function Forecast() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [itemId, setItemId] = useState('FOODS_3_090');
  const [storeId, setStoreId] = useState('CA_1');
  const [horizon, setHorizon] = useState(30);
  const [forecastResult, setForecastResult] = useState(null);

  const generateForecast = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await forecastService.generate({ item_id: itemId, store_id: storeId, horizon_days: horizon });
      setForecastResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate forecast');
    } finally {
      setLoading(false);
    }
  };

  const chartData = forecastResult?.forecast?.map(f => ({
    date: f.forecast_date,
    predicted_sales: f.predicted_sales,
    type: 'Forecast',
  })) || [];

  return (
    <div className="space-y-6">
      <h1>🔮 AI Demand Forecasting</h1>
      <p className="text-gray-500 text-sm -mt-4">Generate demand predictions with weather, season, and holiday context.</p>

      {/* Config */}
      <div className="content-section">
        <div className="content-section-title">Forecast Configuration</div>
        <div className="grid md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Product ID</label>
            <input type="text" value={itemId} onChange={e => setItemId(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Store ID</label>
            <input type="text" value={storeId} onChange={e => setStoreId(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Horizon (days)</label>
            <select value={horizon} onChange={e => setHorizon(Number(e.target.value))} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm">
              <option value={7}>7 Days</option>
              <option value={30}>30 Days</option>
              <option value={90}>90 Days</option>
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={generateForecast} disabled={loading} className="w-full py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm">
              {loading ? 'Generating...' : '🚀 Generate Forecast'}
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {/* Results */}
      {forecastResult && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="Total Forecast" value={formatNumber(Math.round(forecastResult.summary.total_forecast))} icon={TrendingUp} color="blue" />
            <KpiCard label="Avg Daily" value={formatNumber(Math.round(forecastResult.summary.avg_daily))} icon={Calendar} color="green" />
            <KpiCard label="Peak Day" value={formatDate(forecastResult.summary.peak_day)} sub={`${formatNumber(Math.round(forecastResult.summary.peak_value))} units`} icon={TrendingUp} color="orange" />
            <KpiCard label="Model" value={forecastResult.header.model_type.replace('_', ' ')} icon={Brain} color="purple" />
          </div>

          {/* Chart */}
          <div className="content-section">
            <div className="content-section-title">Forecast Visualization</div>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={v => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="predicted_sales" stroke="#E53E3E" strokeWidth={2} dot={false} name="Forecast" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Forecast Table */}
          <div className="content-section">
            <div className="content-section-title">Forecast Details</div>
            <div className="overflow-x-auto max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2 px-3 font-medium text-gray-500">Date</th>
                    <th className="text-right py-2 px-3 font-medium text-gray-500">Predicted Sales</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastResult.forecast?.map((f, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-2 px-3">{formatDate(f.forecast_date)}</td>
                      <td className="py-2 px-3 text-right font-medium">{f.predicted_sales.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
