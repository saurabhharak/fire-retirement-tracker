import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "../PageHeader";

describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Dashboard" />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<PageHeader title="Settings" subtitle="Configure your plan" />);
    expect(screen.getByText("Configure your plan")).toBeInTheDocument();
  });
});
