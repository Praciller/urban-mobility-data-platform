import type { Meta, StoryObj } from "@storybook/react-vite";

import { StatCard } from "./StatCard";

const meta = {
  component: StatCard,
  parameters: { layout: "centered" },
  title: "Components/StatCard",
} satisfies Meta<typeof StatCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    detail: "Across the selected date range",
    label: "Total trips",
    value: "128,430",
  },
};

export const StatusVariants: Story = {
  args: { label: "Stat card variants", value: "" },
  render: () => (
    <div className="stat-grid">
      <StatCard detail="Within expected range" label="Average fare" tone="success" value="$18.40" />
      <StatCard detail="Needs review" label="Warning rows" tone="warning" value="1,204" />
      <StatCard label="Data freshness" value="Jan 02, 10:30" valueSize="compact" />
    </div>
  ),
};
