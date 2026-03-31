import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface GrowthRow {
  year: number;
  age: number;
  monthly_sip: number;
  annual_inv: number;
  cumulative: number;
  portfolio: number;
  gains: number;
  equity_value: number;
  debt_gold_cash: number;
}

export interface RetirementData {
  corpus: number;
  annual_expense: number;
  monthly_expense: number;
  monthly_swp: number;
  surplus: number;
  funded_ratio: number;
  required_corpus: number;
  buckets: Array<{
    name: string;
    pct: number;
    amount: number;
    coverage_years: number;
  }>;
  swr_scenarios: Array<{
    rate: number;
    annual: number;
    monthly: number;
    vs_expense: number;
    verdict: string;
  }>;
}

export interface FundAllocationRow {
  name: string;
  category: string;
  pct: number;
  monthly_sip: number;
  account: string;
}

export function useGrowthProjection() {
  return useQuery({
    queryKey: ["projections", "growth"],
    queryFn: () =>
      api
        .get<{ data: GrowthRow[] }>("/api/projections/growth")
        .then((r) => r.data),
  });
}

export function useRetirementAnalysis() {
  return useQuery({
    queryKey: ["projections", "retirement"],
    queryFn: () =>
      api
        .get<{ data: RetirementData }>("/api/projections/retirement")
        .then((r) => r.data),
  });
}

export function useFundAllocation() {
  return useQuery({
    queryKey: ["projections", "fund-allocation"],
    queryFn: () =>
      api
        .get<{ data: FundAllocationRow[] }>("/api/projections/fund-allocation")
        .then((r) => r.data),
  });
}

export function useMonthlySips() {
  return useQuery({
    queryKey: ["projections", "monthly-sips"],
    queryFn: () =>
      api
        .get<{ data: number[] }>("/api/projections/monthly-sips")
        .then((r) => r.data),
  });
}
