export default function KpiCard({ label, value, sub, icon: Icon, color = 'blue', loading }) {
  const colors = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-emerald-600',
    orange: 'from-orange-500 to-amber-600',
    purple: 'from-purple-500 to-violet-600',
    red: 'from-red-500 to-rose-600',
  };

  if (loading) {
    return (
      <div className="kpi-card animate-pulse">
        <div className="h-3 bg-gray-200 rounded w-1/2 mb-2" />
        <div className="h-8 bg-gray-200 rounded w-3/4 mb-1" />
        {sub && <div className="h-3 bg-gray-100 rounded w-1/3" />}
      </div>
    );
  }

  return (
    <div className="kpi-card relative overflow-hidden group">
      {Icon && (
        <div className={`absolute -right-3 -top-3 w-16 h-16 bg-gradient-to-br ${colors[color] || colors.blue} rounded-full opacity-10 group-hover:opacity-20 transition-opacity`} />
      )}
      <div className="relative">
        <div className="flex items-center gap-2 mb-1">
          {Icon && <Icon className="w-4 h-4 text-gray-400" />}
          <span className="kpi-card-label">{label}</span>
        </div>
        <div className="kpi-card-value">{value}</div>
        {sub && <div className="kpi-card-sub">{sub}</div>}
      </div>
    </div>
  );
}
