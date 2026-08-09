export default function KpiCard({ label, value, sub, icon: Icon, color = 'blue', loading, aiInsight }) {
  if (loading) {
    return (
      <div className="kpi-card animate-pulse">
        <div className="h-3 bg-stone-100 rounded w-1/2 mb-2" />
        <div className="h-8 bg-stone-100 rounded w-3/4 mb-1" />
        {sub && <div className="h-3 bg-stone-100/70 rounded w-1/3" />}
      </div>
    );
  }

  return (
    <div className="kpi-card group relative overflow-hidden">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center flex-shrink-0 group-hover:bg-indigo-50 transition-colors">
              <Icon className="w-5 h-5 text-slate-600" />
            </div>
          )}
          <span className="kpi-card-label">{label}</span>
        </div>
        {aiInsight && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#18181B] text-white text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
            AI
          </div>
        )}
      </div>
      <div className="kpi-card-value">{value}</div>
      {sub && <div className="kpi-card-sub">{sub}</div>}

      {/* Floating glow effect on hover */}
      <div className="absolute inset-0 bg-gradient-to-b from-indigo-300/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none rounded-2xl"></div>
    </div>
  );
}

