import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Package } from 'lucide-react';
import { analyticsService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber, DAYS } from '../utils/helpers';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#2563EB', '#38A169', '#D69E2E', '#E53E3E', '#805AD5', '#3182CE'];

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(90);

  useEffect(() => {
    Promise.all([
      analyticsService.overview(),
      analyticsService.salesTrend(days),
      analyticsService.topProducts(10),
      analyticsService.storePerformance(),
      analyticsService.seasonal(),
      analyticsService.dayOfWeek(),
    ])
      .then(([ov, trend, top, stores, seasonal, dow]) => {
        setData({
          overview: ov.data,
          trend: trend.data,
          topProducts: top.data,
          stores: stores.data,
          seasonal: seasonal.data,
          dayOfWeek: dow.data,
        });
      })
      .catch(e => setError(e.response?.data?.detail || 'Failed to load analytics'))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <LoadingSpinner message="Loading analytics..." />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const { overview, trend, topProducts, stores, seasonal, dayOfWeek } = data;

  return (
    <div className="space-y-6">
      <h1>📈 Sales & Revenue Analytics</h1>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Sales" value={formatNumber(overview?.total_sales)} icon={BarChart3} color="blue" />
        <KpiCard label="Avg Daily" value={formatNumber(Math.round(overview?.avg_daily_sales || 0))} icon={TrendingUp} color="green" />
        <KpiCard label="Products" value={formatNumber(overview?.total_products)} icon={Package} color="orange" />
        <KpiCard label="Stores" value={formatNumber(overview?.total_stores)} icon={BarChart3} color="purple" />
      </div>

      {/* Sales Trend */}
      <div className="content-section">
        <div className="flex items-center justify-between mb-4">
          <div className="content-section-title mb-0">Sales Trend</div>
          <select value={days} onChange={e => setDays(Number(e.target.value))} className="text-sm border border-gray-200 rounded-lg px-3 py-1.5">
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
            <option value={180}>180 days</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={v => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="sales" stroke="#2563EB" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Top Products */}
        <div className="content-section">
          <div className="content-section-title">Top Products</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={topProducts.slice(0, 8)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="item_id" type="category" width={90} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="total_sales" fill="#2563EB" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Day of Week */}
        <div className="content-section">
          <div className="content-section-title">Sales by Day of Week</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={dayOfWeek}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avg_sales" fill="#38A169" radius={[4, 4, 0, 0]}>
                {dayOfWeek?.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Store Performance */}
      <div className="content-section">
        <div className="content-section-title">Store Performance</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left py-3 px-4 font-medium text-gray-500">Store</th>
                <th className="text-right py-3 px-4 font-medium text-gray-500">Total Sales</th>
                <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Daily</th>
                <th className="text-right py-3 px-4 font-medium text-gray-500">Products</th>
              </tr>
            </thead>
            <tbody>
              {stores?.map((s, i) => (
                <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{s.store_id}</td>
                  <td className="py-3 px-4 text-right">{formatNumber(s.total_sales)}</td>
                  <td className="py-3 px-4 text-right">{formatNumber(Math.round(s.avg_daily_sales))}</td>
                  <td className="py-3 px-4 text-right">{formatNumber(s.item_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Seasonal */}
      {seasonal?.length > 0 && (
        <div className="content-section">
          <div className="content-section-title">Seasonal Breakdown</div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={seasonal} dataKey="total_sales" nameKey="season" cx="50%" cy="50%" outerRadius={80} label={({ season, percent }) => `${season} ${(percent * 100).toFixed(0)}%`}>
                {seasonal.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
