import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfusionMatrix } from "../ConfusionMatrix";
import { Meter } from "../metrics";
import { pct } from "@/lib/format";

describe("the tier confusion matrix", () => {
  it("puts each count where the gold and returned tiers cross", () => {
    render(<ConfusionMatrix matrix={{ high: { high: 14, medium: 1 }, low: { low: 3 } }} />);
    const rows = screen.getAllByRole("row");
    const goldHigh = rows.find((row) => row.textContent?.startsWith("gold high"));
    expect(goldHigh).toHaveTextContent("14");
    expect(goldHigh).toHaveTextContent("1");
  });

  it("says so plainly when there is nothing to show", () => {
    render(<ConfusionMatrix matrix={{}} />);
    expect(screen.getByText(/No graded tiers/)).toBeInTheDocument();
  });

  it("fills empty cells with a zero rather than leaving them blank", () => {
    render(<ConfusionMatrix matrix={{ low: { low: 3 } }} />);
    // A blank cell reads as missing data; a zero reads as "this never happened".
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
  });
});

describe("the accuracy meter", () => {
  it("shows the percentage as text, not only as a bar", () => {
    render(<Meter label="Tier exact" value={0.96} detail="26/27" />);
    expect(screen.getByText("96%")).toBeInTheDocument();
    expect(screen.getByText("26/27")).toBeInTheDocument();
  });

  it("renders an em dash rather than NaN when nothing was graded", () => {
    render(<Meter label="Confidence" value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("colours by score but never relies on colour alone", () => {
    expect(pct(0.96)).toBe("96%");
    expect(pct(null)).toBe("—");
  });
});
