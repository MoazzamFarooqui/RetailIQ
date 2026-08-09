import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect, useState } from 'react';
import { weatherService } from '../../services/index';
import { CalendarDays, Thermometer, PartyPopper, Megaphone, TrendingUp } from 'lucide-react';

function ContextChip({ icon: Icon, tone, children }) {
  const tones = {
    default: 'bg-white border border-gray-200 text-[#18181B]',
    holiday: 'bg-amber-50 border border-amber-200 text-amber-800',
    pre: 'bg-white border border-gray-200 text-[#18181B]',
    demand: 'bg-[#18181B] text-white',
    ai: 'bg-indigo-50 border border-indigo-200 text-indigo-700',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium shadow-sm ${tones[tone] || tones.default}`}>
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
  '/stores': { title: 'Stores', desc: 'Store intelligence & performance' },
  '/products': { title: 'Products', desc: 'Product intelligence' },
  '/advisor': { title: 'Advisor', desc: 'AI business advisor' },
  '/what-if': { title: 'What-If Analysis', desc: 'Inventory simulation' },
  '/alerts': { title: 'Alerts', desc: 'Smart alerts' },
  '/data-health': { title: 'Data Health', desc: 'Data quality monitoring' },
  '/reports': { title: 'Reports', desc: 'Generated reports' }
};

export default function Layout() {
  const [context, setContext] = useState(null);
  const location = useLocation();
  const page = PAGE_TITLES[location.pathname] || PAGE_TITLES['/'];

  useEffect(() => {
    weatherService.holidaysCurrent().then(r => setContext(r.data)).catch(() => {})
  }, []);

  return (
    <div className="flex min-h-screen bg-[#f4f4f1]">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-20 border-b border-stone-100 bg-[#f4f4f1]/90 backdrop-blur-md">
          <div className="px-6 lg:px-10 py-4 flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-[.16em] text-stone-400">Retail Intelligence</div>
              <div className="text-sm font-semibold text-stone-800 truncate" aria-label={page.title}>{page.title}</div>
            </div>

            {/* Context chips with indigo accent for AI features */}
            {context && (
              <div className="hidden md:flex flex-wrap justify-end gap-2 text-sm">
                {context.season && (
                  <ContextChip icon={CalendarDays} tone="default">
                    {context.season_emoji} {context.season}
                  </ContextChip>
                )}
                {context.temperature_c && (
                  <ContextChip icon={Thermometer} tone="default">
                    {context.temperature_c}°C
                  </ContextChip>
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
                {context.ai_insight && (
                  <ContextChip tone="ai" icon={TrendingUp}>
                    AI Insight Available
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
