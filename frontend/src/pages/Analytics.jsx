import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';

export default function Analytics() {
  const { groupId } = useParams();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await apiClient.get(`/groups/${groupId}/analytics/by-category`);
        setAnalytics(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [groupId]);

  if (loading) return <div>Loading...</div>;
  if (!analytics) return <div>Failed to load analytics</div>;

  return (
    <div>
      <Link to={`/groups/${groupId}`} className="text-muted text-sm flex items-center gap-2 mb-6 hover:text-main">
        <span>←</span> Back to Group
      </Link>
      
      <h1 className="text-xl mb-8">Spending Analytics</h1>
      
      <div className="card mb-8">
        <h2 className="text-lg mb-4">Total Spending: ₹{analytics.grand_total.toFixed(2)}</h2>
        
        <div className="flex-col gap-4">
          {analytics.categories.map((cat, idx) => (
            <div key={idx} className="flex justify-between items-center py-2" style={{ borderBottom: '1px solid var(--border)' }}>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: '20px' }}>{cat.icon}</span>
                <span className="font-medium">{cat.category_name}</span>
                <span className="text-muted text-sm">({cat.count} expenses)</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-semibold">₹{cat.total.toFixed(2)}</span>
                <span className="badge badge-primary">{cat.percentage}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
