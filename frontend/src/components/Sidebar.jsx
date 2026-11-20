import React from "react";
import { Code, MessageSquare, FolderOpen, ChevronRight } from "lucide-react";
import { SQL_DEMOS, NL_DEMOS, ERR_DEMOS } from "../utils/demos";

export default function Sidebar({ mode, onModeChange, activeDemo, onSelectDemo, schema }) {
  return (
    <aside className="sidebar">
      {/* Mode Toggle */}
      <div className="sb-section">
        <div className="sb-label">Query Mode</div>
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === "sql" ? "active" : ""}`}
            onClick={() => onModeChange("sql")}
          >
            <Code size={14} /> SQL
          </button>
          <button
            className={`mode-btn ${mode === "nl" ? "active" : ""}`}
            onClick={() => onModeChange("nl")}
          >
            <MessageSquare size={14} /> Natural Language
          </button>
        </div>
      </div>

      {/* Demo Queries */}
      <div className="sb-section sb-demos">
        <div className="sb-label">Demo Queries</div>
        <div className="demo-list">
          {SQL_DEMOS.map((d, i) => (
            <DemoItem key={`sql-${i}`} demo={d} idx={`sql-${i}`}
              active={activeDemo === `sql-${i}`}
              onClick={() => onSelectDemo(`sql-${i}`, d.query, "sql")}
              color="purple"
            />
          ))}
          <div className="demo-divider" />
          {NL_DEMOS.map((d, i) => (
            <DemoItem key={`nl-${i}`} demo={d} idx={`nl-${i}`}
              active={activeDemo === `nl-${i}`}
              onClick={() => onSelectDemo(`nl-${i}`, d.query, "nl")}
              color="cyan"
            />
          ))}
          <div className="demo-divider" />
          {ERR_DEMOS.map((d, i) => (
            <DemoItem key={`err-${i}`} demo={d} idx={`err-${i}`}
              active={activeDemo === `err-${i}`}
              onClick={() => onSelectDemo(`err-${i}`, d.query, "sql")}
              color="red"
            />
          ))}
        </div>
      </div>

      {/* Schema */}
      <div className="sb-section">
        <div className="sb-label">Database Schema</div>
        <div className="schema-list">
          {(schema || []).map(t => (
            <div key={t.table_name} className="schema-item">
              <FolderOpen size={14} className="schema-icon" />
              <div className="schema-info">
                <span className="schema-name">{t.table_name}</span>
                <span className="schema-meta">{t.row_count.toLocaleString()} rows · {t.columns.length} cols</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

function DemoItem({ demo, active, onClick, color }) {
  return (
    <button className={`demo-item ${active ? "active" : ""}`} onClick={onClick}>
      <span className={`demo-badge demo-badge-${color}`}>{demo.badge}</span>
      <span className="demo-label">{demo.label}</span>
      <ChevronRight size={12} className="demo-arrow" />
    </button>
  );
}
