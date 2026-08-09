import { useState, useEffect } from 'react';
import { intelligenceService } from '../services';
import { Store, TrendingUp, TrendingDown } from 'lucide-react';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState, EmptyState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';

export default function Stores() {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    intelligenceService.stores()
      .then((res) => setStores(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load stores'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner message="Loading store intelligence..." />;
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;

  const totalSales = stores.reduce((acc, s) => acc + (s.total_sales || 0), 0);
  const totalRevenue = stores.reduce((acc, s) => acc + (s.revenue || 0), 0);
  const avgGrowth =
    stores.length > 0
      ? stores.reduce((acc, s) => acc + (s.growth_pct || 0), 0) / stores.filter((s) => s.growth_pct !== null && s.growth_pct !== undefined).length
      : 0;

  return (
    <div className="space-y-8 animate-fade-in floating-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Store Intelligence</h1>
          <p className="page-subtitle">Deep-dive analytics across every store in your network</p>
        </div>
      </div>

      {/* KPI Row */}
      {stores.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 section-gap">
          <KpiCard label="Stores" value={formatNumber(stores.length)} icon={Store} color="blue" />
          <KpiCard label="Units Sold" value={formatNumber(totalSales)} icon={TrendingUp} color="green" />
          <KpiCard label="Total Revenue" value={totalRevenue > 0 ? `$${formatNumber(Math.round(totalRevenue))}` : '—'} icon={TrendingUp} color="orange" />
          <KpiCard label="Avg Growth" value={Number.isFinite(avgGrowth) ? `${avgGrowth >= 0 ? '+' : ''}${avgGrowth.toFixed(1)}%` : '—'} icon={TrendingUp} color="purple" aiInsight />
        </div>
      )}

      {stores.length === 0 ? (
        <EmptyState icon={Store} message="No store data yet. Upload data first." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {stores.map((s) => (
            <div key={s.store_id} className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                    <Store className="w-4 h-4 text-slate-600" />
                  </div>
                  <h3 className="font-semibold text-slate-900">{s.store_id}</h3>
                </div>
                {s.growth_pct !== null && s.growth_pct !== undefined ? (
                  <span className={`badge ${s.growth_pct >= 0 ? 'badge-ok' : 'badge-critical'}`}>
                    {s.growth_pct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    {s.growth_pct >= 0 ? '+' : ''}{s.growth_pct}%
                  </span>
                ) : null}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="kpi-card-value">{formatNumber(s.total_sales)}</div>
                  <div className="kpi-card-label">Units sold</div>
                </div>
                <div>
                  <div className="kpi-card-value">{s.revenue !== null && s.revenue !== undefined ? `$${formatNumber(Math.round(s.revenue))}` : '—'}</div>
                  <div className="kpi-card-label">Revenue</div>
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700">{formatNumber(s.avg_daily_sales)}</div>
                  <div className="kpi-card-label">Avg daily</div>
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700">{formatNumber(s.products)}</div>
                  <div className="kpi-card-label">Products</div>
                </div>
              </div>
              {s.peak_day && (
                <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                  Peak day: <span className="font-medium text-slate-600">{s.peak_day}</span>
                  {s.weather_sensitivity !== null && s.weather_sensitivity !== undefined && (
                    <> · Weather sensitivity: <span className="font-medium text-slate-600">{s.weather_sensitivity}</span></>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

