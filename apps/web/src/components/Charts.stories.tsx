import type { Meta, StoryObj } from "@storybook/react-vite";

import { BarChartPanel, LineChartPanel } from "./Charts";
import { storyTrends, type StoryTrend } from "../stories/fixtures";

const meta = {
  parameters: { layout: "padded" },
  title: "Components/Charts",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const TrendPanels: Story = {
  render: () => (
    <div className="chart-grid">
      <section className="panel">
        <h2>Trips and revenue trend</h2>
        <LineChartPanel<StoryTrend>
          data={storyTrends}
          emptyTitle="No daily trend data"
          lines={[{ key: "trips", name: "Trips", tone: "primary" }]}
          xKey="label"
        />
      </section>
      <section className="panel">
        <h2>Daily trips</h2>
        <BarChartPanel<StoryTrend>
          bars={[{ key: "trips", name: "Trips", tone: "accent" }]}
          data={storyTrends}
          emptyTitle="No daily trip data"
          xKey="label"
        />
      </section>
    </div>
  ),
};

export const Empty: Story = {
  render: () => (
    <LineChartPanel<StoryTrend>
      data={[]}
      emptyTitle="No trend data for this range"
      lines={[]}
      xKey="label"
    />
  ),
};
