interface EmptyStateProps {
  title: string;
  detail?: string;
}

export function LoadingState({ hosted = false }: { hosted?: boolean }) {
  return (
    <section aria-live="polite" className="state-card" role="status">
      <div className="spinner" aria-hidden="true" />
      <h1>{hosted ? "Loading mobility analytics" : "Loading local mobility analytics"}</h1>
      <p>
        {hosted
          ? "The demo API may take a moment to start after being idle."
          : "Reading the local FastAPI service and DuckDB-backed marts."}
      </p>
    </section>
  );
}

export function ErrorState({
  hosted = false,
  message,
  onRetry,
}: {
  hosted?: boolean;
  message: string;
  onRetry: () => void;
}) {
  return (
    <section aria-live="assertive" className="state-card state-card--error" role="alert">
      <h1>API unavailable</h1>
      {hosted ? (
        <p>The demo API may still be starting. Wait a moment, then select Retry.</p>
      ) : (
        <>
          <p>Start the local FastAPI service, then retry the dashboard request.</p>
          <code>uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000</code>
        </>
      )}
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
