import type { Preview } from "@storybook/react-vite";

import "../src/styles.css";

const preview: Preview = {
  parameters: {
    a11y: {
      test: "error",
    },
    layout: "padded",
    viewport: {
      options: {
        compact: {
          name: "Compact (768–899px)",
          styles: { height: "900px", width: "820px" },
          type: "tablet",
        },
        desktop: {
          name: "Desktop (1440px)",
          styles: { height: "900px", width: "1440px" },
          type: "desktop",
        },
        mobile: {
          name: "Mobile (390px)",
          styles: { height: "844px", width: "390px" },
          type: "mobile1",
        },
      },
    },
  },
};

export default preview;
