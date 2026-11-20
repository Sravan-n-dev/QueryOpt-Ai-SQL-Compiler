import React from "react";
import { Check, X, Loader2 } from "lucide-react";

const STAGES = [
  { num: 1, name: "Lexer" },
  { num: 2, name: "Parser" },
  { num: 3, name: "Semantic" },
  { num: 4, name: "Rel. Algebra" },
  { num: 5, name: "Logical Opt" },
  { num: 6, name: "Cost Opt" },
  { num: 7, name: "Volcano Exec" },
];

export default function PipelineProgress({ stages, loading, visible }) {
  if (!visible) return null;

  const stageMap = {};
  if (stages) {
    stages.forEach(s => { stageMap[s.stage_number] = s; });
  }

  return (
    <div className="pipeline-bar animate-slide-up">
      {STAGES.map((s, i) => {
        const info = stageMap[s.num];
        let status = "pending";
        if (loading && !info) status = "pending";
        else if (info?.status === "success") status = "success";
        else if (info?.status === "error") status = "error";
        else if (loading) status = "running";

        return (
          <React.Fragment key={s.num}>
            {i > 0 && <div className={`pipe-connector ${status === "success" ? "pipe-done" : ""}`} />}
            <div className={`pipe-step pipe-${status}`} title={info ? `${info.duration_ms}ms` : ""}>
              <div className="pipe-circle">
                {status === "success" && <Check size={12} />}
                {status === "error" && <X size={12} />}
                {status === "running" && <Loader2 size={12} className="spin" />}
                {status === "pending" && <span className="pipe-num">{s.num}</span>}
              </div>
              <span className="pipe-label">{s.name}</span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}
