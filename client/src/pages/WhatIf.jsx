import { useState } from 'react';
import { purchaseService } from '../services';
import { ArrowLeftRight, Play } from 'lucide-react';
import { ErrorState } from '../components/common/LoadingState';

const FIELDS = [
  { key: 'demand_growth', label: 'Demand growth (%)', type: 'number', step: 0.01, default: 0, hint: 'e.g. 0.10 = +10% demand' },
  { key: 'lead_time_days', label: 'Supplier lead time (days)', type: 'number', step: 1, default: 7 },
  { key: 'service_level', label: 'Service level', type: 'number', step: 0.01, default: 0.95, min: 0.5, max: 0.999 },
  { key: 'holding_cost_rate', label: 'Holding cost rate', type: 'number', step: 0.01, default: 0.25 },
  { key: 'order_cost', label: 'Order cost ($)', type: 'number', step: 1, default: 100 },
  { key: 'unit_cost', label: 'Unit cost ($)', type: 'number', step: 1, default: 10 },
];

const DELTA_STYLES = {
  good: 'text-emerald-600',
  bad: 'text-red-600',
  neutral: 'text-slate-500',
};

export default function WhatIf() {
  const [params, setParams] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await purchaseService.whatIf({ ...params, sample_size: 2000 });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const deltaClass = (key, val) => {
    if (val === null || val === undefined) return DELTA_STYLES.neutral;
    if (key.includes('items_to_reorder') || key.includes('stockout') || key.includes('carrying') || key.includes('overstock')) {
      return val < 0 ? DELTA_STYLES.good : val > 0 ? DELTA_STYLES.bad : DELTA_STYLES.neutral;
    }
    return val > 0 ? DELTA_STYLES.good : val < 0 ? DELTA_STYLES.bad : DELTA_STYLES.neutral;
  };

  const fmt = (v) => {
    if (v === null || v === undefined) return '—';
    return typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 1 }) : v;
  };

  return (
    <div className="space-y-8 animate-fade-in floating-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Inventory What-If Simulator</h1>
          <p className="page-subtitle">Change the knobs and see how safety stock, orders, risk, and value respond</p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 section-gap">
        {/* Controls */}
        <div className="content-section">
          <div className="flex items-center gap-2 content-section-title">
            <ArrowLeftRight className="w-4 h-4 text-neutral-900" />
            Scenario
          </div>
          <div className="space-y-4">
            {FIELDS.map((f) => (
              <div key={f.key}>
                <label className="field-label">{f.label}</label>
                <input
                  type="number"
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  value={params[f.key] ?? f.default}
                  onChange={(e) => setParams({ ...params, [f.key]: e.target.value === '' ? undefined : parseFloat(e.target.value) })}
                  className="input"
                />
                {f.hint && <p className="text-[11px] text-slate-500 mt-1">{f.hint}</p>}
              </div>
            ))}
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="btn-gradient w-full mt-5"
          >
            <Play size={15} /> {loading ? 'Simulating…' : 'Run simulation'}
          </button>
        </div>

        {/* Results */}
        <div className="md:col-span-2">
          {error && <ErrorState message={error} />}
          {!result ? (
            <div className="content-section h-full flex items-center justify-center text-center text-sm text-slate-500 bg-white/60 border-dashed">
              <div>
                <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
                  <ArrowLeftRight className="w-6 h-6 text-slate-400" />
                </div>
                Set a scenario and run the simulation to see the impact on your inventory.
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <div className="content-section-title">Impact on Inventory</div>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.keys(result.deltas).map((key) => (
                    <div key={key} className="card p-4">
                      <div className={`kpi-card-value ${deltaClass(key, result.deltas[key])}`}>
                        {result.deltas[key] !== null ? `${result.deltas[key] > 0 ? '+' : ''}${fmt(result.deltas[key])}` : '—'}
                      </div>
                      <div className="kpi-card-label mt-1 break-words">{key.replace(/_/g, ' ')}</div>
                      <div className="text-[11px] text-slate-500 mt-1">
                        baseline {fmt(result.baseline_financials[key])} → scenario {fmt(result.scenario_financials[key])}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {result.top_changes.length > 0 && (
                <div className="content-section">
                  <div className="content-section-title">Biggest order changes</div>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th>Store</th>
                          <th className="text-right">Order (base)</th>
                          <th className="text-right">Order (scenario)</th>
                          <th className="text-right">Δ</th>
                          <th className="text-right">Safety stock Δ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.top_changes.map((c, i) => (
                          <tr key={i}>
                            <td className="font-medium">{c.item_id}</td>
                            <td>{c.store_id}</td>
                            <td className="num">{fmt(c.order_qty_baseline)}</td>
                            <td className="num">{fmt(c.order_qty_scenario)}</td>
                            <td className={`num font-semibold ${c.delta_qty >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {c.delta_qty > 0 ? '+' : ''}{fmt(c.delta_qty)}
                            </td>
                            <td className="num">{fmt(c.safety_stock_scenario - c.safety_stock_baseline)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}