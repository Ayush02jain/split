import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

export default function AddMemberModal({ groupId, onClose, onSuccess }) {
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const data = await apiClient.get('/auth/users');
        setUsers(data);
      } catch (err) {
        console.error("Failed to load users:", err);
      } finally {
        setFetching(false);
      }
    };
    fetchUsers();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedUserId) return;
    
    setLoading(true);
    setError(null);

    try {
      await apiClient.post(`/groups/${groupId}/members`, {
        user_id: selectedUserId,
        joined_at: new Date().toISOString().split('T')[0]
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to add member');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '400px' }}>
        <div className="modal-header">
          <h2 className="text-lg font-semibold">Add Member to Group</h2>
          <button className="close-btn" onClick={onClose} type="button">×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body flex-col gap-4">
            {error && <div className="badge badge-danger mb-2 block p-2">{error}</div>}

            <div className="flex-col gap-2">
              <label className="text-sm font-medium">Select a User</label>
              <select 
                required 
                value={selectedUserId}
                onChange={e => setSelectedUserId(e.target.value)}
                disabled={fetching}
              >
                <option value="" disabled>{fetching ? 'Loading users...' : 'Choose someone to add'}</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.display_name} ({u.email})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !selectedUserId}>
              {loading ? 'Adding...' : 'Add Member'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
