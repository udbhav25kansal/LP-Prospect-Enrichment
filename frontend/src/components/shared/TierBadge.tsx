import { clsx } from "clsx";
import { TIER_CONFIG } from "@/lib/constants";

export default function TierBadge({ tier }: { tier: string }) {
  const config = TIER_CONFIG[tier] || TIER_CONFIG["WEAK FIT"];
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border",
        config.bg,
        config.text,
        config.border
      )}
    >
      {config.label}
    </span>
  );
}
