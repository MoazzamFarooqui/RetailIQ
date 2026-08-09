import { useState, useEffect } from 'react';
import { uploadService } from '../services/index';
import { LoadingSpinner, ErrorState } from '../components/common/LoadingState';
import { UploadCloud, CheckCircle2, AlertTriangle, FileText, Table2, HardDrive, Wand2, XCircle, Loader2 as LoaderIcon } from 'lucide-react';

function StatusPill({ status }) {
  const styles = {
    cleaned: 'badge-ok',
    error: 'badge-critical',
    processing: 'badge-low',
    uploaded: 'badge-excess',
  };
  const icons = {
    cleaned: CheckCircle2,
    error: XCircle,
    processing: LoaderIcon,
    uploaded: UploadCloud,
  };
  const Icon = icons[status] || FileText;
  return (
    <span className={styles[status] || 'badge-neutral'}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
}

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
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Upload Data</h1>
          <p className="page-subtitle">Upload retail sales CSV files — auto-validate, clean, and append to your dataset</p>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="content-section">
        <div className="content-section-title">Upload CSV</div>
        <div className="border-2 border-dashed border-slate-700 rounded-xl p-10 text-center hover:border-brand-400 hover:bg-brand-500/10 transition-all group">
          <div className="w-14 h-14 rounded-2xl bg-slate-900/10 text-slate-900 flex items-center justify-center mx-auto mb-4 group-hover:scale-105 transition-transform">
            <UploadCloud className="w-7 h-7" />
          </div>
          <p className="text-sm font-bold text-slate-900 mb-5">Drop your CSV file here or click to browse</p>
          <p className="text-xs font-bold text-slate-900 mb-5">Expected columns: <code className="bg-transparent text-sm font-normal text-slate-900">date, sales, item_id, store_id</code></p>
          <div className="flex justify-center">
            <label className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-slate-900 text-white text-sm font-medium cursor-pointer hover:bg-slate-700 transition-colors">
              <UploadCloud className="w-4 h-4" />
              Choose file
              <input
                type="file"
                accept=".csv"
                onChange={e => setFile(e.target.files[0])}
                className="sr-only"
              />
            </label>
          </div>
          {file && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm text-slate-300 animate-fade-in">
              <FileText className="w-4 h-4 text-brand-500" />
              <span className="font-medium">{file.name}</span>
              <span className="text-slate-500">· {(file.size / 1024).toFixed(1)} KB</span>
            </div>
          )}
          {file && (
            <button onClick={handleUpload} disabled={uploading} className="btn-primary mt-5">
              {uploading ? (
                <>
                  <LoaderIcon className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  Upload & Validate
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {/* Upload Result */}
      {result && (
        <div className={`content-section animate-fade-in ${result.errors?.length > 0 ? '!border-red-500/40' : '!border-emerald-500/40'}`}>
          <div className="flex items-center gap-2.5 mb-4">
            {result.errors?.length > 0
              ? <AlertTriangle className="w-5 h-5 text-red-500" />
              : <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
            <span className={`font-bold ${result.errors?.length > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {result.errors?.length > 0 ? 'Validation Failed' : 'Upload Successful'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-5">
            <div className="text-center p-4 bg-surface-925 rounded-xl border border-slate-800">
              <Table2 className="w-5 h-5 text-brand-500 mx-auto mb-1.5" />
              <div className="text-2xl font-bold text-white tabular-nums">{result.row_count.toLocaleString()}</div>
              <div className="text-xs text-slate-400 mt-0.5">Rows</div>
            </div>
            <div className="text-center p-4 bg-surface-925 rounded-xl border border-slate-800">
              <FileText className="w-5 h-5 text-emerald-500 mx-auto mb-1.5" />
              <div className="text-2xl font-bold text-white tabular-nums">{result.column_count}</div>
              <div className="text-xs text-slate-400 mt-0.5">Columns</div>
            </div>
            <div className="text-center p-4 bg-surface-925 rounded-xl border border-slate-800">
              <HardDrive className="w-5 h-5 text-violet-500 mx-auto mb-1.5" />
              <div className="text-2xl font-bold text-white tabular-nums">{result.file_size_kb.toFixed(0)} KB</div>
              <div className="text-xs text-slate-400 mt-0.5">File Size</div>
            </div>
          </div>

          {result.warnings?.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-amber-400 bg-amber-500/10 p-3 rounded-lg mb-2 animate-fade-in">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{w}</span>
            </div>
          ))}
          {result.errors?.map((e, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-2 animate-fade-in">
              <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{e}</span>
            </div>
          ))}

          {result.errors?.length === 0 && (
            <button onClick={() => handleClean(result.id)} disabled={cleaning} className="btn-success mt-3">
              {cleaning ? (
                <>
                  <LoaderIcon className="w-4 h-4 animate-spin" />
                  Cleaning...
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  Auto-Clean & Process
                </>
              )}
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
          <div className="table-wrap">
            <table className="data-table bordered">
              <thead>
                <tr>
                  <th className="pl-1 text-sm font-semibold text-[#374151]">File</th>
                  <th className="text-sm font-semibold text-[#374151]">Rows</th>
                  <th className="text-sm font-semibold text-[#374151]">Size</th>
                  <th className="text-sm font-semibold text-[#374151]">Status</th>
                  <th className="text-sm font-semibold text-[#374151]">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => (
                  <tr key={i}>
                    <td className="font-medium text-white">
                      <span className="inline-flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-500" />
                        {h.original_filename}
                      </span>
                    </td>
                    <td>{h.row_count?.toLocaleString() || '—'}</td>
                    <td>{h.file_size_kb?.toFixed(0) || '—'} KB</td>
                    <td><StatusPill status={h.status} /></td>
                    <td className="text-slate-500">{new Date(h.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No uploads yet.</p>
        )}
      </div>
    </div>
  );
}

