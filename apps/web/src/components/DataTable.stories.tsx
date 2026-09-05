import type { Meta, StoryObj } from "@storybook/react-vite";

import { DataTable, type DataColumn } from "./DataTable";
import { storyTrips, type StoryTrip } from "../stories/fixtures";

interface StoryDataTableProps {
  columns: DataColumn<StoryTrip>[];
  emptyDetail?: string;
  emptyTitle: string;
  getRowKey: (row: StoryTrip) => string | number;
  rows: StoryTrip[];
}

function StoryDataTable(props: StoryDataTableProps) {
  return <DataTable<StoryTrip> {...props} />;
}

const columns: DataColumn<StoryTrip>[] = [
  { header: "Pickup", render: (row) => row.pickup },
  { header: "Route", render: (row) => row.route },
  { align: "right", header: "Fare", render: (row) => `$${row.fare.toFixed(2)}` },
  { align: "right", header: "Miles", render: (row) => row.distance.toFixed(1) },
  { header: "Quality", render: (row) => row.status },
];

const meta = {
  component: StoryDataTable,
  parameters: { layout: "padded" },
  title: "Components/DataTable",
} satisfies Meta<StoryDataTableProps>;

export default meta;
type Story = StoryObj<StoryDataTableProps>;

export const Populated: Story = {
  args: {
    columns,
    emptyTitle: "No trips found",
    getRowKey: (row: StoryTrip) => row.pickup,
    rows: storyTrips,
  },
};

export const Empty: Story = {
  args: {
    columns,
    emptyDetail: "Try widening the date range or lowering the quality filter.",
    emptyTitle: "No trips match these filters",
    getRowKey: (row: StoryTrip) => row.pickup,
    rows: [],
  },
};
