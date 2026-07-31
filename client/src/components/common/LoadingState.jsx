export function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

export function ErrorState({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
      <div className="text-4xl mb-3">⚠️</div>
      <p className="text-sm text-red-500 mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Try Again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message = 'No data available', icon = '📭' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
      <div className="text-4xl mb-3">{icon}</div>
      <p className="text-sm">{message}</p>
    </div>
  );
}
