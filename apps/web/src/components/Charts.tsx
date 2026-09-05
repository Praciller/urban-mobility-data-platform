import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "./StateBlocks";

interface LineChartPanelProps<RowT extends object> {
  data: RowT[];
  xKey: keyof RowT;
  lines: Array<{ key: keyof RowT; name: string; tone: ChartTone }>;
  emptyTitle: string;
}

interface BarChartPanelProps<RowT extends object> {
  data: RowT[];
  xKey: keyof RowT;
  bars: Array<{ key: keyof RowT; name: string; tone: ChartTone }>;
  emptyTitle: string;
}

export type ChartTone = "primary" | "secondary" | "accent" | "success" | "warning";

const chartColors: Record<ChartTone, string> = {
  primary: "var(--chart-primary)",
  secondary: "var(--chart-secondary)",
  accent: "var(--chart-accent)",
  success: "var(--chart-success)",
  warning: "var(--chart-warning)",
};

const chartAxis = {
  fill: "var(--color-text-muted)",
  fontSize: 12,
};

const chartHeightPx = 288;

function formatAxisLabel(value: unknown): string {
  const label = String(value);
  return label.length > 18 ? `${label.slice(0, 15)}…` : label;
}

export function LineChartPanel<RowT extends object>({
  data,
  xKey,
  lines,
  emptyTitle,
}: LineChartPanelProps<RowT>) {
  if (data.length === 0) return <EmptyState title={emptyTitle} />;

  return (
    <div
      aria-label={`${lines.map((line) => line.name).join(" and ")} chart with ${data.length} data points`}
      className="chart"
      role="img"
    >
      <ResponsiveContainer width="100%" height={chartHeightPx}>
        <LineChart data={data}>
          <CartesianGrid stroke="var(--color-hairline)" strokeDasharray="3 3" />
          <XAxis
            axisLine={{ stroke: "var(--color-hairline)" }}
            dataKey={String(xKey)}
            height={44}
            minTickGap={12}
            tick={chartAxis}
            tickFormatter={formatAxisLabel}
            tickLine={false}
          />
          <YAxis
            axisLine={{ stroke: "var(--color-hairline)" }}
            tick={chartAxis}
            tickLine={false}
            width={56}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-hairline)",
              borderRadius: "var(--radius-sm)",
              boxShadow: "var(--elevation-tooltip)",
            }}
            labelStyle={{ color: "var(--color-ink)" }}
          />
          <Legend wrapperStyle={{ color: "var(--color-text-muted)", fontSize: 12 }} />
          {lines.map((line) => (
            <Line
              dataKey={String(line.key)}
              dot={false}
              key={String(line.key)}
              name={line.name}
              stroke={chartColors[line.tone]}
              strokeWidth={2}
              type="monotone"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BarChartPanel<RowT extends object>({
  data,
  xKey,
  bars,
  emptyTitle,
}: BarChartPanelProps<RowT>) {
  if (data.length === 0) return <EmptyState title={emptyTitle} />;

  return (
    <div
      aria-label={`${bars.map((bar) => bar.name).join(" and ")} chart with ${data.length} data points`}
      className="chart"
      role="img"
    >
      <ResponsiveContainer width="100%" height={chartHeightPx}>
        <BarChart data={data}>
          <CartesianGrid stroke="var(--color-hairline)" strokeDasharray="3 3" />
          <XAxis
            axisLine={{ stroke: "var(--color-hairline)" }}
            dataKey={String(xKey)}
            height={44}
            minTickGap={12}
            tick={chartAxis}
            tickFormatter={formatAxisLabel}
            tickLine={false}
          />
          <YAxis
            axisLine={{ stroke: "var(--color-hairline)" }}
            tick={chartAxis}
            tickLine={false}
            width={56}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-hairline)",
              borderRadius: "var(--radius-sm)",
              boxShadow: "var(--elevation-tooltip)",
            }}
            labelStyle={{ color: "var(--color-ink)" }}
          />
          <Legend wrapperStyle={{ color: "var(--color-text-muted)", fontSize: 12 }} />
          {bars.map((bar) => (
            <Bar dataKey={String(bar.key)} fill={chartColors[bar.tone]} key={String(bar.key)} name={bar.name} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
