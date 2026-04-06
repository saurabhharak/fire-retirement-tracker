export const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
] as const;

export const COLORS = {
  primary: "#00895E",
  secondary: "#D4A843",
  tertiary: "#1A3A5C",
  background: "#0D1B2A",
  surface: "#132E3D",
  text: "#E8ECF1",
  success: "#2E8B57",
  warning: "#E5A100",
  error: "#E5A100",
} as const;

export const EXPENSE_CATEGORIES: { value: string; label: string; color: string }[] = [
  { value: "housing", label: "Housing", color: "#D4A843" },
  { value: "food", label: "Food", color: "#00895E" },
  { value: "transport", label: "Transport", color: "#3B82F6" },
  { value: "utilities", label: "Utilities", color: "#6B7280" },
  { value: "entertainment", label: "Entertainment", color: "#E07A5F" },
  { value: "health", label: "Health", color: "#2E8B57" },
  { value: "education", label: "Education", color: "#8B5CF6" },
  { value: "insurance", label: "Insurance", color: "#1A3A5C" },
  { value: "subscriptions", label: "Subscriptions", color: "#EC4899" },
  { value: "other", label: "Other", color: "#9CA3AF" },
];

export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "LayoutDashboard" },
  { path: "/income-expenses", label: "Income & Expenses", icon: "Coins" },
  { path: "/gold-portfolio", label: "Gold Portfolio", icon: "Gem" },
  { path: "/fire-settings", label: "FIRE Settings", icon: "Settings" },
  { path: "/fund-allocation", label: "Fund Allocation", icon: "Briefcase" },
  { path: "/growth-projection", label: "Growth Projection", icon: "TrendingUp" },
  { path: "/retirement-analysis", label: "Retirement Analysis", icon: "Shield" },
  { path: "/sip-tracker", label: "SIP Tracker", icon: "ClipboardList" },
  { path: "/settings-privacy", label: "Settings & Privacy", icon: "Lock" },
] as const;
