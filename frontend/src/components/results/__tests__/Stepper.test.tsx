import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Stepper } from "../Stepper";

const steps = [
  { step: "framework", label: "Loading the framework pack", done: true },
  { step: "materiality_factors", label: "Rating materiality factors", done: true },
  { step: "inherent_risk_tier", label: "Choosing the inherent risk tier", done: true },
];

describe("the progress stepper", () => {
  it("lists the steps in the order they arrived", () => {
    render(<Stepper steps={steps} />);
    const labels = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(labels).toEqual([
      "Loading the framework pack",
      "Rating materiality factors",
      "Choosing the inherent risk tier",
    ]);
  });

  it("treats only the most recent step as in flight", () => {
    const { container } = render(<Stepper steps={steps} />);
    // Everything before the last has completed; the last is still spinning.
    expect(container.querySelectorAll(".animate-spin")).toHaveLength(1);
    const items = screen.getAllByRole("listitem");
    expect(items[items.length - 1].querySelector(".animate-spin")).not.toBeNull();
  });

  it("renders nothing but the frame before any step has arrived", () => {
    render(<Stepper steps={[]} />);
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
    expect(screen.getByText(/Running assessment/)).toBeInTheDocument();
  });
});
