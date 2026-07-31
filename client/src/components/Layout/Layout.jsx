import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect, useState } from 'react';
import { weatherService } from '../../services/index';

export default function Layout() {
  const [context, setContext] = useState(null);

  useEffect(() => {
    weatherService.holidaysCurrent().then(r => setContext(r.data)).catch(() => {});
  }, []);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Context banner */}
        {context && (
          <div className="mb-6 flex flex-wrap gap-3 text-sm">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg border border-gray-100 shadow-sm">
              {context.season_emoji} {context.season}
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg border border-gray-100 shadow-sm">
              🌡️ {context.temperature_c}°C
            </span>
            {context.holiday_today && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-yellow-50 text-yellow-700 rounded-lg border border-yellow-200 shadow-sm">
                🎉 {context.holiday_today}
              </span>
            )}
            {context.pre_holiday_window && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 text-orange-700 rounded-lg border border-orange-200 shadow-sm">
                📢 {context.pre_holiday_window.holiday_name} in {context.pre_holiday_window.days_until_holiday}d
              </span>
            )}
            {context.demand_multiplier > 1 && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-50 text-purple-700 rounded-lg border border-purple-200 shadow-sm">
                📊 {context.demand_multiplier}x demand multiplier
              </span>
            )}
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
