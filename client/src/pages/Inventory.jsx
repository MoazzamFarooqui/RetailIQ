import { useState } from 'react';
import { inventoryService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';
import { Package, AlertTriangle, TrendingUp, ShoppingCart, Rocket, AlertCircle, Boxes } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts';

const CRITICAL_RED = '#EF4444';
const STATUS_COLORS = { OK: '#18181B', LOW: '#71717A', CRITICAL: CRITICAL_RED, EXCESS: '#0EA5E9' };

const tooltipStyle = {
  contentStyle: {
    borderRadius: '10px',
    border: '1px solid #1f2937',
    background: '#0e1219',
    color: '#f8fafc',
    fontSize: '12px',
    boxShadow: '0 8px 24px -8px rgb(0 0 0 / 0.6)',
  },
};

function ChartCard({ title, subtitle, children }) {
  return (
    <div className="content-section">
      <div className="content-section-title">{title}</div>
      {subtitle && <div className="text-xs text-slate-500 -mt-3 mb-4">{subtitle}</div>}
      {children}
    </div>
  );
}

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
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Inventory</h1>
          <p className="page-subtitle">AI-powered recommendations with season & holiday demand multipliers</p>
        </div>
      </div>

      {/* Config */}
      <div className="content-section">
        <div className="content-section-title">Configuration</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="field-label">Service Level</label>
            <input type="number" step="0.01" min="0.8" max="0.999" value={config.serviceLevel}
              onChange={e => setConfig({...config, serviceLevel: parseFloat(e.target.value)})}
              className="input" />
          </div>
          <div>
            <label className="field-label">Lead Time (days)</label>
            <input type="number" min="1" max="60" value={config.leadTime}
              onChange={e => setConfig({...config, leadTime: parseInt(e.target.value)})}
              className="input" />
          </div>
          <div>
            <label className="field-label">Excess Threshold (days)</label>
            <input type="number" min="30" max="365" value={config.excessThreshold}
              onChange={e => setConfig({...config, excessThreshold: parseInt(e.target.value)})}
              className="input" />
          </div>
          <div>
            <label className="field-label">Sample Size</label>
            <input type="number" min="100" max="10000" step="100" value={config.sampleSize}
              onChange={e => setConfig({...config, sampleSize: parseInt(e.target.value)})}
              className="input" />
          </div>
          <div className="flex items-end">
            <button onClick={generate} disabled={loading} className="btn-gradient w-full">
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Analyzing...
                </>
              ) : (
                <>
                  <Rocket className="w-4 h-4" />
                  Generate Recommendations
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} />}
      {loading && <LoadingSpinner message="Analyzing inventory levels..." />}

      {result && (
        <>
          {/* KPI Row */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <KpiCard label="Total Items" value={formatNumber(metrics.total_items)} icon={Package} color="blue" />
            <KpiCard label="Healthy" value={formatNumber(metrics.items_ok)} sub={`${metrics.total_items > 0 ? ((metrics.items_ok/metrics.total_items)*100).toFixed(0) : 0}% of items`} icon={TrendingUp} color="green" />
            <KpiCard label="Low / Critical" value={formatNumber(metrics.items_low + metrics.items_critical)} sub={`${metrics.total_items > 0 ? (((metrics.items_low + metrics.items_critical)/metrics.total_items)*100).toFixed(0) : 0}% at risk`} icon={AlertTriangle} color="red" />
            <KpiCard label="Need Reorder" value={formatNumber(metrics.items_need_reorder)} icon={ShoppingCart} color="orange" />
            <KpiCard label="Avg Days of Stock" value={metrics.avg_days_of_stock.toFixed(1)} icon={Boxes} color="purple" />
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            {/* Status Distribution */}
            <ChartCard title="Status Distribution" subtitle="Share of items by inventory health">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={52} outerRadius={88} paddingAngle={3} labelLine={false} label={({ name, percent, x, y, textAnchor }) => (
                  <text x={x} y={y} textAnchor={textAnchor} fill={name === 'CRITICAL' ? CRITICAL_RED : '#374151'} fontSize={11} fontWeight={600}>
                    {`${name} ${(percent * 100).toFixed(0)}%`}
                  </text>
                )}>
                    {statusData.map((d, i) => <Cell key={i} fill={STATUS_COLORS[d.name] || '#999'} />)}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                  <Legend content={({ payload }) => (
                    <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 list-none mt-2">
                      {payload?.map((entry, index) => (
                        <li key={`legend-${index}`} className="flex items-center gap-1.5">
                          <span
                            style={{
                              width: 9,
                              height: 9,
                              borderRadius: '50%',
                              backgroundColor: entry.color,
                              display: 'inline-block',
                            }}
                          />
                          <span style={{ fontSize: 12, color: entry.name === 'CRITICAL' ? CRITICAL_RED : '#374151' }}>
                            {entry.name}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Count by Status */}
            <ChartCard title="Count by Status" subtitle="Number of items in each health category">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#374151' }} tickLine={false} axisLine={{ stroke: '#1f2937' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#374151' }} tickLine={false} axisLine={false} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} name="Items">
                    {statusData.map((d, i) => <Cell key={i} fill={STATUS_COLORS[d.name] || '#999'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          {/* Stockout predictions */}
          {result.stockout_predictions?.length > 0 && (
            <div className="content-section">
              <div className="content-section-title">
                <AlertCircle className="w-4 h-4 text-[#18181B]" />
                Stockout Predictions
              </div>
              <div className="scroll-thin max-h-72">
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Store</th>
                        <th className="text-right">Stock</th>
                        <th className="text-right">Days Left</th>
                        <th className="text-right">Predicted Date</th>
                        <th className="text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.stockout_predictions.map((s, i) => (
                        <tr key={i}>
                          <td className="font-medium text-white">{s.item_id}</td>
                          <td>{s.store_id}</td>
                          <td className="num">{formatNumber(s.current_stock)}</td>
                          <td className="num font-bold">{s.days_remaining.toFixed(0)}</td>
                          <td className="num">{s.predicted_stockout_date}</td>
                          <td className="text-center">
                            {s.is_critical
                              ? <span className="badge-critical">Critical</span>
                              : <span className="badge-low">Warning</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Overstock */}
          {result.overstock_items?.length > 0 && (
            <div className="content-section">
              <div className="content-section-title">
                <Boxes className="w-4 h-4 text-sky-500" />
                Overstock Detection
              </div>
              <p className="text-sm text-slate-400 mb-3">{result.overstock_items.length} items with excess inventory</p>
              <div className="scroll-thin max-h-72">
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th className="text-right">Stock</th>
                        <th className="text-right">Days of Stock</th>
                        <th className="text-right">Excess Units</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.overstock_items.map((o, i) => (
                        <tr key={i}>
                          <td className="font-medium text-white">{o.item_id}</td>
                          <td className="num">{formatNumber(o.current_stock)}</td>
                          <td className="num">{o.days_of_stock.toFixed(0)}</td>
                          <td className="num font-medium text-orange-400">{formatNumber(o.excess_units)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}


