import { useState, useEffect } from 'react';
import { insightsService } from '../services/index';
import KpiCard from '../components/common/KpiCard';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { getSeasonEmoji } from '../utils/helpers';
import { Sparkles, Brain, TrendingUp } from 'lucide-react';

export default function AIInsights() {
  const [seasonContext, setSeasonContext] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      insightsService.seasonContext(),
      insightsService.list(),
    ])
      .then(([ctx, list]) => {
        setSeasonContext(ctx.data);
        setInsights(list.data);
      })
      .catch(e => setError(e.response?.data?.detail || 'Failed to load insights'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const generateInsights = async () => {
    setGenerating(true);
    try {
      await insightsService.generate();
      const list = await insightsService.list();
      setInsights(list.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate insights');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading insights..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  const severityColors = {
    info: 'bg-blue-50 border-blue-100 text-blue-700',
    warning: 'bg-yellow-50 border-yellow-100 text-yellow-700',
    error: 'bg-red-50 border-red-100 text-red-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1>✨ AI Business Insights</h1>
          <p className="text-gray-500 text-sm mt-1">Automated analysis with season, weather, and holiday awareness.</p>
        </div>
        <button onClick={generateInsights} disabled={generating}
          className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 transition-all text-sm flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          {generating ? 'Generating...' : 'Generate Insights'}
        </button>
      </div>

      {/* Season Context */}
      {seasonContext && (
        <div className="content-section">
          <div className="content-section-title">Current Season Context</div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
              <div className="text-3xl mb-2">{getSeasonEmoji(seasonContext.current_season)}</div>
              <div className="font-semibold text-gray-800">{seasonContext.current_season}</div>
              <div className="text-sm text-gray-600 mt-1">{seasonContext.season_advice}</div>
            </div>
            <div className="space-y-2">
              {seasonContext.high_demand_products?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-green-600 uppercase">High Demand</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {seasonContext.high_demand_products.slice(0, 10).map((p, i) => (
                      <span key={i} className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs border border-green-200">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {seasonContext.low_demand_products?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-orange-600 uppercase">Low Demand</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {seasonContext.low_demand_products.slice(0, 10).map((p, i) => (
                      <span key={i} className="px-2 py-0.5 bg-orange-50 text-orange-700 rounded text-xs border border-orange-200">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {seasonContext.upcoming_holidays?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-purple-600 uppercase">Upcoming Holidays</span>
                  <div className="space-y-1 mt-1">
                    {seasonContext.upcoming_holidays.map((h, i) => (
                      <div key={i} className="text-sm flex items-center gap-2">
                        <span className="text-purple-500">•</span>
                        <span className="font-medium">{h.name}</span>
                        <span className="text-gray-400">{h.date?.substring(0, 10)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Insights List */}
      <div className="content-section">
        <div className="content-section-title">Generated Insights</div>
        {insights && insights.length > 0 ? (
          <div className="space-y-3">
            {insights.map((insight, i) => (
              <div key={i} className={`p-4 rounded-xl border ${severityColors[insight.severity] || 'bg-gray-50 border-gray-100'}`}>
                <div className="flex items-start gap-3">
                  <Brain className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">{insight.category}</span>
                      <span className="text-xs text-gray-400">{new Date(insight.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="text-sm" dangerouslySetInnerHTML={{ __html: insight.insight_text }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm">No insights generated yet. Click "Generate Insights" to start.</p>
        )}
      </div>
    </div>
  );
}
