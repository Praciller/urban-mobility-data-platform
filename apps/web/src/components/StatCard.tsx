interface StatCardProps {
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "warning" | "success";
  valueSize?: "default" | "compact";
}

export function StatCard({ label, value, detail, tone = "default", valueSize = "default" }: StatCardProps) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <span>{label}</span>
      <strong className={valueSize === "compact" ? "stat-card__value--compact" : undefined}>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}
