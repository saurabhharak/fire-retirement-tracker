import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { UseQueryResult } from "@tanstack/react-query";
import GrowthProjection from "../GrowthProjection";
import type { GrowthRow } from "../../hooks/useProjections";

// Mock the projection hooks to return fixed rows so the page can render.
const GROWTH_ROWS: GrowthRow[] = [
  { year: 0, age: 30, monthly_sip: 50000, annual_inv: 0, cumulative: 0, portfolio: 0, gains: 0, equity_value: 0, debt_gold_cash: 0 },
  { year: 1, age: 31, monthly_sip: 50000, annual_inv: 600000, cumulative: 600000, portfolio: 600000, gains: 0, equity_value: 0, debt_gold_cash: 0 },
  { year: 2, age: 32, monthly_sip: 55000, annual_inv: 660000, cumulative: 1260000, portfolio: 1300000, gains: 40000, equity_value: 0, debt_gold_cash: 0 },
];

const FIRE_INPUTS = {
  dob: "1997-07-11",
  retirement_age: 50,
  life_expectancy: 90,
  your_sip: 50000,
  wife_sip: 0,
  step_up_pct: 0.1,
  existing_corpus: 0,
  equity_return: 0.11,
  debt_return: 0.07,
  precious_metals_return: 0.09,
  cash_return: 0.035,
  inflation: 0.06,
  swr: 0.03,
  equity_pct: 0.8,
  precious_metals_pct: 0.05,
  cash_pct: 0.02,
  monthly_expense: 125000,
};

vi.mock("../../hooks/useProjections", () => ({
  useGrowthProjection: vi.fn(),
  useRetirementAnalysis: () => ({ data: undefined, isLoading: false }),
  useFundAllocation: () => ({ data: [], isLoading: false }),
  useMonthlySips: () => ({ data: [] }),
}));

vi.mock("../../hooks/useFireInputs", () => ({
  useFireInputs: () => ({ data: FIRE_INPUTS, isLoading: false }),
}));

import { useGrowthProjection } from "../../hooks/useProjections";
const mockUseGrowthProjection = vi.mocked(useGrowthProjection);

function queryResult<T>(data: T): UseQueryResult<T, Error> {
  return {
    data,
    isLoading: false,
    isError: false,
    error: null,
    isPending: false,
    isLoadingError: false,
    isRefetchError: false,
    dataUpdatedAt: 0,
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    errorUpdateCount: 0,
    isFetched: true,
    isFetchedAfterMount: true,
    isFetching: false,
    isPaused: false,
    isPlaceholderData: false,
    isRefetching: false,
    isStale: false,
    isSuccess: true,
    refetch: vi.fn(),
    remove: vi.fn(),
    fetchStatus: "idle",
    status: "success",
  } as unknown as UseQueryResult<T, Error>;
}

describe("GrowthProjection debounce", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGrowthProjection.mockImplementation(() => queryResult(GROWTH_ROWS));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps BOTH slider changes after moving two sliders quickly", async () => {
    render(<GrowthProjection />);

    // Open the what-if panel
    fireEvent.click(screen.getByText("What-If Scenarios"));

    // Find sliders: the label span lives inside a flex-col div that also
    // contains the <input type=range>.
    const sipLabel = screen.getByText("Your Monthly SIP (₹)");
    const equityLabel = screen.getByText("Equity Return (%)");
    const sipSlider = sipLabel.closest("div.flex.flex-col")?.querySelector("input");
    const equitySlider = equityLabel.closest("div.flex.flex-col")?.querySelector("input");
    expect(sipSlider).toBeTruthy();
    expect(equitySlider).toBeTruthy();

    // Move both sliders within the 500ms debounce window.
    fireEvent.change(sipSlider as HTMLInputElement, { target: { value: "60000" } });
    fireEvent.change(equitySlider as HTMLInputElement, { target: { value: "12" } });

    // Let the (single) debounce timer fire.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 600));
    });

    // The scenario API params must contain BOTH overrides.
    await waitFor(() => {
      const lastCall = mockUseGrowthProjection.mock.calls.at(-1);
      expect(lastCall?.[0]).toEqual(
        expect.objectContaining({ your_sip: 60000, equity_return: 0.12 }),
      );
    });
  });

  it("does not lose a slider change when two sliders move in quick succession", async () => {
    render(<GrowthProjection />);
    fireEvent.click(screen.getByText("What-If Scenarios"));

    const sipLabel = screen.getByText("Your Monthly SIP (₹)");
    const equityLabel = screen.getByText("Equity Return (%)");
    const sipSlider = sipLabel.closest("div.flex.flex-col")?.querySelector("input");
    const equitySlider = equityLabel.closest("div.flex.flex-col")?.querySelector("input");
    expect(sipSlider).toBeTruthy();

    fireEvent.change(sipSlider as HTMLInputElement, { target: { value: "70000" } });
    fireEvent.change(equitySlider as HTMLInputElement, { target: { value: "13" } });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 600));
    });

    await waitFor(() => {
      const lastCall = mockUseGrowthProjection.mock.calls.at(-1);
      expect(lastCall?.[0]).toEqual(
        expect.objectContaining({ your_sip: 70000, equity_return: 0.13 }),
      );
    });
  });
});
