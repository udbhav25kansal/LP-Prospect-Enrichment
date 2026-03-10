import { clsx } from "clsx";

function getScoreColor(score: number): string {
  if (score >= 8) return "bg-emerald-500";
  if (score >= 6) return "bg-blue-500";
  if (score >= 4) return "bg-amber-500";
  return "bg-gray-400";
}

export default function ScoreBar({
  score,
  label,
  weight,
  confidence,
}: {
  score: number;
  label: string;
  weight?: string;
  confidence?: string | null;
}) {
  const pct = (score / 10) * 100;
  const color = getScoreColor(score);

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-sm">
        <span className="font-medium text-gray-700">
          {label}
          {weight && (
            <span className="text-gray-400 font-normal ml-1">({weight})</span>
          )}
        </span>
        <div className="flex items-center gap-2">
          <span className="font-bold text-gray-900">{score.toFixed(1)}</span>
          {confidence && (
            <span
              className={clsx(
                "text-xs",
                confidence === "high" && "text-green-600",
                confidence === "medium" && "text-amber-600",
                confidence === "low" && "text-red-500"
              )}
            >
              {confidence}
            </span>
          )}
        </div>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={clsx("h-2 rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
