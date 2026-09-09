import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Parlour from "../Parlour";
import type { UseQueryResult } from "@tanstack/react-query";

// Mock the hooks the page depends on.
const PARLOURS = [
  { id: "p1", name: "Vrindavan Treats", role: "owner", sarvam_starting_credits: 100 },
];

const SALES = [
  { id: "s1", parlour_id: "p1", sale_date: "2026-08-15", cash_amount: 2750, online_amount: 5769 },
];

const INVOICES = [
  { id: "inv1", parlour_id: "p1", distributor: "M/S.MAHAVIR", bill_no: "AMUL2602568", bill_date: "2026-07-01", total_amount: 1761.88 },
];

const SUMMARY = {
  total_sales: 8519,
  total_purchases: 1761.88,
  total_expenses: 0,
  profit: 6757.12,
  sales_cash: 2750,
  sales_online: 5769,
  invoice_count: 1,
  period: "month",
  period_key: "2026-08",
};

const TRENDS = {
  labels: ["2026-07", "2026-08"],
  sales: [0, 8519],
  purchases: [1761.88, 0],
  expenses: [0, 0],
  profit: [-1761.88, 8519],
};

const SARVAM = { starting: 100, used: 5, remaining: 95, call_count: 2, cost_inr: 0.25 };

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

vi.mock("../../hooks/useParlours", () => ({
  useParlours: vi.fn(),
}));

vi.mock("../../hooks/useAmulSales", () => ({
  useAmulSales: vi.fn(),
}));

vi.mock("../../hooks/useAmulPurchases", () => ({
  useAmulPurchases: vi.fn(),
}));

vi.mock("../../hooks/useAmulInvoices", () => ({
  useAmulInvoices: vi.fn(),
}));

vi.mock("../../hooks/useAmulOtherExpenses", () => ({
  useAmulOtherExpenses: vi.fn(),
}));

vi.mock("../../hooks/useAmulAnalytics", () => ({
  useAmulAnalytics: vi.fn(),
}));

vi.mock("../../hooks/useSarvamUsage", () => ({
  useSarvamUsage: vi.fn(),
}));

vi.mock("../../hooks/useParlourMembers", () => ({
  useParlourMembers: vi.fn(),
}));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", email: "saurabhharak1997@gmail.com" } }),
}));

import { useParlours } from "../../hooks/useParlours";
import { useAmulSales } from "../../hooks/useAmulSales";
import { useAmulPurchases } from "../../hooks/useAmulPurchases";
import { useAmulInvoices } from "../../hooks/useAmulInvoices";
import { useAmulOtherExpenses } from "../../hooks/useAmulOtherExpenses";
import { useAmulAnalytics } from "../../hooks/useAmulAnalytics";
import { useSarvamUsage } from "../../hooks/useSarvamUsage";
import { useParlourMembers } from "../../hooks/useParlourMembers";

const mockUseParlours = vi.mocked(useParlours);
const mockUseAmulSales = vi.mocked(useAmulSales);
const mockUseAmulPurchases = vi.mocked(useAmulPurchases);
const mockUseAmulInvoices = vi.mocked(useAmulInvoices);
const mockUseAmulOtherExpenses = vi.mocked(useAmulOtherExpenses);
const mockUseAmulAnalytics = vi.mocked(useAmulAnalytics);
const mockUseSarvamUsage = vi.mocked(useSarvamUsage);
const mockUseParlourMembers = vi.mocked(useParlourMembers);

function mockOwnerHooks() {
  mockUseParlours.mockReturnValue({
    parlours: PARLOURS,
    isLoading: false,
    save: vi.fn(),
  } as unknown as ReturnType<typeof useParlours>);

  mockUseAmulSales.mockReturnValue({
    sales: SALES,
    isLoading: false,
    save: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  } as unknown as ReturnType<typeof useAmulSales>);

  mockUseAmulPurchases.mockReturnValue({
    purchases: [],
    isLoading: false,
    save: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  } as unknown as ReturnType<typeof useAmulPurchases>);

  mockUseAmulInvoices.mockReturnValue({
    invoices: INVOICES,
    isLoading: false,
    upload: vi.fn(),
    update: vi.fn(),
    updateItem: vi.fn(),
    remove: vi.fn(),
  } as unknown as ReturnType<typeof useAmulInvoices>);

  mockUseAmulOtherExpenses.mockReturnValue({
    expenses: [],
    isLoading: false,
    save: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  } as unknown as ReturnType<typeof useAmulOtherExpenses>);

  mockUseAmulAnalytics.mockReturnValue(
    queryResult({ summary: SUMMARY, trends: TRENDS })
  );

  mockUseSarvamUsage.mockReturnValue(
    queryResult(SARVAM)
  );

  mockUseParlourMembers.mockReturnValue({
    members: [
      { id: "m1", member_id: "u1", role: "owner" },
    ],
    isLoading: false,
    addMember: vi.fn(),
    removeMember: vi.fn(),
  } as unknown as ReturnType<typeof useParlourMembers>);
}

describe("Parlour page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem(
      "fire_tracker_selected_parlour",
      JSON.stringify({ parlourId: "p1", role: "owner" })
    );
    mockOwnerHooks();
  });

  it("renders summary cards when analytics loaded", async () => {
    render(<Parlour />);
    // Navigate to Analytics tab
    await waitFor(() => {
      expect(screen.getByText("Analytics")).toBeTruthy();
    });
    fireEvent.click(screen.getByText("Analytics"));
    expect(screen.getByText("Total Sales")).toBeTruthy();
    expect(screen.getByText("Total Purchases")).toBeTruthy();
    expect(screen.getByText("Profit")).toBeTruthy();
  });

  it("shows empty state when no sales", async () => {
    mockUseAmulSales.mockReturnValue({
      sales: [],
      isLoading: false,
      save: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
    } as unknown as ReturnType<typeof useAmulSales>);
    render(<Parlour />);
    await waitFor(() => {
      expect(screen.getByText(/No sales yet/i)).toBeTruthy();
    });
  });

  it("period selector changes analytics query", async () => {
    render(<Parlour />);
    await waitFor(() => screen.getByText("Analytics"));
    fireEvent.click(screen.getByText("Analytics"));
    fireEvent.change(screen.getByLabelText(/Period/i), { target: { value: "year" } });
    await waitFor(() => {
      const calls = mockUseAmulAnalytics.mock.calls;
      // Second arg carries the { period, periodValue } options
      expect(calls.at(-1)?.[1]).toEqual(
        expect.objectContaining({ period: "year", periodValue: expect.stringMatching(/^\d{4}$/) })
      );
    });
  });

  it("does not render the Sarvam tab", async () => {
    localStorage.setItem(
      "fire_tracker_selected_parlour",
      JSON.stringify({ parlourId: "p1", role: "data_entry" })
    );
    mockUseParlours.mockReturnValue({
      parlours: [{ id: "p1", name: "Vrindavan Treats", role: "data_entry" }],
      isLoading: false,
      save: vi.fn(),
    } as unknown as ReturnType<typeof useParlours>);
    render(<Parlour />);
    await waitFor(() => screen.getByText("Members"));
    // Sarvam OCR tab is hidden entirely
    expect(screen.queryByText("Sarvam")).toBeNull();
  });
});
