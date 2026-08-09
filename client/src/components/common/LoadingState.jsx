import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';

export function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
      <Loader2 className="w-8 h-8 animate-spin text-brand-600 mb-3" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

export function ErrorState({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="card p-8 flex flex-col items-center justify-center text-center">
      <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-3">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      <p className="text-sm font-medium text-red-400 mb-1">Something went wrong</p>
      <p className="text-sm text-slate-500 mb-5">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-primary">Try Again</button>
      )}
    </div>
  );
}

export function EmptyState({ message = 'No data available', icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-slate-400">
      <div className="w-12 h-12 rounded-full bg-slate-800/60 flex items-center justify-center mb-3">
        <Icon className="w-6 h-6 text-slate-400" />
      </div>
      <p className="text-sm">{message}</p>
    </div>
  );
}

