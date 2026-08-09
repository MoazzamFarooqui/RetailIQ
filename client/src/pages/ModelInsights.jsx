import { useState, useEffect } from 'react';
import { modelService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';
import { Brain, BarChart3, TrendingUp, Activity, CheckCircle2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

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

export default function ModelInsights() {
  const [features, setFeatures] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      modelService.features().catch(() => ({ data: [] })),
      modelService.best().catch(() => null),
      modelService.history().catch(() => ({ data: [] })),
    ])
      .then(([f, m, h]) => {
        setFeatures(f.data);
        setModelInfo(m?.data || null);
        setHistory(h.data);
      })
      .catch(e => setError(e.response?.data?.detail || 'Failed to load model insights'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return <LoadingSpinner message="Loading model insights..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Model Insights</h1>
          <p className="page-subtitle">How the forecasting model works — feature importance and performance</p>
        </div>
      </div>

      {/* Model Info */}
      {modelInfo && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Best Model" value={modelInfo.model_type.replace('_', ' ')} icon={Brain} color="blue" />
          <KpiCard label="MAE" value={modelInfo.mae?.toFixed(2) || '—'} icon={BarChart3} color="green" />
          <KpiCard label="RMSE" value={modelInfo.rmse?.toFixed(2) || '—'} icon={TrendingUp} color="orange" />
          <KpiCard label="MAPE" value={modelInfo.mape ? `${modelInfo.mape.toFixed(2)}%` : '—'} icon={Activity} color="purple" />
        </div>
      )}

      {/* Feature Importance */}
      <div className="content-section">
        <div className="content-section-title">Feature Importance</div>
        <p className="text-xs text-slate-500 -mt-3 mb-4">Top features driving forecast predictions</p>
        {features && features.length > 0 ? (
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={features.slice(0, 15)} layout="vertical" margin={{ left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <YAxis dataKey="feature" type="category" width={150} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="importance" fill="#4a6cf7" radius={[0, 6, 6, 0]} name="Importance" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-slate-500 text-sm">No feature importance data available. Train a model first.</p>
        )}
      </div>

      {/* Model History */}
      <div className="content-section">
        <div className="content-section-title">Training History</div>
        {history && history.length > 0 ? (
          <div className="scroll-thin max-h-72">
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th className="text-right">MAE</th>
                    <th className="text-right">RMSE</th>
                    <th className="text-right">MAPE</th>
                    <th className="text-right">R²</th>
                    <th className="text-right">Features</th>
                    <th className="text-center">Best</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((m, i) => (
                    <tr key={i}>
                      <td className="font-medium text-white">{m.model_type.replace('_', ' ')}</td>
                      <td className="num">{m.mae?.toFixed(2) || '—'}</td>
                      <td className="num">{m.rmse?.toFixed(2) || '—'}</td>
                      <td className="num">{m.mape ? `${m.mape.toFixed(2)}%` : '—'}</td>
                      <td className="num">{m.r2?.toFixed(4) || '—'}</td>
                      <td className="num">{m.feature_count || '—'}</td>
                      <td className="text-center">
                        {m.is_best
                          ? <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-xs"><CheckCircle2 className="w-4 h-4" />Best</span>
                          : <span className="text-slate-300">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No training history available.</p>
        )}
      </div>
    </div>
  );
}

