import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("renders message", () => {
    render(<EmptyState message="No data yet" />);
    expect(screen.getByText("No data yet")).toBeInTheDocument();
  });

  it("renders action button and calls handler", () => {
    const handler = vi.fn();
    render(<EmptyState message="Empty" actionLabel="Add" onAction={handler} />);
    fireEvent.click(screen.getByText("Add"));
    expect(handler).toHaveBeenCalledOnce();
  });
});
