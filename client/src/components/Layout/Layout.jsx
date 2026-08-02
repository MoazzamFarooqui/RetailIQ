import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect, useState } from 'react';
import { weatherService } from '../../services/index';
import { CalendarDays, Thermometer, PartyPopper, Megaphone, TrendingUp } from 'lucide-react';

function ContextChip({ icon: Icon, tone, children }) {
  const tones = {
    default: 'bg-white border-slate-200 text-slate-600',
    holiday: 'bg-amber-50 border-amber-200 text-amber-800',
    pre: 'bg-orange-50 border-orange-200 text-orange-800',
    demand: 'bg-violet-50 border-violet-200 text-violet-800',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium shadow-sm ${tones[tone] || tones.default}`}>
      {Icon && <Icon className="w-4 h-4" />}
      {children}
    </span>
  );
}

const PAGE_TITLES = {
  '/': { title: 'Dashboard', desc: 'Platform overview and key business metrics' },
  '/analytics': { title: 'Analytics', desc: 'Sales & revenue performance' },
  '/forecast': { title: 'Forecast', desc: 'AI demand predictions' },
  '/inventory': { title: 'Inventory', desc: 'Stock optimization' },
  '/model-insights': { title: 'Model Insights', desc: 'Explainability & performance' },
  '/ai-insights': { title: 'AI Insights', desc: 'Automated business intelligence' },
  '/upload': { title: 'Upload Data', desc: 'Import & validate datasets' },
};

export default function Layout() {
  const [context, setContext] = useState(null);
  const location = useLocation();
  const page = PAGE_TITLES[location.pathname] || PAGE_TITLES['/'];

  useEffect(() => {
    weatherService.holidaysCurrent().then(r => setContext(r.data)).catch(() => {});
  }, []);

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-200">
          <div className="px-6 lg:px-8 py-3.5 flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Retail Intelligence</div>
              <div className="text-sm font-semibold text-slate-800 truncate">{page.title}</div>
            </div>

            {/* Context chips */}
            {context && (
              <div className="hidden md:flex flex-wrap justify-end gap-2 text-sm">
                {context.season && (
                  <ContextChip icon={CalendarDays}>{context.season_emoji} {context.season}</ContextChip>
                )}
                {context.temperature_c && (
                  <ContextChip icon={Thermometer}>{context.temperature_c}°C</ContextChip>
                )}
                {context.holiday_today && (
                  <ContextChip tone="holiday" icon={PartyPopper}>{context.holiday_today}</ContextChip>
                )}
                {context.pre_holiday_window && (
                  <ContextChip tone="pre" icon={Megaphone}>
                    {context.pre_holiday_window.holiday_name} in {context.pre_holiday_window.days_until_holiday}d
                  </ContextChip>
                )}
                {context.demand_multiplier > 1 && (
                  <ContextChip tone="demand" icon={TrendingUp}>
                    {context.demand_multiplier}x demand
                  </ContextChip>
                )}
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 px-6 lg:px-8 py-6 max-w-7xl mx-auto w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
