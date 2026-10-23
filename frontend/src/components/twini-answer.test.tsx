import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TwiniAnswer } from "./twini-answer";

describe("TwiniAnswer", () => {
  it("renders Markdown as structured content", () => {
    const html = renderToStaticMarkup(<TwiniAnswer content={`## Patient summary
**Current rule:** Criteria met [Synthetic patient record]

- Creatinine increased
- Keep separate from future risk

| Signal | Result |
| --- | --- |
| 24-hour risk | 82% |`} />);

    expect(html).toContain("<h4>Patient summary</h4>");
    expect(html).toContain("<strong>Current rule:</strong>");
    expect(html).toContain("twini-inline-citation");
    expect(html).toContain("<ul>");
    expect(html).toContain("<table>");
    expect(html).not.toContain("| Signal | Result |");
    expect(html).not.toContain("**Current rule:**");
  });

  it("renders tables as stacked labelled records in compact surfaces", () => {
    const html = renderToStaticMarkup(<TwiniAnswer compact content={`| Piece | What it is | Key points |
| --- | --- | --- |
| Roadmap | Project plan | Eight phases |`} />);

    expect(html).not.toContain("<table>");
    expect(html).toContain("twini-answer-records");
    expect(html).toContain("aria-label=\"Result 1\"");
    expect(html).toContain("Piece");
    expect(html).toContain("Roadmap");
    expect(html).toContain("What it is");
    expect(html).toContain("Project plan");
  });
});
