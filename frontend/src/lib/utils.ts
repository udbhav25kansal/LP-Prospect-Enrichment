export function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function formatCheckSize(
  min: number | null,
  max: number | null
): string {
  if (!min || !max) return "N/A";
  return `${formatCurrency(min)} - ${formatCurrency(max)}`;
}

export function formatScore(score: number): string {
  return score.toFixed(1);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
