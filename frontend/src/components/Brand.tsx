export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? "brand--compact" : ""}`} aria-label="Orion University">
      <span className="brand__mark" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none">
          <path d="m12 29.5 12-20 12 20-12 7-12-7Z" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" />
          <path d="M17 27h14M24 13v24" stroke="var(--brand-mint)" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </span>
      {!compact && (
        <span className="brand__type">
          <strong>ORION</strong>
          <small>UNIVERSITY</small>
        </span>
      )}
    </div>
  );
}

