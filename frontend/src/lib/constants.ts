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
  error: "#C45B5B",
} as const;

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
