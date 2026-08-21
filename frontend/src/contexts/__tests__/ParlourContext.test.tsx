import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ParlourProvider, useParlour } from "../ParlourContext";

const STORAGE_KEY = "fire_tracker_selected_parlour";

function TestConsumer() {
  const { selectedParlourId, role, setSelectedParlour } = useParlour();
  return (
    <div>
      <span data-testid="id">{selectedParlourId ?? "none"}</span>
      <span data-testid="role">{role ?? "none"}</span>
      <button onClick={() => setSelectedParlour("p1", "owner")}>Select p1</button>
    </div>
  );
}

describe("ParlourContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to no parlour when nothing stored", () => {
    render(
      <ParlourProvider>
        <TestConsumer />
      </ParlourProvider>
    );
    expect(screen.getByTestId("id").textContent).toBe("none");
    expect(screen.getByTestId("role").textContent).toBe("none");
  });

  it("persists selection to localStorage", async () => {
    render(
      <ParlourProvider>
        <TestConsumer />
      </ParlourProvider>
    );
    act(() => {
      screen.getByText("Select p1").click();
    });
    expect(screen.getByTestId("id").textContent).toBe("p1");
    expect(screen.getByTestId("role").textContent).toBe("owner");
    const stored = localStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored as string)).toEqual({ parlourId: "p1", role: "owner" });
  });

  it("reads an existing selection from localStorage on mount", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ parlourId: "p9", role: "data_entry" }));
    render(
      <ParlourProvider>
        <TestConsumer />
      </ParlourProvider>
    );
    expect(screen.getByTestId("id").textContent).toBe("p9");
    expect(screen.getByTestId("role").textContent).toBe("data_entry");
  });

  it("resets selection when setSelectedParlour is called with null", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ parlourId: "p1", role: "owner" }));
    function ResetConsumer() {
      const { selectedParlourId, setSelectedParlour } = useParlour();
      return (
        <div>
          <span data-testid="id">{selectedParlourId ?? "none"}</span>
          <button onClick={() => setSelectedParlour(null)}>Reset</button>
        </div>
      );
    }
    render(
      <ParlourProvider>
        <ResetConsumer />
      </ParlourProvider>
    );
    expect(screen.getByTestId("id").textContent).toBe("p1");
    act(() => {
      screen.getByText("Reset").click();
    });
    expect(screen.getByTestId("id").textContent).toBe("none");
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
