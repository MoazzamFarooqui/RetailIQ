import { useState, useEffect } from 'react';
import { Package, Store, Tags, MapPin, TrendingUp, BarChart3, Calendar, Layers, Upload as UploadIcon, Sparkles as SparklesIcon, Sun as SunIcon, Brain as BrainIcon } from 'lucide-react';
import { analyticsService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { ErrorState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';

const FEATURES = [
  { icon: UploadIcon, title: 'Data Ingestion', desc: 'Upload retail sales CSVs — auto-validate, clean, and append.', ai: false },
  { icon: SparklesIcon, title: 'Demand Forecasting', desc: '7/30/90 day demand predictions with live context.', ai: true },
  { icon: Package, title: 'Inventory Optimization', desc: 'Safety stock, reorder points, EOQ, stockout prediction.', ai: false },
  { icon: SunIcon, title: 'Environmental Context', desc: 'Real-time weather and holiday integration.', ai: false },
  { icon: BrainIcon, title: 'Explainable AI', desc: 'SHAP-based prediction explanations.', ai: true },
  { icon: TrendingUp, title: 'Analytics & Reports', desc: 'Revenue tracking, trend analysis, performance.', ai: false },
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
    <div className="space-y-8 animate-fade-in floating-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Platform overview and key business metrics</p>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 section-gap">
        <KpiCard label="Total Products" value={overview ? formatNumber(overview.total_products) : '—'} icon={Package} loading={loading} />
        <KpiCard label="Stores" value={overview ? formatNumber(overview.total_stores) : '—'} icon={Store} loading={loading} />
        <KpiCard label="Categories" value={overview ? formatNumber(overview.total_categories) : '—'} icon={Tags} loading={loading} />
        <KpiCard label="States" value={overview ? formatNumber(overview.total_states) : '—'} icon={MapPin} loading={loading} />
      </div>

      {/* More KPIs */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 section-gap">
          <KpiCard label="Total Sales" value={formatNumber(overview.total_sales)} icon={BarChart3} aiInsight />
          <KpiCard label="Avg Daily Sales" value={formatNumber(Math.round(overview.avg_daily_sales))} icon={TrendingUp} />
          <KpiCard label="Time Series" value={formatNumber(overview.n_time_series)} icon={Layers} />
          <KpiCard
            label="Date Range"
            value={Array.isArray(overview.date_range) ? overview.date_range[1] || '—' : overview.date_range?.split(' to ')[1] || '—'}
            sub={Array.isArray(overview.date_range) ? overview.date_range[0] || '' : overview.date_range?.split(' to ')[0] || ''}
            icon={Calendar}
          />
        </div>
      )}

      {/* Feature Cards - Premium neutral styling */}
      <div className="content-section section-gap">
        <div className="content-section-title">Platform Capabilities</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-sm group cursor-pointer hover:border-neutral-400 hover:shadow-md transition-all duration-200">
              <div className="w-10 h-10 rounded-xl bg-[#F3F4F6] text-[#18181B] flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                <f.icon className="w-5 h-5" />
              </div>
              <div className="font-semibold text-[#111827] text-[0.95rem] mb-1">{f.title}</div>
              <div className="text-xs text-slate-500 leading-relaxed">{f.desc}</div>
              {f.ai && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 bg-[#18181B] text-white">
                  <span className="w-1.5 h-1.5 rounded-full bg-white"></span>
                  <span className="text-[11px] font-medium">AI Powered</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

