import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface FireInputsData {
  dob: string;
  retirement_age: number;
  life_expectancy: number;
  your_sip: number;
  wife_sip: number;
  step_up_pct: number;
  existing_corpus: number;
  equity_return: number;
  debt_return: number;
  gold_return: number;
  cash_return: number;
  inflation: number;
  swr: number;
  equity_pct: number;
  gold_pct: number;
  cash_pct: number;
  monthly_expense: number;
}

export function useFireInputs() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["fire-inputs"],
    queryFn: () =>
      api
        .get<{ data: FireInputsData | null }>("/api/fire-inputs")
        .then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: (data: FireInputsData) => api.put("/api/fire-inputs", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fire-inputs"] });
      queryClient.invalidateQueries({ queryKey: ["projections"] });
    },
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    save: mutation.mutateAsync,
    isSaving: mutation.isPending,
  };
}
