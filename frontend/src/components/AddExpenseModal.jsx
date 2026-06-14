import { useState } from 'react';
import { apiClient } from '../api/client';

export default function AddExpenseModal({ groupId, members, onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [paidBy, setPaidBy] = useState('');
  const [splitType, setSplitType] = useState('equal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Basic split details builder based on split type
      const participantIds = members.map(m => m.user_id);
      
      const payload = {
        title,
        amount: parseFloat(amount),
        currency: 'INR',
        paid_by: paidBy,
        split_type: splitType,
        expense_date: new Date().toISOString().split('T')[0],
        participants: participantIds.map(id => ({ user_id: id }))
      };

      await apiClient.post(`/groups/${groupId}/expenses`, payload);
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create expense');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="text-lg font-semibold">Add an expense</h2>
          <button className="close-btn" onClick={onClose} type="button">×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body flex-col gap-4">
            {error && <div className="badge badge-danger mb-2 block p-2">{error}</div>}

            <div className="flex gap-4">
              <div className="flex-col gap-2" style={{ flex: 1 }}>
                <label className="text-sm font-medium">Description</label>
                <input 
                  type="text" 
                  required 
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="e.g. Dinner at Marina Bites"
                />
              </div>
              <div className="flex-col gap-2" style={{ width: '120px' }}>
                <label className="text-sm font-medium">Amount</label>
                <input 
                  type="number" 
                  step="0.01"
                  required 
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="₹0.00"
                />
              </div>
            </div>

            <div className="flex-col gap-2">
              <label className="text-sm font-medium">Paid by</label>
              <select 
                required 
                value={paidBy}
                onChange={e => setPaidBy(e.target.value)}
              >
                <option value="" disabled>Select person</option>
                {members.filter(m => !m.left_at).map(m => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex-col gap-2">
              <label className="text-sm font-medium">Split how?</label>
              <select 
                value={splitType}
                onChange={e => setSplitType(e.target.value)}
              >
                <option value="equal">Equally between everyone</option>
                <option value="unequal">Exact amounts</option>
                <option value="percentage">By percentages</option>
                <option value="share">By shares</option>
              </select>
            </div>
            
            <p className="text-xs text-muted">
              Note: For advanced split types (unequal, percentage, share), the detailed amounts will be requested in the next step.
            </p>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save Expense'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
