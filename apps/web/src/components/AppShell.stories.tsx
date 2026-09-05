import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn } from "storybook/test";

import { AppShell } from "./AppShell";
import { StatCard } from "./StatCard";
import { storyFilters, storyHealth, storyMetadata } from "../stories/fixtures";

const meta = {
  component: AppShell,
  parameters: { layout: "fullscreen" },
  title: "Components/AppShell",
} satisfies Meta<typeof AppShell>;

export default meta;
type Story = StoryObj<typeof meta>;

const baseArgs = {
  activePage: "overview" as const,
  children: (
    <div className="content-stack">
      <div className="stat-grid">
        <StatCard detail="Across the selected range" label="Total trips" value="128,430" />
        <StatCard
          detail="Within expected range"
          label="Average fare"
          tone="success"
          value="$18.40"
        />
      </div>
      <section className="panel">
        <h2>Overview notes</h2>
        <p>These stories use deterministic local fixtures and the production design tokens.</p>
      </section>
    </div>
  ),
  exportUrl: "/api/export/daily.csv",
  filters: storyFilters,
  health: storyHealth,
  isLoading: false,
  metadata: storyMetadata,
  onFilterChange: fn(),
  onPageChange: fn(),
  onReload: fn(),
};

export const DesktopConnected: Story = {
  args: baseArgs,
  globals: { viewport: "desktop" },
};

export const CompactNavigation: Story = {
  args: baseArgs,
  globals: { viewport: "compact" },
  play: async ({ args, canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole("button", { name: "Demand Trends" }));
    await expect(args.onPageChange).toHaveBeenCalledWith("demand");
  },
};

export const MobileLoading: Story = {
  args: { ...baseArgs, health: undefined, isLoading: true, metadata: undefined },
  globals: { viewport: "mobile" },
};
