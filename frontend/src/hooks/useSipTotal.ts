import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useSipTotal() {
  return useQuery({
    queryKey: ["sip-log", "total-invested"],
    queryFn: () => api.get<{ data: number }>("/api/sip-log/total-invested").then((r) => r.data),
    staleTime: 15 * 60 * 1000, // 15 min
  });
}
