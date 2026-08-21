export interface TrendData {
  labels: string[];
  sales: number[];
  purchases: number[];
  expenses: number[];
  profit: number[];
}

export interface DailySale {
  cash_amount?: number | string | null;
  online_amount?: number | string | null;
}

export function dailyTotal(sale: DailySale): number {
  const cash = Number(sale.cash_amount ?? 0) || 0;
  const online = Number(sale.online_amount ?? 0) || 0;
  return cash + online;
}

export function trendChartData(trends: TrendData): {
  month: string;
  sales: number;
  purchases: number;
  expenses: number;
  profit: number;
}[] {
  if (
    !trends ||
    !Array.isArray(trends.labels) ||
    !Array.isArray(trends.sales) ||
    !Array.isArray(trends.purchases) ||
    !Array.isArray(trends.expenses) ||
    !Array.isArray(trends.profit)
  ) {
    return [];
  }
  return trends.labels
    .map((month, i) => ({
      month,
      sales: Number(trends.sales[i] ?? 0),
      purchases: Number(trends.purchases[i] ?? 0),
      expenses: Number(trends.expenses[i] ?? 0),
      profit: Number(trends.profit[i] ?? 0),
    }))
    .sort((a, b) => a.month.localeCompare(b.month));
}

export function periodLabel(period: string): string {
  if (period === "day") return "Daily";
  if (period === "quarter") return "Quarterly";
  if (period === "year") return "Annual";
  return "Monthly";
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
] as const;

/** Format a period_value (YYYY-MM-DD | YYYY-MM | YYYY-Qn | YYYY) into a readable label. */
export function formatPeriodValue(periodValue?: string): string {
  if (!periodValue) return "";
  // day: YYYY-MM-DD
  const dayMatch = periodValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dayMatch) {
    const [, y, m, d] = dayMatch;
    return `${Number(d)} ${MONTH_NAMES[Number(m) - 1]} ${y}`;
  }
  // quarter: YYYY-Qn
  const qMatch = periodValue.match(/^(\d{4})-Q([1-4])$/);
  if (qMatch) {
    return `Q${qMatch[2]} ${qMatch[1]}`;
  }
  // month: YYYY-MM
  const mMatch = periodValue.match(/^(\d{4})-(\d{2})$/);
  if (mMatch) {
    return `${MONTH_NAMES[Number(mMatch[2]) - 1]} ${mMatch[1]}`;
  }
  // year: YYYY
  return periodValue;
}
