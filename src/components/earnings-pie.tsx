"use client";

import { useMemo } from "react";

type PieDatum = {
  label: string;
  value: number;
};

const COLORS = [
  "#4f46e5",
  "#22c55e",
  "#06b6d4",
  "#f97316",
  "#a855f7",
  "#eab308",
  "#ef4444",
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
];

export function EarningsPie({ data }: { data: PieDatum[] }) {
  const { gradient, total, slices } = useMemo(() => {
    const positiveData = data.filter((d) => d.value > 0);
    const totalValue = positiveData.reduce((sum, d) => sum + d.value, 0);
    if (totalValue <= 0) {
      return { gradient: "", total: 0, slices: [] as Array<PieDatum & { pct: number; color: string }> };
    }

    let cursor = 0;
    const parts: string[] = [];
    const decorated = positiveData.map((d, i) => {
      const start = (cursor / totalValue) * 360;
      cursor += d.value;
      const end = (cursor / totalValue) * 360;
      const color = COLORS[i % COLORS.length];
      parts.push(`${color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`);
      return { ...d, pct: (d.value / totalValue) * 100, color };
    });

    return {
      gradient: `conic-gradient(${parts.join(", ")})`,
      total: totalValue,
      slices: decorated,
    };
  }, [data]);

  return (
    <section className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="pill mb-2 w-fit">Earnings split</div>
          <div className="text-lg font-semibold text-[var(--foreground)]">
            Share by agent
          </div>
          <div className="text-sm text-[var(--muted)]">
            Showing percentage of total earnings across your agents.
          </div>
        </div>
      </div>

      {total <= 0 ? (
        <div className="text-sm text-[var(--muted)]">No earnings yet.</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-[220px,1fr] md:items-center">
          <div
            className="mx-auto h-48 w-48 rounded-full border border-[var(--border)]"
            style={{ background: gradient }}
          />
          <div className="grid gap-2">
            {slices.map((slice) => (
              <div
                key={slice.label}
                className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-white px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className="text-sm text-[var(--foreground)]">{slice.label}</span>
                </div>
                <div className="text-sm font-semibold text-[var(--foreground)]">
                  {slice.value.toFixed(2)} GAS · {slice.pct.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

