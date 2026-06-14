import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await register(email, displayName, password);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Failed to register');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container items-center justify-center">
      <div className="card" style={{ width: '100%', maxWidth: '400px' }}>
        <h2 className="text-xl font-semibold mb-6 text-center" style={{ color: 'var(--primary)' }}>
          Join Spreetail
        </h2>
        
        {error && (
          <div className="badge badge-danger mb-4" style={{ display: 'block', textAlign: 'center', padding: '8px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex-col gap-4">
          <div className="flex-col gap-2">
            <label className="text-sm font-medium">Your Name</label>
            <input 
              type="text" 
              required 
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="e.g. Aisha"
            />
          </div>

          <div className="flex-col gap-2">
            <label className="text-sm font-medium">Email address</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="name@example.com"
            />
          </div>
          
          <div className="flex-col gap-2">
            <label className="text-sm font-medium">Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              minLength={6}
            />
          </div>
          
          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%', marginTop: '8px', padding: '12px' }}
            disabled={loading}
          >
            {loading ? 'Creating account...' : 'Sign up'}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-6">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
