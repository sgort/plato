import { useState } from "react";
import { useCbs } from "@/hooks/useCbs";
import type { CbsObservation } from "@/types";

// ── Inline SVG line chart ─────────────────────────────────────────────────────

interface ChartProps {
  observations: CbsObservation[];
}

function SparkLine({ observations }: ChartProps) {
  const values = observations.map((o) => o.value ?? 0);
  if (values.length < 2) return null;

  const W = 260;
  const H = 80;
  const PAD = { top: 8, right: 8, bottom: 20, left: 36 };

  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const rangeV = maxV - minV || 1;

  const toX = (i: number) =>
    PAD.left + (i / (values.length - 1)) * (W - PAD.left - PAD.right);
  const toY = (v: number) =>
    PAD.top + (1 - (v - minV) / rangeV) * (H - PAD.top - PAD.bottom);

  const points = values.map((v, i) => `${toX(i)},${toY(v)}`).join(" ");
  const areaPoints = [
    `${toX(0)},${H - PAD.bottom}`,
    ...values.map((v, i) => `${toX(i)},${toY(v)}`),
    `${toX(values.length - 1)},${H - PAD.bottom}`,
  ].join(" ");

  // Tick labels: first, middle, last period
  const labelIdx = [0, Math.floor(values.length / 2), values.length - 1];

  // Y axis ticks
  const yTicks = [minV, (minV + maxV) / 2, maxV];

  const formatPeriod = (p: string) => {
    // CBS periods look like "2024JJ00" (annual), "2024KW01" (quarterly), "2024MM01" (monthly)
    if (/\d{4}JJ/.test(p)) return p.slice(0, 4);
    if (/\d{4}KW(\d{2})/.test(p)) return `${p.slice(0, 4)} K${p.slice(6)}`;
    if (/\d{4}MM(\d{2})/.test(p)) return `${p.slice(0, 4)}-${p.slice(6)}`;
    return p.slice(0, 7);
  };

  const formatValue = (v: number) =>
    Math.abs(v) >= 1000
      ? `${(v / 1000).toFixed(1)}K`
      : v % 1 === 0
      ? String(v)
      : v.toFixed(1);

  const latestValue = values[values.length - 1];
  const prevValue = values[values.length - 2];
  const trend = latestValue - prevValue;

  return (
    <div>
      {/* Current value + trend */}
      <div className="mb-2 flex items-baseline gap-2">
        <span className="font-mono text-2xl font-semibold text-slate-100">
          {formatValue(latestValue)}
        </span>
        <span
          className={`font-mono text-xs ${
            trend > 0 ? "text-emerald-400" : trend < 0 ? "text-red-400" : "text-slate-500"
          }`}
        >
          {trend > 0 ? "▲" : trend < 0 ? "▼" : "—"} {Math.abs(trend).toFixed(1)}
        </span>
        <span className="text-xs text-slate-500">
          {formatPeriod(observations[observations.length - 1].period)}
        </span>
      </div>

      {/* Chart */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        className="overflow-visible"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="cbs-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {yTicks.map((v, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={toY(v)}
              y2={toY(v)}
              stroke="#243347"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 4}
              y={toY(v) + 3}
              textAnchor="end"
              fontSize={9}
              fill="#64748b"
            >
              {formatValue(v)}
            </text>
          </g>
        ))}

        {/* Area fill */}
        <polygon points={areaPoints} fill="url(#cbs-area)" />

        {/* Line */}
        <polyline
          points={points}
          fill="none"
          stroke="#f59e0b"
          strokeWidth={1.75}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Latest dot */}
        <circle
          cx={toX(values.length - 1)}
          cy={toY(latestValue)}
          r={3}
          fill="#f59e0b"
        />

        {/* X axis labels */}
        {labelIdx.map((i) => (
          <text
            key={i}
            x={toX(i)}
            y={H - 4}
            textAnchor={i === 0 ? "start" : i === values.length - 1 ? "end" : "middle"}
            fontSize={8}
            fill="#64748b"
          >
            {formatPeriod(observations[i].period)}
          </text>
        ))}
      </svg>
    </div>
  );
}

// ── Widget ────────────────────────────────────────────────────────────────────

export function CbsWidget() {
  const [open, setOpen] = useState(true);
  const { datasets, selectedCode, observations, dataset, loading, error, selectDataset } = useCbs(16);

  return (
    <section>
      {/* Header */}
      <button
        className="mb-3 flex w-full items-center justify-between text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          CBS — Statistieken
        </h2>
        <svg
          className={`h-3.5 w-3.5 text-slate-600 transition-transform duration-200 ${open ? "" : "-rotate-90"}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="animate-fade-in space-y-3">
          {/* Dataset selector */}
          <select
            value={selectedCode}
            onChange={(e) => selectDataset(e.target.value)}
            className="w-full rounded-lg border border-ink-600 bg-ink-800 px-3 py-1.5
                       text-xs text-slate-300 focus:border-amber-500 focus:outline-none
                       focus:ring-1 focus:ring-amber-500/30"
          >
            {datasets.map((d) => (
              <option key={d.code} value={d.code}>
                {d.label}
              </option>
            ))}
          </select>

          {/* Chart area */}
          <div className="rounded-lg border border-ink-700 bg-ink-800/40 px-3 py-3">
            {loading && (
              <div className="flex h-16 items-center justify-center">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
              </div>
            )}
            {error && (
              <p className="text-center text-xs text-red-400">{error}</p>
            )}
            {!loading && !error && observations.length > 0 && (
              <SparkLine observations={observations} />
            )}
            {!loading && !error && observations.length === 0 && (
              <p className="text-center text-xs text-slate-600">Geen data</p>
            )}
          </div>

          {/* Dataset description */}
          {dataset && (
            <p className="text-xs text-slate-600 leading-relaxed">
              {dataset.description}{" "}
              <a
                href={`https://opendata.cbs.nl/statline/#/CBS/nl/dataset/${dataset.code}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-amber-600 hover:text-amber-500"
              >
                CBS →
              </a>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
