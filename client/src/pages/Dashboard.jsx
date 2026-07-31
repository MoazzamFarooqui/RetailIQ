import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Package, Brain, Sparkles, Upload } from 'lucide-react';
import { analyticsService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber, formatDate } from '../utils/helpers';

const FEATURES = [
  { icon: '📤', title: 'Upload & Validate', desc: 'Upload retail sales CSVs — auto-validate, clean, and append.' },
  { icon: '🔮', title: 'AI Forecasting', desc: '7/30/90 day demand predictions with live context.' },
  { icon: '📦', title: 'Inventory Optimization', desc: 'Safety stock, reorder points, EOQ, stockout prediction.' },
  { icon: '🌤', title: 'Live Context', desc: 'Real-time weather and holiday integration.' },
  { icon: '🧠', title: 'Explainable AI', desc: 'SHAP-based prediction explanations.' },
  { icon: '📈', title: 'Business Intelligence', desc: 'Revenue tracking, trend analysis, performance.' },
];

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analyticsService.overview()
      .then(r => setOverview(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;

  return (
    <div className="space-y-6">
      <div>
        <h1>RetailIQ — Retail Intelligence Platform</h1>
        <p className="text-gray-500 text-sm mt-1">Dashboard overview and platform capabilities</p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Products" value={overview ? formatNumber(overview.total_products) : '—'} icon={Package} loading={loading} />
        <KpiCard label="Stores" value={overview ? formatNumber(overview.total_stores) : '—'} icon={BarChart3} color="green" loading={loading} />
        <KpiCard label="Categories" value={overview ? formatNumber(overview.total_categories) : '—'} icon={TrendingUp} color="orange" loading={loading} />
        <KpiCard label="States" value={overview ? formatNumber(overview.total_states) : '—'} icon={Brain} color="purple" loading={loading} />
      </div>

      {/* More KPIs */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Total Sales" value={formatNumber(overview.total_sales)} icon={TrendingUp} color="blue" />
          <KpiCard label="Avg Daily Sales" value={formatNumber(Math.round(overview.avg_daily_sales))} icon={BarChart3} color="green" />
          <KpiCard label="Time Series" value={formatNumber(overview.n_time_series)} icon={Package} color="orange" />
          <KpiCard label="Date Range" value={overview.date_range?.split(' to ')[1] || '—'} sub={overview.date_range?.split(' to ')[0] || ''} color="purple" />
        </div>
      )}

      {/* Feature Cards */}
      <div className="content-section">
        <div className="content-section-title">Platform Capabilities</div>
        <div className="grid md:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="p-4 bg-white rounded-xl border border-gray-100 hover:shadow-md hover:border-blue-200 transition-all text-center">
              <div className="text-2xl mb-2">{f.icon}</div>
              <div className="font-semibold text-gray-800 mb-1">{f.title}</div>
              <div className="text-xs text-gray-500 leading-relaxed">{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
