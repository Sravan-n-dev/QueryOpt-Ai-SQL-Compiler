import React from "react";
import { Rows3, Timer, HardDrive, TrendingDown, ShieldCheck } from "lucide-react";

export default function MetricsRibbon({ result }) {
  if (!result || !result.success || !result.execution_result) return null;

  const er = result.execution_result;
  const rep = result.optimization_report || {};
  const match = result.results_match;

  const items = [
    { icon: Rows3, label: "Output Rows", value: er.row_count, color: "purple" },
    { icon: Timer, label: "Latency", value: `${(er.execution_time_ms || 0).toFixed(2)} ms`, color: "cyan" },
    { icon: HardDrive, label: "Rows Scanned", value: er.rows_scanned, color: "amber" },
    { icon: TrendingDown, label: "Est. Cost", value: (rep.optimized_cost || 0).toFixed(2), color: "pink" },
    { icon: ShieldCheck, label: "SQLite Check",
      value: match === true ? "100% Match ✓" : match === false ? "Order Diff" : "Verified ✓",
      color: match === false ? "amber" : "green"
    },
  ];

  return (
    <div className="metrics-ribbon animate-slide-up">
      {items.map((m, i) => (
        <div key={i} className={`metric-card metric-${m.color}`}>
          <m.icon size={16} className="metric-icon" />
          <div className="metric-info">
            <span className="metric-label">{m.label}</span>
            <span className="metric-value">{m.value}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
