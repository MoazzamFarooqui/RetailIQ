import { useState, useEffect } from 'react';
import { alertsService } from '../services';
import { AlertTriangle, CheckCircle2, BellRing, RefreshCw } from 'lucide-react';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, EmptyState, ErrorState } from '../components/common/LoadingState';

const SEVERITY_STYLES = {
  critical: 'badge-critical',
  high: 'badge-critical',
  medium: 'badge-low',
  low: 'badge-neutral',
  info: 'badge-ai',
};

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [counts, setCounts] = useState({ total: 0, unread: 0, critical: 0, high: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [includeResolved, setIncludeResolved] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [listRes, countsRes] = await Promise.all([
        alertsService.list({ include_resolved: includeResolved }),
        alertsService.counts(),
      ]);
      setAlerts(listRes.data);
      setCounts(countsRes.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [includeResolved]);

  const markRead = async (id) => {
    await alertsService.markRead(id);
    load();
  };
  const resolve = async (id) => {
    await alertsService.resolve(id);
    load();
  };
  const detect = async () => {
    await alertsService.detect();
    load();
  };

  const parseContext = (ctx) => {
    try { return JSON.parse(ctx || '{}'); } catch { return {}; }
  };

  return (
    <div className="space-y-8 animate-fade-in floating-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Smart Alerts</h1>
          <p className="page-subtitle">Events that need your attention, detected automatically</p>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={includeResolved} onChange={(e) => setIncludeResolved(e.target.checked)} />
            Show resolved
          </label>
          <button onClick={detect} className="btn-primary flex items-center gap-2">
            <RefreshCw size={15} /> Run detection
          </button>
        </div>
      </div>

      {/* Counts */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 section-gap">
        <KpiCard label="Total Open" value={counts.total} icon={BellRing} color="blue" />
        <KpiCard label="Unread" value={counts.unread} icon={BellRing} color="purple" />
        <KpiCard label="Critical" value={counts.critical} icon={AlertTriangle} color="red" />
        <KpiCard label="High" value={counts.high} icon={AlertTriangle} color="orange" />
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {loading ? (
        <LoadingSpinner message="Loading alerts..." />
      ) : alerts.length === 0 ? (
        <EmptyState icon={BellRing} message="No alerts. Run detection to scan for issues." />
      ) : (
        <div className="space-y-3 section-gap">
          {alerts.map((a) => {
            const ctx = parseContext(a.context);
            return (
              <div key={a.id} className={`card p-5 ${a.is_read ? 'opacity-70' : ''}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className={`badge ${SEVERITY_STYLES[a.severity] || 'badge-neutral'}`}>{a.severity}</span>
                      <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{a.alert_type.replace(/_/g, ' ')}</span>
                      <span className="text-[11px] text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                    <h3 className="font-semibold text-slate-900">{a.title}</h3>
                    <p className="text-sm text-slate-600 mt-0.5">{a.message}</p>
                    {ctx.item_id && (
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">Item: {ctx.item_id}</span>
                        {ctx.store_id && <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">Store: {ctx.store_id}</span>}
                        {ctx.days !== undefined && <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">{ctx.days}d</span>}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    {!a.is_read && (
                      <button onClick={() => markRead(a.id)} className="btn-outline text-xs">Mark read</button>
                    )}
                    {!a.is_resolved && (
                      <button onClick={() => resolve(a.id)} className="btn-success flex items-center gap-1 text-xs">
                        <CheckCircle2 size={13} /> Resolve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}