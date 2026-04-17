import clsx from "clsx";
import type { LogRankResult } from "@/lib/api";

interface Props { result: LogRankResult }

export default function ResultCard({ result }: Props) {
  const { p_value, significant, hazard_ratio, median_survival, n_patients, n_events } = result;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
      <h2 className="font-semibold text-lg">Log-Rank Test Results</h2>

      {/* P-value badge */}
      <div className="flex items-center gap-3">
        <span className="text-slate-600 text-sm">P-value:</span>
        <span className={clsx(
          "font-mono font-bold text-lg px-3 py-1 rounded-full",
          significant ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-700"
        )}>
          {p_value < 0.001 ? "< 0.001" : p_value.toFixed(4)}
        </span>
        {significant && (
          <span className="text-green-700 text-sm font-medium">Significant (p &lt; 0.05)</span>
        )}
      </div>

      {/* HR */}
      <div>
        <span className="text-slate-600 text-sm">Hazard Ratio:</span>
        <p className="font-mono mt-1 text-slate-800">{hazard_ratio.label}</p>
      </div>

      {/* Group stats table */}
      <table className="w-full text-sm border-collapse mt-2">
        <thead>
          <tr className="bg-slate-50 text-slate-600">
            <th className="text-left p-2 border border-slate-200">Group</th>
            <th className="text-right p-2 border border-slate-200">N</th>
            <th className="text-right p-2 border border-slate-200">Events</th>
            <th className="text-right p-2 border border-slate-200">Median Survival</th>
          </tr>
        </thead>
        <tbody>
          {Object.keys(n_patients).map((name) => (
            <tr key={name} className="hover:bg-slate-50">
              <td className="p-2 border border-slate-200 font-medium">{name}</td>
              <td className="p-2 border border-slate-200 text-right">{n_patients[name]}</td>
              <td className="p-2 border border-slate-200 text-right">{n_events[name]}</td>
              <td className="p-2 border border-slate-200 text-right font-mono">
                {median_survival[name] != null
                  ? median_survival[name]!.toFixed(1)
                  : "NR"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
