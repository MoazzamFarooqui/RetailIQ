import { useState, useEffect } from 'react';
import { Package, Store, Tags, MapPin, TrendingUp, BarChart3, Calendar, Layers, Upload as UploadIcon, Sparkles as SparklesIcon, Sun as SunIcon, Brain as BrainIcon } from 'lucide-react';
import { analyticsService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { ErrorState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';

const FEATURES = [
  { icon: UploadIcon, tint: 'bg-teal-50 text-brand-600', title: 'Upload & Validate', desc: 'Upload retail sales CSVs — auto-validate, clean, and append.' },
  { icon: SparklesIcon, tint: 'bg-violet-50 text-violet-600', title: 'AI Forecasting', desc: '7/30/90 day demand predictions with live context.' },
  { icon: Package, tint: 'bg-emerald-50 text-emerald-600', title: 'Inventory Optimization', desc: 'Safety stock, reorder points, EOQ, stockout prediction.' },
  { icon: SunIcon, tint: 'bg-amber-50 text-amber-600', title: 'Live Context', desc: 'Real-time weather and holiday integration.' },
  { icon: BrainIcon, tint: 'bg-rose-50 text-rose-600', title: 'Explainable AI', desc: 'SHAP-based prediction explanations.' },
  { icon: TrendingUp, tint: 'bg-sky-50 text-sky-600', title: 'Business Intelligence', desc: 'Revenue tracking, trend analysis, performance.' },
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
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Platform overview and key business metrics</p>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Products" value={overview ? formatNumber(overview.total_products) : '—'} icon={Package} loading={loading} />
        <KpiCard label="Stores" value={overview ? formatNumber(overview.total_stores) : '—'} icon={Store} color="green" loading={loading} />
        <KpiCard label="Categories" value={overview ? formatNumber(overview.total_categories) : '—'} icon={Tags} color="orange" loading={loading} />
        <KpiCard label="States" value={overview ? formatNumber(overview.total_states) : '—'} icon={MapPin} color="purple" loading={loading} />
      </div>

      {/* More KPIs */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Total Sales" value={formatNumber(overview.total_sales)} icon={BarChart3} color="blue" />
          <KpiCard label="Avg Daily Sales" value={formatNumber(Math.round(overview.avg_daily_sales))} icon={TrendingUp} color="green" />
          <KpiCard label="Time Series" value={formatNumber(overview.n_time_series)} icon={Layers} color="orange" />
          <KpiCard label="Date Range" value={overview.date_range?.split(' to ')[1] || '—'} sub={overview.date_range?.split(' to ')[0] || ''} icon={Calendar} color="purple" />
        </div>
      )}

      {/* Feature Cards */}
      <div className="content-section">
        <div className="content-section-title">Platform Capabilities</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="p-5 bg-slate-50/70 border border-slate-200 rounded-xl card-hover group">
              <div className={`w-10 h-10 rounded-lg ${f.tint} flex items-center justify-center mb-3 group-hover:scale-105 transition-transform`}>
                <f.icon className="w-5 h-5" />
              </div>
              <div className="font-semibold text-slate-900 mb-1">{f.title}</div>
              <div className="text-xs text-slate-500 leading-relaxed">{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
