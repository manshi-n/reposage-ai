interface ScoreRingProps {
  label: string;
  value?: number;
  size?: number;
  description?: string;
}

export default function ScoreRing({
  label,
  value = 0,
  size = 96,
  description,
}: ScoreRingProps) {
  const safeValue = Math.max(
    0,
    Math.min(100, value ?? 0)
  );

  const radius = (size - 12) / 2;
  const circumference =
    2 * Math.PI * radius;

  const offset =
    circumference -
    (safeValue / 100) * circumference;

  const color =
    safeValue >= 80
      ? "#4FB8A6"
      : safeValue >= 60
      ? "#E8A33D"
      : "#E1596A";

  const status =
    safeValue >= 80
      ? "Healthy"
      : safeValue >= 60
      ? "Needs review"
      : "Needs attention";

  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-900 p-4">
      <div className="flex items-center gap-4">
        <div
          className="relative shrink-0"
          style={{
            width: size,
            height: size,
          }}
        >
          <svg
            width={size}
            height={size}
            className="-rotate-90"
          >
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="#242C3A"
              strokeWidth={8}
              fill="none"
            />

            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={color}
              strokeWidth={8}
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-700"
            />
          </svg>

          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-mono text-xl font-semibold text-mist-100">
              {safeValue}
            </span>
          </div>
        </div>

        <div className="min-w-0">
          <p className="text-sm font-medium text-mist-100">
            {label}
          </p>

          <p
            className="mt-1 text-xs"
            style={{ color }}
          >
            {status}
          </p>

          {description && (
            <p className="mt-2 text-xs leading-relaxed text-mist-400">
              {description}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}