import { useState, useRef, useEffect } from 'react';
import { advisorService } from '../services';
import { Send, Bot, Sparkles, AlertCircle } from 'lucide-react';

const SUGGESTIONS = [
  'Why did sales decline?',
  'Which products should I reorder?',
  'Which stores are underperforming?',
  'What products are likely to see increased demand?',
  'What should I do next?',
];

export default function Advisor() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const ask = async (question) => {
    if (!question.trim() || loading) return;
    setError(null);
    setMessages((m) => [...m, { role: 'user', content: question }]);
    setInput('');
    setLoading(true);
    try {
      const history = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }));
      const res = await advisorService.ask(question, history);
      setMessages((m) => [...m, {
        role: 'assistant',
        content: res.data.answer,
        mode: res.data.mode,
      }]);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to get an answer. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 animate-fade-in">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-[#F3F4F6] text-[#18181B] flex items-center justify-center">
            <Bot size={22} />
          </div>
          <div>
            <h1 className="page-title">AI Business Advisor</h1>
            <p className="page-subtitle">Answers grounded in your real sales, inventory, and forecast data.</p>
          </div>
        </div>
      </div>

      {messages.length === 0 && !loading && (
        <div>
          <p className="text-sm text-slate-600 mb-3">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-sm bg-white border-[#E5E7EB] text-[#374151] hover:bg-[#18181B] hover:text-white transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              m.role === 'user'
                ? 'bg-slate-900 text-white'
                : 'card border border-slate-200 text-slate-800'
            }`}>
              {m.mode === 'rules' && m.role === 'assistant' && (
                <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide font-semibold text-amber-600 mb-1">
                  <Sparkles size={10} /> Rule-based
                </span>
              )}
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="card border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-500 flex items-center gap-2">
              <div className="animate-spin h-4 w-4 border-2 border-indigo-600 border-t-transparent rounded-full" />
              Analyzing your data…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      <form
        onSubmit={(e) => { e.preventDefault(); ask(input); }}
        className="flex gap-2 rounded-2xl border p-2 sm:p-3 bg-white shadow-sm sticky bottom-4"
        style={{ borderColor: 'var(--border)' }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about sales, inventory, forecasts, stores…"
          className="flex-1 bg-transparent px-3 py-2 text-sm outline-none text-slate-900 placeholder:text-slate-400"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl px-5 flex items-center gap-2 bg-[#18181B] text-white hover:bg-slate-700 disabled:opacity-50 transition-colors"
        >
          <Send size={16} /> Ask
        </button>
      </form>
    </div>
  );
}

