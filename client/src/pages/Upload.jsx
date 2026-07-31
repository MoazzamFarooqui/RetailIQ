import { useState, useEffect } from 'react';
import { uploadService } from '../services/index';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { Upload as UploadIcon, CheckCircle, AlertCircle, FileText } from 'lucide-react';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [cleaning, setCleaning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    uploadService.history()
      .then(r => setHistory(r.data))
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadService.upload(file);
      setResult(res.data);
      // Refresh history
      const h = await uploadService.history();
      setHistory(h.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleClean = async (datasetId) => {
    setCleaning(true);
    try {
      await uploadService.clean(datasetId);
      const h = await uploadService.history();
      setHistory(h.data);
    } catch (e) {
      setError('Clean failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setCleaning(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1>📤 Upload Data</h1>
      <p className="text-gray-500 text-sm -mt-4">Upload retail sales CSV files. Auto-validate, clean, and append to your dataset.</p>

      {/* Upload Zone */}
      <div className="content-section">
        <div className="content-section-title">Upload CSV</div>
        <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-blue-300 transition-colors">
          <UploadIcon className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 mb-1">Drop your CSV file here or click to browse</p>
          <p className="text-xs text-gray-400 mb-4">Expected columns: date, sales, item_id, store_id</p>
          <input type="file" accept=".csv" onChange={e => setFile(e.target.files[0])} className="block mx-auto text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          {file && <p className="mt-2 text-sm text-gray-600">Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)</p>}
          {file && (
            <button onClick={handleUpload} disabled={uploading}
              className="mt-4 px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm">
              {uploading ? 'Uploading...' : 'Upload & Validate'}
            </button>
          )}
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {/* Upload Result */}
      {result && (
        <div className={`content-section ${result.errors?.length > 0 ? 'border-red-200' : 'border-green-200'}`}>
          <div className="flex items-center gap-2 mb-3">
            {result.errors?.length > 0
              ? <AlertCircle className="w-5 h-5 text-red-500" />
              : <CheckCircle className="w-5 h-5 text-green-500" />}
            <span className={`font-semibold ${result.errors?.length > 0 ? 'text-red-700' : 'text-green-700'}`}>
              {result.errors?.length > 0 ? 'Validation Failed' : 'Upload Successful'}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-800">{result.row_count.toLocaleString()}</div>
              <div className="text-xs text-gray-500">Rows</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-800">{result.column_count}</div>
              <div className="text-xs text-gray-500">Columns</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-800">{result.file_size_kb.toFixed(0)} KB</div>
              <div className="text-xs text-gray-500">File Size</div>
            </div>
          </div>
          {result.warnings?.map((w, i) => (
            <div key={i} className="text-sm text-yellow-600 bg-yellow-50 p-2 rounded mb-1">{w}</div>
          ))}
          {result.errors?.map((e, i) => (
            <div key={i} className="text-sm text-red-600 bg-red-50 p-2 rounded mb-1">{e}</div>
          ))}
          {result.errors?.length === 0 && (
            <button onClick={() => handleClean(result.id)} disabled={cleaning}
              className="mt-3 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm">
              {cleaning ? 'Cleaning...' : 'Auto-Clean & Process'}
            </button>
          )}
        </div>
      )}

      {/* Upload History */}
      <div className="content-section">
        <div className="content-section-title">Upload History</div>
        {loadingHistory ? (
          <LoadingSpinner message="Loading history..." />
        ) : history && history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 font-medium text-gray-500">File</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Rows</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Size</th>
                  <th className="text-center py-2 px-3 font-medium text-gray-500">Status</th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{h.original_filename}</td>
                    <td className="py-2 px-3 text-right">{h.row_count?.toLocaleString() || '—'}</td>
                    <td className="py-2 px-3 text-right">{h.file_size_kb?.toFixed(0) || '—'} KB</td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        h.status === 'cleaned' ? 'bg-green-50 text-green-700' :
                        h.status === 'error' ? 'bg-red-50 text-red-700' :
                        'bg-yellow-50 text-yellow-700'
                      }`}>{h.status}</span>
                    </td>
                    <td className="py-2 px-3 text-right text-gray-400">{new Date(h.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-sm">No uploads yet.</p>
        )}
      </div>
    </div>
  );
}
