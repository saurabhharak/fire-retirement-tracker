import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricCard } from "../MetricCard";

describe("MetricCard", () => {
  it("renders label and formatted value", () => {
    render(<MetricCard label="Test Metric" value={125000} />);
    expect(screen.getByText("Test Metric")).toBeInTheDocument();
    expect(screen.getByText("₹1,25,000")).toBeInTheDocument();
  });

  it("renders with custom prefix", () => {
    render(<MetricCard label="Rate" value={48} prefix="" suffix="%" />);
    expect(screen.getByText("48%")).toBeInTheDocument();
  });

  it("shows positive delta in green", () => {
    render(<MetricCard label="Surplus" value={50000} delta={5000} />);
    expect(screen.getByText(/5,000/)).toBeInTheDocument();
  });

  it("shows negative delta", () => {
    render(<MetricCard label="Deficit" value={50000} delta={-3000} />);
    expect(screen.getByText(/3,000/)).toBeInTheDocument();
  });
});
