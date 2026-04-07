import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface KiteHolding {
  fund: string;
  tradingsymbol: string;
  quantity: number;
  average_price: number;
  last_price: number;
  last_price_date: string;
  pnl: number;
  invested: number;
  current_value: number;
  pnl_pct: number;
  sip_amount: number | null;
  sip_frequency: string | null;
  sip_next_date: string | null;
}

export interface KiteSIP {
  sip_id: string;
  fund: string;
  tradingsymbol: string;
  status: "ACTIVE" | "PAUSED" | "CANCELLED";
  frequency: "monthly" | "weekly" | "quarterly";
  instalment_amount: number;
  completed_instalments: number;
  instalment_day: number;
  next_instalment: string | null;
}

export interface KitePortfolio {
  holdings: KiteHolding[];
  sips: KiteSIP[];
  total_invested: number;
  current_value: number;
  total_pnl: number;
  pnl_pct: number;
  total_monthly_sip: number;
  active_sip_count: number;
  synced_at: string;
  is_stale: boolean;
}

export interface KiteStatus {
  connected: boolean;
  connected_at?: string;
  expires_at?: string;
  is_expired: boolean;
  last_sync?: string;
}

export function useKitePortfolio() {
  const queryClient = useQueryClient();

  const status = useQuery({
    queryKey: ["kite-status"],
    queryFn: () =>
      api.get<{ data: KiteStatus }>("/api/kite/status").then((r) => r.data),
  });

  const portfolio = useQuery({
    queryKey: ["kite-portfolio"],
    queryFn: () =>
      api.get<{ data: KitePortfolio }>("/api/kite/portfolio").then((r) => r.data),
    enabled: !!status.data?.connected && !status.data?.is_expired,
  });

  const connect = async () => {
    const res = await api.get<{ data: { url: string } }>("/api/kite/login-url");
    window.location.href = res.data.url;
  };

  const disconnect = useMutation({
    mutationFn: () => api.delete("/api/kite/session"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kite-status"] });
      queryClient.invalidateQueries({ queryKey: ["kite-portfolio"] });
    },
  });

  return {
    status: status.data,
    statusLoading: status.isLoading,
    portfolio: portfolio.data,
    portfolioLoading: portfolio.isLoading,
    connect,
    disconnect: disconnect.mutateAsync,
    refresh: () => {
      queryClient.invalidateQueries({ queryKey: ["kite-portfolio"] });
    },
  };
}
