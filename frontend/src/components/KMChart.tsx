"use client";

import dynamic from "next/dynamic";
import type { CurvePoint } from "@/lib/api";

// Plotly must be loaded client-side only
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed"];

interface KMChartProps {
  curves: Record<string, CurvePoint[]>;
  xLabel?: string;
  title?: string;
  medians?: Record<string, number | null>;
}

export default function KMChart({ curves, xLabel = "Time", title, medians }: KMChartProps) {
  const names = Object.keys(curves);

  const traces = names.map((name, i) => {
    const pts = curves[name];
    // Build step-function: duplicate each point except first to create horizontal steps
    const xs: number[] = [];
    const ys: number[] = [];
    for (let j = 0; j < pts.length; j++) {
      if (j > 0) {
        xs.push(pts[j].time);
        ys.push(pts[j - 1].survival);
      }
      xs.push(pts[j].time);
      ys.push(pts[j].survival);
    }

    return {
      x: xs,
      y: ys,
      type: "scatter" as const,
      mode: "lines" as const,
      name,
      line: { color: COLORS[i % COLORS.length], width: 2 },
    };
  });

  // Add median lines
  const medianShapes: Plotly.Shape[] = [];
  if (medians) {
    names.forEach((name, i) => {
      const m = medians[name];
      if (m == null || isNaN(m)) return;
      medianShapes.push({
        type: "line",
        x0: m, x1: m, y0: 0, y1: 0.5,
        line: { color: COLORS[i % COLORS.length], width: 1, dash: "dot" },
      } as Plotly.Shape);
    });
  }

  return (
    <Plot
      data={traces}
      layout={{
        title: { text: title ?? "Kaplan-Meier Survival Curves" },
        xaxis: { title: xLabel, zeroline: false },
        yaxis: { title: "Survival Probability", range: [0, 1.05], zeroline: false },
        legend: { x: 0.7, y: 0.95 },
        shapes: medianShapes,
        margin: { t: 50, l: 60, r: 20, b: 60 },
        hovermode: "x unified",
        plot_bgcolor: "#fff",
        paper_bgcolor: "#fff",
      }}
      style={{ width: "100%", height: 420 }}
      config={{ responsive: true, displayModeBar: false }}
    />
  );
}
