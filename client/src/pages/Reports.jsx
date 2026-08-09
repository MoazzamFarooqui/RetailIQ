import { useState } from 'react';
import { reportsService } from '../services';
import { FileText, FileDown, FileSpreadsheet, Eye } from 'lucide-react';
import { ErrorState } from '../components/common/LoadingState';

const REPORT_TYPES = [
  { id: 'executive', label: 'Executive Report', desc: 'Revenue, growth, inventory value, risks, actions' },
  { id: 'inventory', label: 'Inventory Report', desc: 'Reorder decisions, stockouts, overstock, financials' },
  { id: 'forecast', label: 'Forecast Report', desc: 'Active model, accuracy, forecast performance' },
  { id: 'ai_insights', label: 'AI Insights Report', desc: 'Advisor narrative on the business state' },
];

export default function Reports() {
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);

  const download = async (type, format) => {
    setLoading(`${type}-${format}`);
    setError(null);
    const filename = `retailiq_${type}.${format}`;
    const mime = format === 'pdf' ? 'application/pdf' : 'text/csv';

    const saveBlob = (data) => {
      const blob = data instanceof Blob ? data : new Blob([data], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      // Force the save dialog even if the browser would rather open inline.
      a.target = '_blank';
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    };

    try {
      const res = await reportsService.export(type, format, { include_advisor: type === 'ai_insights' });
      // A non-blob payload means an error page or JSON leaked through —
      // never hand that to the downloader as a valid file.
      if (!(res.data instanceof Blob)) {
        throw new Error('Unexpected export response');
      }
      saveBlob(res.data);
    } catch (e) {
      const detail =
        (e.response?.data?.detail) ||
        (e.response?.data instanceof Blob ? 'Export failed' : null) ||
        e.message ||
        'Export failed';
      if (detail === 'Unexpected export response') {
        // The proxy swallowed the binary download (e.g. dev-server quirk);
        // fall back to a direct browser download using the JWT.
        setError('Export response was not a file — falling back to direct download…');
        const token = localStorage.getItem('access_token');
        const query = new URLSearchParams({ format, include_advisor: String(type === 'ai_insights') });
        const href = `/api/v1/reports/${type}/export?${query}`;
        try {
          const res2 = await fetch(href, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (!res2.ok) throw new Error('Export failed');
          const data = await res2.blob();
          saveBlob(data);
          setError(null);
        } catch (e2) {
          setError(detail);
        }
      } else {
        setError(detail);
      }
    } finally {
      setLoading(null);
    }
  };

  const previewReport = async (type) => {
    setLoading(`preview-${type}`);
    setError(null);
    try {
      const res = await reportsService.get(type, { include_advisor: type === 'ai_insights' });
      setPreview({ type, ...res.data });
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load report');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in floating-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Professional reports you can share with management, with auto-generated summaries</p>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      <div className="grid md:grid-cols-2 gap-4 section-gap">
        {REPORT_TYPES.map((r) => (
          <div key={r.id} className="card p-5 flex flex-col">
            <div className="flex items-center gap-3 mb-1">
              <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-slate-600" />
              </div>
              <h3 className="font-semibold text-slate-900">{r.label}</h3>
            </div>
            <p className="text-sm text-slate-500 mb-4 flex-1">{r.desc}</p>
            <div className="flex gap-2">
              <button
                onClick={() => previewReport(r.id)}
                disabled={loading === `preview-${r.id}`}
                className="btn-ghost"
              >
                <Eye size={14} /> Preview
              </button>
              <button
                onClick={() => download(r.id, 'pdf')}
                disabled={loading === `${r.id}-pdf`}
                className="btn-primary"
              >
                <FileDown size={14} /> PDF
              </button>
              <button
                onClick={() => download(r.id, 'csv')}
                disabled={loading === `${r.id}-csv`}
                className="btn-success"
              >
                <FileSpreadsheet size={14} /> CSV
              </button>
            </div>
          </div>
        ))}
      </div>

      {preview && (
        <div className="content-section">
          <div className="flex items-center justify-between mb-4">
            <div className="content-section-title mb-0">{preview.type.replace('_', ' ')} Report</div>
            <button onClick={() => setPreview(null)} className="text-sm text-slate-500 hover:text-slate-700">✕</button>
          </div>
          <div className="space-y-4 text-sm">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Summary</div>
              <p className="text-slate-700">{preview.summary}</p>
            </div>
            {preview.executive && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(preview.executive).filter(([k]) => ['total_sales', 'revenue', 'growth_pct', 'forecast_accuracy_wape'].includes(k)).map(([k, v]) => (
                  <div key={k} className="card p-3">
                    <div className="kpi-card-value">
                      {typeof v === 'number' ? (k === 'revenue' ? `$${v.toLocaleString()}` : k.includes('growth') || k.includes('wape') ? `${v}%` : v.toLocaleString()) : '—'}
                    </div>
                    <div className="kpi-card-label capitalize mt-1">{k.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>
            )}
            {preview.actions?.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Priority Actions</div>
                <ul className="space-y-1">
                  {preview.actions.slice(0, 5).map((a, i) => (
                    <li key={i} className="text-slate-700">• {a.title} — {a.detail}</li>
                  ))}
                </ul>
              </div>
            )}
            {preview.advisor_answer && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Advisor Narrative</div>
                <p className="text-slate-700 whitespace-pre-wrap">{preview.advisor_answer}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

