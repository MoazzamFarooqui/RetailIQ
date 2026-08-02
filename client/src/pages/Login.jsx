import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { TrendingUp, Sparkles, Package, AlertCircle, Loader2, ShieldCheck } from 'lucide-react';

const FEATURE_POINTS = [
  { icon: TrendingUp, title: 'AI Demand Forecasting', desc: 'Predict sales 7–90 days ahead with live context.' },
  { icon: Package, title: 'Inventory Optimization', desc: 'Safety stock, reorder points and stockout alerts.' },
  { icon: Sparkles, title: 'Explainable Insights', desc: 'Understand every prediction with SHAP analysis.' },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Left brand panel */}
      <div className="hidden lg:flex w-[46%] relative overflow-hidden bg-gradient-to-br from-slate-900 via-brand-900 to-emerald-950 text-white flex-col justify-between p-12">
        {/* Decorative grid */}
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{ backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)', backgroundSize: '48px 48px' }}
        />
        <div className="absolute -bottom-32 -right-32 w-[420px] h-[420px] rounded-full bg-brand-500/20 blur-3xl" />
        <div className="absolute -top-24 -left-16 w-[300px] h-[300px] rounded-full bg-emerald-500/20 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-400 to-emerald-500 flex items-center justify-center shadow-lg">
            <svg width="20" height="20" viewBox="0 0 64 64" fill="none">
              <path d="M16 44 V20 M32 44 V12 M48 44 V28" stroke="#fff" strokeWidth="9" strokeLinecap="round" />
              <circle cx="32" cy="44" r="6" fill="#fff" />
            </svg>
          </div>
          <div>
            <div className="font-bold text-xl tracking-tight">RetailIQ</div>
            <div className="text-[10px] font-medium uppercase tracking-widest text-brand-200">Intelligence Suite</div>
          </div>
        </div>

        <div className="relative">
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            Make smarter retail
            <br />
            decisions with AI.
          </h1>
          <p className="mt-4 text-brand-100/90 text-base leading-relaxed max-w-md">
            A unified platform for demand forecasting, inventory optimization and
            explainable business intelligence.
          </p>

          <div className="mt-10 space-y-4">
            {FEATURE_POINTS.map((f, i) => (
              <div key={i} className="flex items-start gap-3.5">
                <div className="w-9 h-9 rounded-lg bg-white/10 ring-1 ring-white/15 flex items-center justify-center flex-shrink-0 backdrop-blur">
                  <f.icon className="w-5 h-5 text-brand-200" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{f.title}</div>
                  <div className="text-sm text-brand-100/70">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative flex items-center gap-2 text-xs text-brand-100/60">
          <ShieldCheck className="w-4 h-4" />
          Secure enterprise-grade platform
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md animate-fade-in">
          {/* Mobile brand */}
          <div className="lg:hidden text-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-emerald-600 flex items-center justify-center mx-auto mb-4 shadow-soft">
              <svg width="26" height="26" viewBox="0 0 64 64" fill="none">
                <path d="M16 44 V20 M32 44 V12 M48 44 V28" stroke="#fff" strokeWidth="9" strokeLinecap="round" />
                <circle cx="32" cy="44" r="6" fill="#fff" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">RetailIQ</h1>
            <p className="text-slate-500 text-sm mt-1">AI-Powered Retail Intelligence Platform</p>
          </div>

          <div className="card p-8">
            <div className="mb-7">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">Welcome back</h2>
              <p className="text-sm text-slate-500 mt-1">Sign in to your account to continue</p>
            </div>

            {error && (
              <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start gap-2.5 animate-fade-in">
                <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="field-label">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input"
                  placeholder="Enter your username"
                  autoComplete="username"
                  required
                />
              </div>
              <div>
                <label className="field-label">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="btn-gradient w-full py-2.5"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>
          </div>

          <p className="text-center text-xs text-slate-400 mt-6">
            © {new Date().getFullYear()} RetailIQ · Retail Intelligence Platform
          </p>
        </div>
      </div>
    </div>
  );
}
