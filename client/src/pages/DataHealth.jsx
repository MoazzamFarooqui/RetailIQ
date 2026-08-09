import { useState, useEffect } from 'react';
import { dataHealthService } from '../services';
import { Database, AlertTriangle } from 'lucide-react';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';

const PASS_TAG = (
  <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold bg-[#F3F4F6] text-[#374151] uppercase">
    <span className="w-1.5 h-1.5 rounded-full bg-[#16A34A]" />
    Pass
  </span>
);

const FAIL_TAG = (
  <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold bg-[#18181B] text-white uppercase">
    <span className="text-[10px] leading-none text-[#FF6B6B]">▲</span>
    Fail
  </span>
);

export default function DataHealth() {
  const [report, setReport] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([dataHealthService.report(), dataHealthService.anomalies()])
      .then(([r, a]) => { setReport(r.data); setAnomalies(a.data.anomalies || []); })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load data health'))
      .finally(() => setLoading(false));
  }, []);

  const scoreColor = (score) => (score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-500' : 'text-red-600');

  return (
    <div className="space-y-8 animate-fade-in floating-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Data Health Center</h1>
          <p className="page-subtitle">Quality scoring and anomaly detection on your data</p>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Assessing data health..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : (
        <div className="space-y-8 section-gap">
          {/* Score */}
          <div className="content-section flex items-center gap-6">
            <div className={`text-5xl font-bold tabular-nums ${scoreColor(report.score)}`}>{report.score}</div>
            <div>
              <div className="text-base font-semibold text-slate-900">Data Health Score</div>
              <p className="text-sm text-slate-500">{report.total_rows.toLocaleString()} rows assessed · {report.assessed_at}</p>
            </div>
          </div>

          {/* Checks */}
          <div className="content-section">
            <div className="content-section-title">Quality Checks</div>
            <div className="grid gap-3">
              {report.checks.map((c) => (
                <div key={c.check} className="flex items-start justify-between gap-4 border border-slate-100 rounded-xl p-4">
                  <div>
                    <div className="font-semibold text-sm text-slate-900 capitalize">{c.check.replace(/_/g, ' ')}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{c.detail}</div>
                  </div>
                  {c.status === 'pass' ? PASS_TAG : c.status === 'fail' ? FAIL_TAG : <span className="badge badge-neutral">{c.status}</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Anomalies */}
          <div className="content-section">
            <div className="flex items-center gap-2 content-section-title">
              <AlertTriangle className="w-4 h-4 text-slate-900" />
              Anomalies Detected ({anomalies.length})
            </div>
            {anomalies.length === 0 ? (
              <div className="text-sm text-slate-500 py-4 text-center">No anomalies detected.</div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Date</th>
                      <th className="text-right">Sales</th>
                      <th className="text-right">Expected</th>
                      <th className="text-right">Z-score</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {anomalies.slice(0, 30).map((a, i) => (
                      <tr key={i}>
                        <td className="font-medium text-slate-900 capitalize">{a.type.replace(/_/g, ' ')}</td>
                        <td>{a.date}</td>
                        <td className="num">{a.sales?.toLocaleString() ?? '—'}</td>
                        <td className="num">{a.expected?.toLocaleString() ?? '—'}</td>
                        <td className="num">{a.z_score ?? '—'}</td>
                        <td>
                          <span className={`badge ${
                            a.severity === 'high' ? 'badge-critical' : a.severity === 'medium' ? 'badge-low' : 'badge-neutral'
                          }`}>{a.severity}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
