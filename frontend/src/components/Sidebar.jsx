import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="avatar">S</div>
        Spreetail
      </div>

      <div className="sidebar-menu">
        <div className="sidebar-section-title">Menu</div>
        <NavLink to="/" className={({isActive}) => `sidebar-link ${isActive ? 'active' : ''}`} end>
          ⌂ Dashboard
        </NavLink>
        {/* We keep Groups active if we are on any group page */}
        <NavLink to="/groups" className={({isActive}) => `sidebar-link ${isActive || window.location.pathname.startsWith('/groups') ? 'active' : ''}`}>
          ▤ Groups
        </NavLink>
        <NavLink to="/expenses" className={({isActive}) => `sidebar-link ${isActive ? 'active' : ''}`}>
          ☰ All expenses
        </NavLink>
        <NavLink to="/activity" className={({isActive}) => `sidebar-link ${isActive ? 'active' : ''}`}>
          ↻ Activity
        </NavLink>

        <div className="sidebar-section-title" style={{ marginTop: '24px' }}>Account</div>
        <NavLink to="/settings" className={({isActive}) => `sidebar-link ${isActive ? 'active' : ''}`}>
          ⚙ Settings
        </NavLink>
        <NavLink to="/help" className={({isActive}) => `sidebar-link ${isActive ? 'active' : ''}`}>
          ❓ Help
        </NavLink>
      </div>

      <div className="sidebar-footer">
        <div className="avatar" style={{ width: '32px', height: '32px', fontSize: '14px' }}>
          {user?.display_name?.charAt(0).toUpperCase() || '?'}
        </div>
        <div className="flex-col" style={{ flex: 1, overflow: 'hidden' }}>
          <div className="font-semibold text-sm" style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
            {user?.display_name || 'Loading...'}
          </div>
          <div className="text-muted" style={{ fontSize: '11px' }}>
            Active session
          </div>
        </div>
        <button onClick={logout} className="btn-ghost" title="Logout" style={{ padding: '4px' }}>
          <span style={{ fontSize: '16px' }}>🚪</span>
        </button>
      </div>
    </aside>
  );
}
