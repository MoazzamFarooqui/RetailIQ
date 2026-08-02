export default function KpiCard({ label, value, sub, icon: Icon, color = 'blue', loading }) {
  const tile = {
    blue: 'from-brand-500 to-emerald-600',
    green: 'from-emerald-500 to-teal-600',
    orange: 'from-orange-500 to-amber-600',
    purple: 'from-violet-500 to-purple-600',
    red: 'from-red-500 to-rose-600',
  };

  if (loading) {
    return (
      <div className="kpi-card animate-pulse">
        <div className="h-3 bg-slate-200 rounded w-1/2 mb-2" />
        <div className="h-8 bg-slate-200 rounded w-3/4 mb-1" />
        {sub && <div className="h-3 bg-slate-100 rounded w-1/3" />}
      </div>
    );
  }

  return (
    <div className="kpi-card group">
      <div className="flex items-center gap-3 mb-3">
        {Icon && (
          <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${tile[color] || tile.blue} flex items-center justify-center shadow-sm flex-shrink-0`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        )}
        <span className="kpi-card-label">{label}</span>
      </div>
      <div className="kpi-card-value">{value}</div>
      {sub && <div className="kpi-card-sub">{sub}</div>}
    </div>
  );
}
