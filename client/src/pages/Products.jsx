import { useState, useEffect, useMemo } from 'react';
import { intelligenceService } from '../services';
import { Boxes, TrendingUp, TrendingDown, X } from 'lucide-react';

const RISK_STYLES = {
  high: 'bg-[#18181B] text-white',
  medium: 'bg-[#FEF3C7] text-[#92400E]',
  low: 'bg-[#F8FAFC] text-[#64748B]',
};

// API fields are typed float|None but edge-case data (single-day series,
// sparse uploads) can carry non-finite values; harden the UI so it never
// renders "NaN" and always shows a clean dash instead.
const fmt = (v, digits = 0) =>
  v !== null && v !== undefined && Number.isFinite(Number(v)) ? Number(v).toLocaleString(undefined, { maximumFractionDigits: digits }) : '—';

const fmtMoney = (v) =>
  v !== null && v !== undefined && Number.isFinite(Number(v)) ? `$${Number(v).toLocaleString()}` : '—';

const CATEGORY_TINTS = {
  FOODS: 'bg-[#F1F5F9] text-[#334155] ring-[#F1F5F9]',
  HOUSEHOLD: 'bg-[#F4F4F5] text-[#18181B] ring-[#F4F4F5]',
  HOBBIES: 'bg-[#E2E8F0] text-[#1E293B] ring-[#E2E8F0]',
};

function CategoryBadge({ category }) {
  if (!category) return <span className="text-slate-400">—</span>;
  const tint = CATEGORY_TINTS[category] || 'bg-slate-100 text-slate-600 ring-slate-200';
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-[0.75rem] font-semibold uppercase ring-1 ${tint}`}>
      {category}
    </span>
  );
}

function ProductsDetail({ product, onClose }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="card w-full max-w-2xl max-h-[85vh] overflow-y-auto scroll-thin"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between px-6 py-4 border-b sticky top-0 bg-white" style={{ borderColor: 'var(--border)' }}>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{product.item_id}</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {product.category || 'No category'} · {fmt(product.stores)} stores · {fmt(product.days_covered)} days covered
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors" aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 px-6 py-5">
          <div>
            <div className="text-xl font-semibold text-slate-900">{fmt(product.total_sales)}</div>
            <div className="text-[11px] text-slate-500">Units sold</div>
          </div>
          <div>
            <div className="text-xl font-semibold text-slate-900">{fmtMoney(product.revenue)}</div>
            <div className="text-[11px] text-slate-500">Revenue</div>
          </div>
          <div>
            <div className="text-xl font-semibold text-slate-900">{fmt(product.avg_daily_sales, 1)}</div>
            <div className="text-[11px] text-slate-500">Avg daily units</div>
          </div>
          <div>
            <div className="text-xl font-semibold text-slate-900">
              {product.growth_pct !== null && product.growth_pct !== undefined && Number.isFinite(Number(product.growth_pct)) ? (
                <span className={Number(product.growth_pct) >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                  {Number(product.growth_pct) >= 0 ? '+' : ''}{product.growth_pct}%
                </span>
              ) : '—'}
            </div>
            <div className="text-[11px] text-slate-500">Growth (28d)</div>
          </div>
        </div>

        <div className="px-6 pb-6">
          <div className="rounded-xl border divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Stockout risk</span>
              <span className={`inline-flex px-2 py-0.5 rounded-full text-[0.75rem] font-semibold uppercase ${RISK_STYLES[product.stockout_risk] || 'bg-slate-100 text-slate-600'}`}>
                {product.stockout_risk || '—'}
              </span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Top store</span>
              <span className="font-semibold text-slate-900">{product.top_store || '—'} {product.top_store_pct != null && Number.isFinite(Number(product.top_store_pct)) ? `(${product.top_store_pct}%)` : ''}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Demand trend</span>
              <span className="font-semibold text-slate-900">{product.trend_slope != null && Number.isFinite(Number(product.trend_slope)) ? `${product.trend_slope} /day` : '—'}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Demand stability (CV)</span>
              <span className="font-semibold text-slate-900">{fmt(product.demand_cv, 2)}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Peak month</span>
              <span className="font-semibold text-slate-900">{product.peak_month != null ? new Date(0, product.peak_month - 1).toLocaleString('en-US', { month: 'long' }) : '—'}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Day-of-week spread</span>
              <span className="font-semibold text-slate-900">{fmt(product.day_of_week_spread_pct, 1)}%</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-slate-500">Forecast accuracy (WAPE)</span>
              <span className="font-semibold text-slate-900">
                {product.forecast_accuracy?.wape != null && Number.isFinite(Number(product.forecast_accuracy.wape))
                  ? `${product.forecast_accuracy.wape.toFixed(1)}%`
                  : '—'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [category, setCategory] = useState('all');

  useEffect(() => {
    intelligenceService.products()
      .then((res) => setProducts(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load products'))
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(() => {
    const set = new Set(products.map((p) => p.category).filter(Boolean));
    return ['all', ...Array.from(set).sort()];
  }, [products]);

  const visible = useMemo(
    () => (category === 'all' ? products : products.filter((p) => p.category === category)),
    [products, category]
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Product Intelligence</h1>
          <p className="page-subtitle">Deep-dive analytics for every product.</p>
        </div>
        {!loading && !error && products.length > 0 && (
          <div className="text-right">
            <div className="text-2xl font-semibold text-slate-900">{products.length.toLocaleString()}</div>
            <div className="text-[11px] text-slate-500">Products tracked</div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><div className="animate-spin h-8 w-8 border-2 border-indigo-600 border-t-transparent rounded-full" /></div>
      ) : error ? (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">{error}</div>
      ) : products.length === 0 ? (
        <div className="text-center py-16 text-slate-500">No product data yet. Upload data first.</div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {categories.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-sm transition-colors ${
                  category === c
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {c === 'all' ? `All (${products.length})` : c}
                {c !== 'all' && ` (${products.filter((p) => p.category === c).length})`}
              </button>
            ))}
          </div>

          <div className="content-section">
            <div className="content-section-title">
              <Boxes className="w-4 h-4" />
              Product List
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Category</th>
                    <th className="text-right">Units</th>
                    <th className="text-right">Revenue</th>
                    <th className="text-right">Growth</th>
                    <th className="text-right">Stores</th>
                    <th className="text-right">Stockout risk</th>
                    <th className="text-right">Top store</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((p) => (
                    <tr key={p.item_id} onClick={() => setSelected(p)} className="cursor-pointer">
                      <td className="font-semibold text-slate-900">{p.item_id}</td>
                      <td><CategoryBadge category={p.category} /></td>
                      <td className="num">{fmt(p.total_sales)}</td>
                      <td className="num">{fmtMoney(p.revenue)}</td>
                      <td className="num">
                        {p.growth_pct !== null && p.growth_pct !== undefined && Number.isFinite(Number(p.growth_pct)) ? (
                          <span className={`inline-flex items-center gap-1 font-semibold ${Number(p.growth_pct) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {Number(p.growth_pct) >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                            {Number(p.growth_pct) >= 0 ? '+' : ''}{p.growth_pct}%
                          </span>
                        ) : '—'}
                      </td>
                      <td className="num">{fmt(p.stores)}</td>
                      <td className="text-right">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[0.75rem] font-semibold uppercase ${RISK_STYLES[p.stockout_risk] || 'bg-slate-100 text-slate-600'}`}>
                          {p.stockout_risk || '—'}
                        </span>
                      </td>
                      <td className="text-right text-slate-600">{p.top_store || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {selected && <ProductsDetail product={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

