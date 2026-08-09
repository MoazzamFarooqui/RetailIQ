import { useState, useEffect } from 'react';
import { insightsService } from '../services/index';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { getSeasonEmoji } from '../utils/helpers';
import { Sparkles, Brain, Lightbulb, TrendingDown, PartyPopper, Loader2, CalendarDays, AlertCircle as AlertCircleIcon } from 'lucide-react';

const severityStyles = {
  info: {
    card: 'border-brand-500/20 bg-brand-500/10',
    badge: 'bg-brand-500/10 text-brand-400',
    icon: Brain,
  },
  warning: {
    card: 'border-amber-500/20 bg-amber-500/10',
    badge: 'bg-amber-500/10 text-amber-400',
    icon: TrendingDown,
  },
  error: {
    card: 'border-red-500/20 bg-red-500/10',
    badge: 'bg-red-500/10 text-red-400',
    icon: AlertCircleIcon,
  },
};

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

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">AI Insights</h1>
          <p className="page-subtitle">Automated analysis with season, weather, and holiday awareness</p>
        </div>
        <button onClick={generateInsights} disabled={generating} className="btn-gradient">
          {generating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Insights
            </>
          )}
        </button>
      </div>

      {/* Season Context */}
      {seasonContext && (
        <div className="content-section">
          <div className="content-section-title">Current Season Context</div>
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-[#18181B] to-[#27272A] text-white p-6">
              <div className="absolute -bottom-10 -right-10 w-44 h-44 rounded-full bg-white/[0.05] blur-2xl" />
              <div className="text-4xl mb-3 drop-shadow-[0_0_8px_rgba(255,255,255,0.25)]">{getSeasonEmoji(seasonContext.current_season)}</div>
              <div className="font-bold text-lg text-white">{seasonContext.current_season}</div>
              <p className="text-[#9CA3AF] text-sm mt-2 leading-relaxed max-w-sm">{seasonContext.season_advice}</p>
            </div>

            <div className="space-y-4">
              {seasonContext.high_demand_products?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-[#18181B] uppercase tracking-wider">High Demand</span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {seasonContext.high_demand_products.slice(0, 10).map((p, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold bg-[#18181B] text-white">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {seasonContext.low_demand_products?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Low Demand</span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {seasonContext.low_demand_products.slice(0, 10).map((p, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold bg-[#F4F4F5] text-[#71717A]">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {seasonContext.upcoming_holidays?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-[#475569] uppercase tracking-wider flex items-center gap-1">
                    <PartyPopper className="w-3.5 h-3.5" />
                    Upcoming Holidays
                  </span>
                  <div className="space-y-1.5 mt-1.5">
                    {seasonContext.upcoming_holidays.map((h, i) => (
                      <div key={i} className="text-sm flex items-center gap-2 justify-start text-left">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#475569]" />
                        <span className="font-medium text-slate-900">{h.name}</span>
                        <span className="text-slate-500">{h.date?.substring(0, 10)}</span>
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
        <div className="content-section-title">
          <Lightbulb className="w-4 h-4 text-slate-900" />
          Generated Insights
        </div>
        {insights && insights.length > 0 ? (
          <div className="space-y-3">
            {insights.map((insight, i) => {
              const style = severityStyles[insight.severity] || severityStyles.info;
              const Icon = style.icon;
              return (
                <div key={i} className={`p-4 sm:p-5 rounded-xl border ${style.card} animate-fade-in`}>
                  <div className="flex items-start gap-3.5">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${style.badge}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">{insight.category}</span>
                        <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                          <CalendarDays className="w-3 h-3" />
                          {new Date(insight.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="text-sm text-slate-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: insight.insight_text }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No insights generated yet. Click "Generate Insights" to start.</p>
        )}
      </div>
    </div>
  );
}


