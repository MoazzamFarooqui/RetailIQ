import { useState } from 'react';
import { inventoryService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import StatusBadge from '../components/common/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber, formatDate } from '../utils/helpers';
import { Package, AlertTriangle, TrendingUp, ShoppingCart } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts';

const STATUS_COLORS = { OK: '#38A169', LOW: '#D69E2E', CRITICAL: '#E53E3E', EXCESS: '#3182CE' };

export default function Inventory() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [config, setConfig] = useState({ serviceLevel: 0.95, leadTime: 7, excessThreshold: 60, sampleSize: 2000 });

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await inventoryService.generateRecommendations({
        service_level: config.serviceLevel,
        lead_time_days: config.leadTime,
        excess_threshold_days: config.excessThreshold,
        sample_size: config.sampleSize,
      });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate recommendations');
    } finally {
      setLoading(false);
    }
  };

  const metrics = result?.metrics;
  const statusData = metrics ? [
    { name: 'OK', value: metrics.items_ok },
    { name: 'LOW', value: metrics.items_low },
    { name: 'CRITICAL', value: metrics.items_critical },
    { name: 'EXCESS', value: metrics.items_excess },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6">
      <h1>📦 Inventory Optimization</h1>
      <p className="text-gray-500 text-sm -mt-4">AI-powered inventory recommendations with season & holiday demand multipliers.</p>

      {/* Config */}
      <div className="content-section">
        <div className="content-section-title">Configuration</div>
        <div className="grid md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Service Level</label>
            <input type="number" step="0.01" min="0.8" max="0.999" value={config.serviceLevel}
              onChange={e => setConfig({...config, serviceLevel: parseFloat(e.target.value)})}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Lead Time (days)</label>
            <input type="number" min="1" max="60" value={config.leadTime}
              onChange={e => setConfig({...config, leadTime: parseInt(e.target.value)})}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Excess Threshold (days)</label>
            <input type="number" min="30" max="365" value={config.excessThreshold}
              onChange={e => setConfig({...config, excessThreshold: parseInt(e.target.value)})}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          </div>
          <div className="flex items-end">
            <button onClick={generate} disabled={loading}
              className="w-full py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm">
              {loading ? 'Analyzing...' : '🚀 Generate Recommendations'}
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} />}
      {loading && <LoadingSpinner message="Analyzing inventory levels..." />}

      {result && (
        <>
          {/* KPI Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <KpiCard label="Total Items" value={formatNumber(metrics.total_items)} icon={Package} color="blue" />
            <KpiCard label="Healthy" value={formatNumber(metrics.items_ok)} sub={`${metrics.total_items > 0 ? ((metrics.items_ok/metrics.total_items)*100).toFixed(0) : 0}%`} icon={TrendingUp} color="green" />
            <KpiCard label="Low / Critical" value={formatNumber(metrics.items_low + metrics.items_critical)} sub={`${metrics.total_items > 0 ? (((metrics.items_low + metrics.items_critical)/metrics.total_items)*100).toFixed(0) : 0}% at risk`} icon={AlertTriangle} color="red" />
            <KpiCard label="Need Reorder" value={formatNumber(metrics.items_need_reorder)} icon={ShoppingCart} color="orange" />
            <KpiCard label="Avg Days of Stock" value={metrics.avg_days_of_stock.toFixed(1)} icon={Package} color="purple" />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Status Distribution */}
            <div className="content-section">
              <div className="content-section-title">Status Distribution</div>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}>
                    {statusData.map((d, i) => <Cell key={i} fill={STATUS_COLORS[d.name] || '#999'} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Count by Status */}
            <div className="content-section">
              <div className="content-section-title">Count by Status</div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[4,4,0,0]}>
                    {statusData.map((d, i) => <Cell key={i} fill={STATUS_COLORS[d.name] || '#999'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Stockout predictions */}
          {result.stockout_predictions?.length > 0 && (
            <div className="content-section">
              <div className="content-section-title">⚠️ Stockout Predictions</div>
              <div className="overflow-x-auto max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 px-3 font-medium text-gray-500">Item</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-500">Store</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500">Stock</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500">Days Left</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500">Predicted Date</th>
                      <th className="text-center py-2 px-3 font-medium text-gray-500">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.stockout_predictions.map((s, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 px-3 font-medium">{s.item_id}</td>
                        <td className="py-2 px-3">{s.store_id}</td>
                        <td className="py-2 px-3 text-right">{formatNumber(s.current_stock)}</td>
                        <td className="py-2 px-3 text-right font-bold">{s.days_remaining.toFixed(0)}</td>
                        <td className="py-2 px-3 text-right">{s.predicted_stockout_date}</td>
                        <td className="py-2 px-3 text-center">{s.is_critical ? <span className="text-red-600 font-bold">CRITICAL</span> : <span className="text-yellow-600">Warning</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Overstock */}
          {result.overstock_items?.length > 0 && (
            <div className="content-section">
              <div className="content-section-title">📦 Overstock Detection</div>
              <p className="text-sm text-gray-500 mb-3">{result.overstock_items.length} items with excess inventory</p>
              <div className="overflow-x-auto max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 px-3 font-medium text-gray-500">Item</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500">Stock</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500">Days of Stock</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500">Excess Units</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.overstock_items.map((o, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 px-3 font-medium">{o.item_id}</td>
                        <td className="py-2 px-3 text-right">{formatNumber(o.current_stock)}</td>
                        <td className="py-2 px-3 text-right">{o.days_of_stock.toFixed(0)}</td>
                        <td className="py-2 px-3 text-right text-orange-600 font-medium">{formatNumber(o.excess_units)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
