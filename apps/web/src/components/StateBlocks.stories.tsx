import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn } from "storybook/test";

import { EmptyState, ErrorState, LoadingState } from "./StateBlocks";

const meta = {
  parameters: { layout: "centered" },
  title: "Components/StateBlocks",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;
type ErrorStory = StoryObj<{ message: string; onRetry: () => void }>;

export const Loading: Story = {
  render: () => <LoadingState />,
};

export const Empty: Story = {
  render: () => (
    <EmptyState
      detail="Try adjusting the date range or selecting another page."
      title="No results yet"
    />
  ),
};

export const ErrorWithRetry: ErrorStory = {
  args: { onRetry: fn(), message: "The local API returned HTTP 503." },
  render: (args) => <ErrorState {...args} />,
  play: async ({ args, canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole("button", { name: "Retry" }));
    await expect(args.onRetry).toHaveBeenCalledOnce();
  },
};
