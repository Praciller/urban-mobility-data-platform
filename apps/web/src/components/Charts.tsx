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
  lines: Array<{ key: keyof RowT; name: string; color: string }>;
  emptyTitle: string;
}

interface BarChartPanelProps<RowT extends object> {
  data: RowT[];
  xKey: keyof RowT;
  bars: Array<{ key: keyof RowT; name: string; color: string }>;
  emptyTitle: string;
}

export function LineChartPanel<RowT extends object>({
  data,
  xKey,
  lines,
  emptyTitle,
}: LineChartPanelProps<RowT>) {
  if (data.length === 0) return <EmptyState title={emptyTitle} />;

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={String(xKey)} tickLine={false} />
          <YAxis tickLine={false} width={64} />
          <Tooltip />
          <Legend />
          {lines.map((line) => (
            <Line
              dataKey={String(line.key)}
              dot={false}
              key={String(line.key)}
              name={line.name}
              stroke={line.color}
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
    <div className="chart">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={String(xKey)} tickLine={false} />
          <YAxis tickLine={false} width={64} />
          <Tooltip />
          <Legend />
          {bars.map((bar) => (
            <Bar dataKey={String(bar.key)} fill={bar.color} key={String(bar.key)} name={bar.name} radius={[6, 6, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
