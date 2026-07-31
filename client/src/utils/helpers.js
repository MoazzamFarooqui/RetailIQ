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
    OK: 'text-green-600 bg-green-50 border-green-200',
    LOW: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    CRITICAL: 'text-red-600 bg-red-50 border-red-200',
    EXCESS: 'text-blue-600 bg-blue-50 border-blue-200',
  };
  return colors[status] || 'text-gray-600 bg-gray-50 border-gray-200';
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
