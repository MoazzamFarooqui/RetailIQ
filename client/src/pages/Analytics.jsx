import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Package, Store } from 'lucide-react';
import { analyticsService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#2563EB', '#16A34A', '#D97706', '#DC2626', '#805AD5', '#0EA5E9'];

const tooltipStyle = {
  contentStyle: {
    borderRadius: '10px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 8px 24px -8px rgb(15 23 42 / 0.18)',
    fontSize: '12px',
  },
};

function ChartCard({ title, subtitle, children, right }) {
  return (
    <div className="content-section">
      <div className="flex items-start justify-between mb-4 gap-4">
        <div>
          <div className="content-section-title mb-0">{title}</div>
          {subtitle && <div className="text-xs text-slate-400 mt-0.5">{subtitle}</div>}
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

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
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Sales & revenue performance across your retail network</p>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Sales" value={formatNumber(overview?.total_sales)} icon={BarChart3} color="blue" />
        <KpiCard label="Avg Daily" value={formatNumber(Math.round(overview?.avg_daily_sales || 0))} icon={TrendingUp} color="green" />
        <KpiCard label="Products" value={formatNumber(overview?.total_products)} icon={Package} color="orange" />
        <KpiCard label="Stores" value={formatNumber(overview?.total_stores)} icon={Store} color="purple" />
      </div>

      {/* Sales Trend */}
      <ChartCard
        title="Sales Trend"
        subtitle="Daily sales over the selected period"
        right={
          <select value={days} onChange={e => setDays(Number(e.target.value))} className="select w-auto">
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 180 days</option>
          </select>
        }
      >
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} tickFormatter={v => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={v => formatNumber(v)} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="sales" stroke="#2563EB" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} name="Sales" />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Products */}
        <ChartCard title="Top Products" subtitle="Highest-grossing items">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={topProducts.slice(0, 8)} layout="vertical" margin={{ left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={v => formatNumber(v)} />
              <YAxis dataKey="item_id" type="category" width={100} tick={{ fontSize: 10, fill: '#475569' }} tickLine={false} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="total_sales" fill="#2563EB" radius={[0, 6, 6, 0]} name="Total Sales" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Day of Week */}
        <ChartCard title="Sales by Day of Week" subtitle="Average daily sales per weekday">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={dayOfWeek}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={v => formatNumber(v)} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="avg_sales" radius={[6, 6, 0, 0]} name="Avg Sales">
                {dayOfWeek?.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Store Performance */}
      <ChartCard title="Store Performance" subtitle="Sales summary by store">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Store</th>
                <th className="text-right">Total Sales</th>
                <th className="text-right">Avg Daily</th>
                <th className="text-right">Products</th>
              </tr>
            </thead>
            <tbody>
              {stores?.map((s, i) => (
                <tr key={i}>
                  <td className="font-medium text-slate-800">
                    <span className="inline-flex items-center gap-2">
                      <span className="w-7 h-7 rounded-lg bg-slate-100 text-slate-500 text-[11px] font-semibold flex items-center justify-center">{i + 1}</span>
                      {s.store_id}
                    </span>
                  </td>
                  <td className="num font-medium">{formatNumber(s.total_sales)}</td>
                  <td className="num">{formatNumber(Math.round(s.avg_daily_sales))}</td>
                  <td className="num">{formatNumber(s.item_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* Seasonal */}
      {seasonal?.length > 0 && (
        <ChartCard title="Seasonal Breakdown" subtitle="Sales distribution by season">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={seasonal} dataKey="total_sales" nameKey="season" cx="50%" cy="50%" innerRadius={52} outerRadius={88} paddingAngle={3} label={({ season, percent }) => `${season} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {seasonal.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  );
}
