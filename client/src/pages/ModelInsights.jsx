import { useState, useEffect } from 'react';
import { modelService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { formatNumber } from '../utils/helpers';
import { Brain, BarChart3, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

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
    <div className="space-y-6">
      <h1>🧠 Model Insights & Explainability</h1>
      <p className="text-gray-500 text-sm -mt-4">Understand how the forecasting model works — feature importance and performance.</p>

      {/* Model Info */}
      {modelInfo && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Best Model" value={modelInfo.model_type.replace('_', ' ')} icon={Brain} color="blue" />
          <KpiCard label="MAE" value={modelInfo.mae?.toFixed(2) || '—'} icon={BarChart3} color="green" />
          <KpiCard label="RMSE" value={modelInfo.rmse?.toFixed(2) || '—'} icon={TrendingUp} color="orange" />
          <KpiCard label="MAPE" value={modelInfo.mape ? `${modelInfo.mape.toFixed(2)}%` : '—'} icon={BarChart3} color="purple" />
        </div>
      )}

      {/* Feature Importance */}
      <div className="content-section">
        <div className="content-section-title">Feature Importance</div>
        {features && features.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={features.slice(0, 15)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="feature" type="category" width={150} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="importance" fill="#2563EB" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm">No feature importance data available. Train a model first.</p>
        )}
      </div>

      {/* Model History */}
      <div className="content-section">
        <div className="content-section-title">Training History</div>
        {history && history.length > 0 ? (
          <div className="overflow-x-auto max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 font-medium text-gray-500">Model</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">MAE</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">RMSE</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">MAPE</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">R²</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Features</th>
                  <th className="text-center py-2 px-3 font-medium text-gray-500">Best</th>
                </tr>
              </thead>
              <tbody>
                {history.map((m, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{m.model_type.replace('_', ' ')}</td>
                    <td className="py-2 px-3 text-right">{m.mae?.toFixed(2) || '—'}</td>
                    <td className="py-2 px-3 text-right">{m.rmse?.toFixed(2) || '—'}</td>
                    <td className="py-2 px-3 text-right">{m.mape ? `${m.mape.toFixed(2)}%` : '—'}</td>
                    <td className="py-2 px-3 text-right">{m.r2?.toFixed(4) || '—'}</td>
                    <td className="py-2 px-3 text-right">{m.feature_count || '—'}</td>
                    <td className="py-2 px-3 text-center">{m.is_best ? <span className="text-green-600 font-bold">✓</span> : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-sm">No training history available.</p>
        )}
      </div>
    </div>
  );
}
