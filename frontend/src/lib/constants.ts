export const TIER_CONFIG: Record<
  string,
  { bg: string; text: string; border: string; label: string }
> = {
  "PRIORITY CLOSE": {
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    border: "border-emerald-300",
    label: "Priority Close",
  },
  "STRONG FIT": {
    bg: "bg-blue-100",
    text: "text-blue-800",
    border: "border-blue-300",
    label: "Strong Fit",
  },
  "MODERATE FIT": {
    bg: "bg-amber-100",
    text: "text-amber-800",
    border: "border-amber-300",
    label: "Moderate Fit",
  },
  "WEAK FIT": {
    bg: "bg-gray-100",
    text: "text-gray-600",
    border: "border-gray-300",
    label: "Weak Fit",
  },
};

export const TIER_COLORS: Record<string, string> = {
  "PRIORITY CLOSE": "#059669",
  "STRONG FIT": "#2563eb",
  "MODERATE FIT": "#d97706",
  "WEAK FIT": "#6b7280",
};

export const CONFIDENCE_CONFIG: Record<
  string,
  { color: string; label: string }
> = {
  high: { color: "text-green-600", label: "High" },
  medium: { color: "text-amber-600", label: "Med" },
  low: { color: "text-red-500", label: "Low" },
};

export const SEVERITY_CONFIG: Record<
  string,
  { bg: string; text: string; icon: string }
> = {
  error: { bg: "bg-red-100", text: "text-red-800", icon: "X" },
  warning: { bg: "bg-amber-100", text: "text-amber-800", icon: "!" },
  info: { bg: "bg-blue-100", text: "text-blue-800", icon: "i" },
};

export const ORG_TYPES = [
  "Single Family Office",
  "Multi-Family Office",
  "Fund of Funds",
  "Foundation",
  "Endowment",
  "Pension",
  "Insurance",
  "Asset Manager",
  "RIA/FIA",
  "HNWI",
  "Private Capital Firm",
];

export const DIMENSION_LABELS: Record<string, { name: string; weight: string }> = {
  d1: { name: "Sector & Mandate Fit", weight: "35%" },
  d2: { name: "Relationship Depth", weight: "30%" },
  d3: { name: "Halo & Strategic Value", weight: "20%" },
  d4: { name: "Emerging Manager Fit", weight: "15%" },
};
