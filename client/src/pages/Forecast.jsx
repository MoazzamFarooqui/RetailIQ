import { useState } from 'react';
import { forecastService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { ErrorState } from '../components/common/LoadingState';
import { formatNumber, formatDate } from '../utils/helpers';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { TrendingUp, Calendar, Brain, Rocket } from 'lucide-react';

const tooltipStyle = {
  contentStyle: {
    borderRadius: '10px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 8px 24px -8px rgb(15 23 42 / 0.18)',
    fontSize: '12px',
  },
};

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
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Forecast</h1>
          <p className="page-subtitle">Generate demand predictions with weather, season, and holiday context</p>
        </div>
      </div>

      {/* Config */}
      <div className="content-section">
        <div className="content-section-title">Forecast Configuration</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="field-label">Product ID</label>
            <input type="text" value={itemId} onChange={e => setItemId(e.target.value)} className="input" placeholder="e.g. FOODS_3_090" />
          </div>
          <div>
            <label className="field-label">Store ID</label>
            <input type="text" value={storeId} onChange={e => setStoreId(e.target.value)} className="input" placeholder="e.g. CA_1" />
          </div>
          <div>
            <label className="field-label">Horizon (days)</label>
            <select value={horizon} onChange={e => setHorizon(Number(e.target.value))} className="select">
              <option value={7}>7 Days</option>
              <option value={30}>30 Days</option>
              <option value={90}>90 Days</option>
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={generateForecast} disabled={loading} className="btn-gradient w-full">
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Generating...
                </>
              ) : (
                <>
                  <Rocket className="w-4 h-4" />
                  Generate Forecast
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {/* Results */}
      {forecastResult && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard label="Total Forecast" value={formatNumber(Math.round(forecastResult.summary.total_forecast))} icon={TrendingUp} color="blue" />
            <KpiCard label="Avg Daily" value={formatNumber(Math.round(forecastResult.summary.avg_daily))} icon={Calendar} color="green" />
            <KpiCard label="Peak Day" value={formatDate(forecastResult.summary.peak_day)} sub={`${formatNumber(Math.round(forecastResult.summary.peak_value))} units`} icon={TrendingUp} color="orange" />
            <KpiCard label="Model" value={forecastResult.header.model_type.replace('_', ' ')} icon={Brain} color="purple" />
          </div>

          {/* Chart */}
          <div className="content-section">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="content-section-title mb-0">Forecast Visualization</div>
                <div className="text-xs text-slate-400 mt-0.5">
                  Predicted daily demand for {itemId} · {storeId} · {horizon} days
                </div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} tickFormatter={v => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <Tooltip {...tooltipStyle} />
                <Line type="monotone" dataKey="predicted_sales" stroke="#E53E3E" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} name="Forecast" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Forecast Table */}
          <div className="content-section">
            <div className="content-section-title">Forecast Details</div>
            <div className="scroll-thin max-h-64">
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th className="text-right">Predicted Sales</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecastResult.forecast?.map((f, i) => (
                      <tr key={i}>
                        <td>{formatDate(f.forecast_date)}</td>
                        <td className="num font-medium">{f.predicted_sales.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
