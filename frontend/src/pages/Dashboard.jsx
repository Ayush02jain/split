import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import CreateGroupModal from '../components/CreateGroupModal';

export default function Dashboard() {
  const { user } = useAuth();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchGroups = async () => {
    try {
      const data = await apiClient.get('/groups');
      setGroups(data);
    } catch (err) {
      console.error("Failed to load groups:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-xl">Welcome back, {user?.display_name}!</h1>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>+ New Group</button>
      </div>

      <h2 className="text-lg mb-4">Your Groups</h2>
      
      {loading ? (
        <div>Loading...</div>
      ) : groups.length === 0 ? (
        <div className="card text-center" style={{ padding: '40px' }}>
          <div className="text-muted mb-4">You aren't in any groups yet.</div>
          <button className="btn btn-outline" onClick={() => setShowCreateModal(true)}>Create your first group</button>
        </div>
      ) : (
        <div className="flex gap-6" style={{ flexWrap: 'wrap' }}>
          {groups.map(group => (
            <Link key={group.id} to={`/groups/${group.id}`} className="card" style={{ flex: '1 1 300px', display: 'block', transition: 'transform 0.2s, box-shadow 0.2s', ':hover': { transform: 'translateY(-2px)' } }}>
              <div className="flex items-center gap-4 mb-4">
                <div className="avatar" style={{ width: '48px', height: '48px', fontSize: '20px' }}>
                  {group.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="font-semibold text-lg" style={{ color: 'var(--text-main)' }}>{group.name}</div>
                  <div className="text-sm text-muted">{group.member_count} members</div>
                </div>
              </div>
              
              <div className="flex justify-between items-center mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
                <span className="text-sm text-muted">Your balance:</span>
                <span className={`font-medium ${group.your_balance > 0 ? 'amount-positive' : group.your_balance < 0 ? 'amount-negative' : ''}`}>
                  {group.your_balance > 0 ? '+' : ''}₹{Math.abs(group.your_balance).toFixed(2)}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateGroupModal 
          onClose={() => setShowCreateModal(false)} 
          onSuccess={fetchGroups} 
        />
      )}
    </div>
  );
}
