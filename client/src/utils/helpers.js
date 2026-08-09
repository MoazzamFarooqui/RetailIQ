export function formatNumber(num) {
  if (!num && num !== 0) return '—';
  if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(2)}B`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

export function formatCurrency(num) {
  if (!num && num !== 0) return '—';
  return `$${formatNumber(num)}`;
}

export function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function getStatusColor(status) {
  const colors = {
    OK: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    LOW: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30',
    EXCESS: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
  };
  return colors[status] || 'text-slate-300 bg-slate-800/60 border-slate-700';
}

export function getStatusBadgeClass(status) {
  const classes = {
    OK: 'badge-ok',
    LOW: 'badge-low',
    CRITICAL: 'badge-critical',
    EXCESS: 'badge-excess',
  };
  return classes[status] || 'badge-neutral';
}

export function getSeasonEmoji(season) {
  const emojis = { Spring: '🌸', Summer: '☀️', Monsoon: '🌧️', Autumn: '🍂', Winter: '❄️' };
  return emojis[season] || '🌤️';
}

export const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export function downloadCSV(data, filename) {
  const blob = new Blob([data], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

