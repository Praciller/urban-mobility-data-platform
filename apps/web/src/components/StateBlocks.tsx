interface EmptyStateProps {
  title: string;
  detail?: string;
}

export function LoadingState() {
  return (
    <section className="state-card" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <h1>Loading local mobility analytics</h1>
      <p>Reading the local FastAPI service and DuckDB-backed marts.</p>
    </section>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="state-card state-card--error">
      <p className="eyebrow">Read-only API</p>
      <h1>API unavailable</h1>
      <p>Start the local FastAPI service, then retry the dashboard request.</p>
      <code>uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000</code>
      <p className="error-message">{message}</p>
      <button className="button button--primary" type="button" onClick={onRetry}>
        Retry
      </button>
    </section>
  );
}

export function EmptyState({ title, detail }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}
