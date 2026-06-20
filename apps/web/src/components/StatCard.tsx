interface StatCardProps {
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "warning" | "success";
}

export function StatCard({ label, value, detail, tone = "default" }: StatCardProps) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}
