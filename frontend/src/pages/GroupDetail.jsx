import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import StatCard from '../components/StatCard';
import ImportWizard from '../components/ImportWizard';
import AddExpenseModal from '../components/AddExpenseModal';
import AddMemberModal from '../components/AddMemberModal';

export default function GroupDetail() {
  const { groupId } = useParams();
  const { user } = useAuth();
  
  const [group, setGroup] = useState(null);
  const [balances, setBalances] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [activeTab, setActiveTab] = useState('balances');
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);
  const [showAddExpense, setShowAddExpense] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);

  const fetchGroupData = async () => {
    try {
      const [groupData, balancesData, expensesData] = await Promise.all([
        apiClient.get(`/groups/${groupId}`),
        apiClient.get(`/groups/${groupId}/balances`),
        apiClient.get(`/groups/${groupId}/expenses`)
      ]);
      setGroup(groupData);
      setBalances(balancesData);
      setExpenses(expensesData);
    } catch (err) {
      console.error("Failed to load group data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroupData();
  }, [groupId]);

  if (loading) return <div>Loading...</div>;
  if (!group) return <div>Group not found</div>;

  // Calculate quick stats
  const memberCount = group.members?.filter(m => !m.left_at)?.length || 0;
  const yourBalance = balances?.balances?.find(b => b.user_id === user.id)?.net_balance || 0;
  
  // Total debt in group is the sum of all positive balances
  const totalDebt = balances?.balances ? balances.balances.filter(b => b.net_balance > 0).reduce((a, b) => a + b.net_balance, 0) : 0;

  return (
    <div>
      <Link to="/" className="text-muted text-sm flex items-center gap-2 mb-6 hover:text-main">
        <span>←</span> Back to Dashboard
      </Link>

      <div className="flex justify-between items-start mb-8">
        <div className="flex items-center gap-4">
          <div className="avatar" style={{ width: '56px', height: '56px', fontSize: '24px', backgroundColor: '#eef2ff', color: '#6366f1' }}>
            {group.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl mb-1">{group.name}</h1>
            {group.description && <p className="text-sm text-muted">📋 {group.description}</p>}
          </div>
        </div>
        
        <div className="flex gap-4">
          <button className="btn btn-outline flex items-center gap-2" onClick={() => setShowImport(true)}>
            <span>📄</span> Import CSV
          </button>
          <button className="btn btn-primary flex items-center gap-2" onClick={() => setShowAddExpense(true)}>
            <span>+</span> Add Expense
          </button>
        </div>
      </div>

      <div className="flex gap-6 mb-8">
        <StatCard 
          title="Total expenses" 
          value={`₹${expenses.reduce((sum, e) => sum + e.amount, 0).toFixed(2)}`} 
        />
        <StatCard 
          title="Total group debt" 
          value={`₹${totalDebt.toFixed(2)}`} 
        />
        <StatCard 
          title="Your balance" 
          value={`${yourBalance > 0 ? '+' : ''}₹${Math.abs(yourBalance).toFixed(2)}`} 
          valueColor={yourBalance > 0 ? 'var(--success)' : yourBalance < 0 ? 'var(--danger)' : 'var(--text-main)'}
        />
        <StatCard 
          title="Group members" 
          value={memberCount} 
        />
      </div>

      {/* Tabs */}
      <div className="tabs">
        <div className={`tab ${activeTab === 'balances' ? 'active' : ''}`} onClick={() => setActiveTab('balances')}>
          <span>⚖</span> Balances
        </div>
        <div className={`tab ${activeTab === 'expenses' ? 'active' : ''}`} onClick={() => setActiveTab('expenses')}>
          <span>🧾</span> Expenses <span className="tab-count">{expenses.length}</span>
        </div>
        <div className={`tab ${activeTab === 'settlements' ? 'active' : ''}`} onClick={() => setActiveTab('settlements')}>
          <span>🤝</span> Settlements
        </div>
        <div className={`tab ${activeTab === 'members' ? 'active' : ''}`} onClick={() => setActiveTab('members')}>
          <span>👥</span> Members <span className="tab-count">{memberCount}</span>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'balances' && (
        <div className="flex gap-6" style={{ alignItems: 'flex-start' }}>
          
          <div className="card" style={{ flex: 2 }}>
            <h3 className="font-semibold mb-1">Settlement plan (who owes whom?)</h3>
            <p className="text-sm text-muted mb-6">The most efficient way to settle all debts.</p>
            
            {(!balances || !balances.debts || balances.debts.length === 0) ? (
              <div className="text-center text-muted py-4">No debts to settle!</div>
            ) : (
              <div className="flex-col gap-4">
                {balances.debts.map((debt, idx) => {
                  const fromUser = group.members.find(m => m.user_id === debt.from_user);
                  const toUser = group.members.find(m => m.user_id === debt.to_user);
                  return (
                    <div key={idx} className="flex items-center justify-between py-2">
                      <div className="flex items-center gap-4">
                        <div className="avatar" style={{ width: '32px', height: '32px', fontSize: '14px' }}>
                          {fromUser?.display_name?.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-col">
                          <span className="font-medium text-sm">{fromUser?.display_name}</span>
                          <span className="text-muted" style={{ fontSize: '11px' }}>owes</span>
                        </div>
                        
                        <span className="text-muted">➔</span>
                        
                        <div className="avatar" style={{ width: '32px', height: '32px', fontSize: '14px', backgroundColor: 'var(--success-bg)', color: 'var(--success)' }}>
                          {toUser?.display_name?.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium text-sm">{toUser?.display_name}</span>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <span className="font-semibold">₹{debt.amount.toFixed(2)}</span>
                        <button className="badge badge-primary" style={{ border: 'none', cursor: 'pointer', padding: '6px 12px' }}>
                          Settle up
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="card" style={{ flex: 1 }}>
            <h3 className="font-semibold mb-6">Member balances</h3>
            
            <div className="flex-col gap-4">
              {group.members?.map(member => {
                const bal = balances?.balances?.find(b => b.user_id === member.user_id)?.net_balance || 0;
                if (member.left_at) return null; // Don't show inactive members by default
                
                return (
                  <div key={member.id} className="flex justify-between items-center py-2" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-3">
                      <div className="avatar" style={{ width: '28px', height: '28px', fontSize: '12px' }}>
                        {member.display_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium">{member.display_name}</span>
                    </div>
                    
                    <span className={`badge ${bal > 0 ? 'badge-success' : bal < 0 ? 'badge-danger' : 'text-muted'}`}>
                      {bal > 0 ? '+' : ''}₹{Math.abs(bal).toFixed(2)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          
        </div>
      )}

      {activeTab === 'expenses' && (
        <div className="card p-0">
          {expenses.length === 0 ? (
             <div className="text-center text-muted py-8">
               <p className="mb-4">No expenses yet. Add one to get started!</p>
             </div>
          ) : (
            <div className="flex-col">
              {expenses.map((exp, idx) => {
                const payer = group.members.find(m => m.user_id === exp.paid_by);
                // Basic split info since the UI is simple
                return (
                  <div key={exp.id} className="flex justify-between items-center py-4 px-6" style={{ borderBottom: idx < expenses.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <div className="flex items-center gap-4">
                      <div className="avatar bg-gray-100 text-gray-600" style={{ width: '40px', height: '40px', fontSize: '20px' }}>
                        🧾
                      </div>
                      <div className="flex-col">
                        <span className="font-semibold">{exp.title}</span>
                        <span className="text-muted text-sm">
                          {payer ? `${payer.display_name} paid` : 'Someone paid'}
                        </span>
                      </div>
                    </div>
                    <div className="flex-col" style={{ alignItems: 'flex-end' }}>
                      <span className="font-semibold">₹{exp.amount.toFixed(2)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      
      {activeTab === 'settlements' && (
        <div className="card">
          <div className="text-center text-muted py-8">
            <p className="mb-4">Settlements history coming soon...</p>
          </div>
        </div>
      )}

      {activeTab === 'members' && (
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-semibold">Group Members</h3>
            <button className="btn btn-outline text-sm" onClick={() => setShowAddMember(true)}>+ Add Member</button>
          </div>
          
          <div className="flex-col gap-4">
            {group.members.map(member => (
              <div key={member.id} className="flex items-center justify-between py-2 border-b border-gray-100">
                <div className="flex items-center gap-3">
                  <div className="avatar" style={{ width: '36px', height: '36px', fontSize: '14px' }}>
                    {member.display_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-col">
                    <span className="font-medium">{member.display_name} {member.user_id === user.id ? '(You)' : ''}</span>
                    <span className="text-xs text-muted">{member.email}</span>
                  </div>
                </div>
                <div className="text-xs text-muted">
                  {member.role === 'admin' ? 'Admin' : 'Member'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showImport && (
        <ImportWizard 
          groupId={groupId} 
          onClose={() => setShowImport(false)} 
          onSuccess={fetchGroupData} 
        />
      )}

      {showAddExpense && (
        <AddExpenseModal 
          groupId={groupId} 
          members={group.members} 
          onClose={() => setShowAddExpense(false)} 
          onSuccess={fetchGroupData} 
        />
      )}

      {showAddMember && (
        <AddMemberModal 
          groupId={groupId} 
          onClose={() => setShowAddMember(false)} 
          onSuccess={fetchGroupData} 
        />
      )}

    </div>
  );
}
