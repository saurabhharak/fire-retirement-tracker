import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export type AnalyticsPeriod = "day" | "month" | "quarter" | "year";

export interface PnLSummary {
  total_sales: number;
  total_purchases: number;
  total_expenses: number;
  profit: number;
  sales_cash: number;
  sales_online: number;
  invoice_count: number;
  period: string;
  period_key: string;
}

export interface Trends {
  labels: string[];
  sales: number[];
  purchases: number[];
  expenses: number[];
  profit: number[];
}

export interface AmulAnalytics {
  summary: PnLSummary;
  trends: Trends;
}

export function useAmulAnalytics(
  parlourId?: string,
  options: { period?: AnalyticsPeriod; periodValue?: string; year?: number } = {}
) {
  const period = options.period ?? "month";
  const params = new URLSearchParams();
  if (parlourId) params.set("parlour_id", parlourId);
  params.set("period", period);
  if (options.periodValue) params.set("period_value", options.periodValue);
  if (options.year) params.set("year", String(options.year));

  return useQuery({
    queryKey: ["amul-analytics", parlourId, { period, periodValue: options.periodValue, year: options.year }],
    queryFn: () =>
      api
        .get<{ data: AmulAnalytics }>(`/api/amul/analytics?${params.toString()}`)
        .then((r) => r.data),
    enabled: !!parlourId,
  });
}