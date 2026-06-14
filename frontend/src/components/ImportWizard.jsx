import { useState } from 'react';
import { apiClient } from '../api/client';

export default function ImportWizard({ groupId, onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const data = await apiClient.postForm(`/groups/${groupId}/import/upload`, formData);
      setSession(data);
    } catch (err) {
      setError(err.message || 'Failed to upload CSV');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await apiClient.post(`/import/${session.id}/confirm`, {});
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to confirm import');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="text-lg font-semibold">Import Expenses from CSV</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {error && <div className="badge badge-danger mb-4 block p-2">{error}</div>}

          {!session ? (
            <form onSubmit={handleUpload} className="flex-col gap-4">
              <p className="text-sm text-muted mb-2">
                Upload your expenses_export.csv file. The system will analyze it and ask you to review any anomalies before saving.
              </p>
              <input 
                type="file" 
                accept=".csv" 
                onChange={(e) => setFile(e.target.files[0])} 
                required
                className="w-full"
              />
              <button 
                type="submit" 
                className="btn btn-primary mt-4" 
                disabled={!file || loading}
              >
                {loading ? 'Uploading...' : 'Upload & Analyze'}
              </button>
            </form>
          ) : (
            <div className="flex-col gap-4">
              <div className="card bg-gray-50 border-gray-200">
                <h3 className="font-semibold text-sm mb-2">Import Summary</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>Total Rows: <span className="font-medium">{session.total_rows}</span></div>
                  <div>Anomalies: <span className="text-danger font-medium">{session.detected_anomalies}</span></div>
                  <div>To Review: <span className="font-medium">{session.pending_reviews}</span></div>
                </div>
              </div>

              {session.pending_reviews > 0 ? (
                <div className="p-4 bg-yellow-50 text-yellow-800 rounded-md text-sm border border-yellow-200">
                  <p className="font-medium mb-1">⚠️ Review Required</p>
                  <p>There are {session.pending_reviews} issues that need your attention before you can confirm the import.</p>
                  <button className="btn btn-outline text-xs mt-3 bg-white">
                    Review Anomalies
                  </button>
                </div>
              ) : (
                <div className="p-4 bg-green-50 text-green-800 rounded-md text-sm border border-green-200">
                  <p className="font-medium">✅ Ready to import!</p>
                  <p>All rows have been analyzed and are ready to be saved to the database.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {session && (
          <div className="modal-footer">
            <button className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button 
              className="btn btn-primary" 
              onClick={handleConfirm} 
              disabled={loading || session.pending_reviews > 0}
            >
              {loading ? 'Importing...' : 'Confirm Import'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
