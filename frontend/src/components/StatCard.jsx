export default function StatCard({ title, value, subtitle, valueColor }) {
  return (
    <div className="card flex-col justify-center" style={{ flex: 1, minWidth: '200px' }}>
      <div className="text-muted text-sm font-medium mb-1">
        {title}
      </div>
      <div className="text-xl font-semibold" style={{ color: valueColor || 'var(--text-main)' }}>
        {value}
      </div>
      {subtitle && (
        <div className="text-muted text-sm mt-1">
          {subtitle}
        </div>
      )}
    </div>
  );
}
