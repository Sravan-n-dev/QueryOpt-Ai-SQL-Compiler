import React, { useState } from "react";
import {
  Table2, Zap, Settings2, GitBranch, TreePine, Search, Database,
} from "lucide-react";
import ResultsTab from "./ResultsTab";

const TAB_LIST = [
  { id: "results", label: "Results", icon: Table2 },
  { id: "optimization", label: "Optimization", icon: Zap },
  { id: "physical", label: "Physical Plan", icon: Settings2 },
  { id: "ra", label: "Rel. Algebra", icon: GitBranch },
  { id: "ast", label: "AST Explorer", icon: TreePine },
  { id: "tokens", label: "Token Stream", icon: Search },
  { id: "schema", label: "Database", icon: Database },
];

export default function InspectorTabs({ result, schema }) {
  const [active, setActive] = useState("results");

  return (
    <section className="inspector-card animate-slide-up">
      <div className="tab-bar">
        {TAB_LIST.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${active === t.id ? "active" : ""}`}
            onClick={() => setActive(t.id)}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>
      <div className="tab-body">
        {active === "results" && <ResultsTab result={result} />}
        {active === "optimization" && <OptimizationTab result={result} />}
        {active === "physical" && <PhysicalTab result={result} />}
        {active === "ra" && <RATab result={result} />}
        {active === "ast" && <ASTTab result={result} />}
        {active === "tokens" && <TokensTab result={result} />}
        {active === "schema" && <SchemaTab schema={schema} />}
      </div>
    </section>
  );
}

/* ---- Optimization Tab ---- */
function OptimizationTab({ result }) {
  if (!result) return <EmptyTab msg="Run a query to see optimization details." />;
  const rep = result.optimization_report || {};
  const rules = result.applied_rules || [];

  return (
    <div className="opt-tab">
      <div className="opt-card">
        <h4 className="opt-title">Cost-Based Optimization Decision</h4>
        {rep.operator_choices?.length > 0 ? (
          rep.operator_choices.map((ch, i) => (
            <div key={i} className="opt-choice">
              <span className="opt-strategy">🎯 {ch.strategy}</span>
              <span className="opt-cost">Cost: {ch.estimated_cost}</span>
              <span className="opt-reason">{ch.reason}</span>
            </div>
          ))
        ) : (
          <p className="opt-fallback">Canonical plan chosen — no multi-path decision required.</p>
        )}
      </div>

      <div className="plan-compare">
        <div className="plan-box">
          <div className="plan-label">📋 Before Optimization</div>
          <pre className="plan-code">{result.ra_tree_text || "N/A"}</pre>
        </div>
        <div className="plan-box plan-box-highlight">
          <div className="plan-label">⚡ After Rewrites</div>
          <pre className="plan-code">{result.ra_tree_optimized_text || "N/A"}</pre>
        </div>
      </div>

      <div className="rules-section">
        <h4>Applied Rewrite Rules</h4>
        {rules.length > 0 ? (
          <div className="rules-badges">
            {rules.map((r, i) => (
              <span key={i} className="rule-badge">⚡ {r.rule_name}</span>
            ))}
          </div>
        ) : (
          <p className="opt-fallback">No rewrites applied (plan is already optimal).</p>
        )}
      </div>
    </div>
  );
}

/* ---- Physical Plan Tab ---- */
function PhysicalTab({ result }) {
  return (
    <div className="code-view-tab">
      <h4>Physical Execution Plan (CBO)</h4>
      <pre className="plan-code">{result?.physical_plan_pretty || "No physical plan available."}</pre>
    </div>
  );
}

/* ---- Relational Algebra Tab ---- */
function RATab({ result }) {
  return (
    <div className="code-view-tab">
      <h4>Canonical Relational Algebra Tree</h4>
      <pre className="plan-code">{result?.ra_tree_text || "No algebra tree."}</pre>
    </div>
  );
}

/* ---- AST Tab ---- */
function ASTTab({ result }) {
  return (
    <div className="code-view-tab">
      <h4>Abstract Syntax Tree</h4>
      <pre className="plan-code">{result?.ast_pretty || "No AST available."}</pre>
    </div>
  );
}

/* ---- Tokens Tab ---- */
function TokensTab({ result }) {
  const tokens = result?.tokens || [];
  if (!tokens.length) return <EmptyTab msg="No tokens to display." />;

  return (
    <div className="results-scroll">
      <table className="data-table">
        <thead><tr><th>#</th><th>Type</th><th>Value</th><th>Line</th><th>Col</th><th>Span</th></tr></thead>
        <tbody>
          {tokens.map((t, i) => (
            <tr key={i}>
              <td>{i}</td>
              <td><code>{t.type}</code></td>
              <td><strong>{t.value}</strong></td>
              <td>{t.line}</td>
              <td>{t.column}</td>
              <td>[{t.pos_start}:{t.pos_end}]</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---- Schema / Database Tab ---- */
function SchemaTab({ schema }) {
  const [expanded, setExpanded] = useState(null);

  if (!schema || schema.length === 0) {
    return <EmptyTab msg="Loading database schema..." />;
  }

  return (
    <div className="schema-tab">
      <div className="schema-tab-header">
        <h4>📊 College Database — Live Schema & Statistics</h4>
        <p className="schema-tab-sub">Click any table to explore its columns, indexes, and statistics.</p>
      </div>

      <div className="schema-cards">
        {schema.map(table => {
          const isOpen = expanded === table.table_name;
          return (
            <div key={table.table_name} className={`schema-card ${isOpen ? "open" : ""}`}>
              <button
                className="schema-card-header"
                onClick={() => setExpanded(isOpen ? null : table.table_name)}
              >
                <div className="schema-card-left">
                  <span className="schema-card-icon">📁</span>
                  <div>
                    <span className="schema-card-name">{table.table_name}</span>
                    <span className="schema-card-meta">
                      {table.row_count.toLocaleString()} rows · {table.columns.length} columns
                      {table.indexes?.length > 0 && ` · ${table.indexes.length} indexes`}
                    </span>
                  </div>
                </div>
                <span className={`schema-chevron ${isOpen ? "open" : ""}`}>▸</span>
              </button>

              {isOpen && (
                <div className="schema-card-body">
                  {/* Columns */}
                  <div className="schema-section">
                    <div className="schema-section-title">Columns</div>
                    <div className="results-scroll">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Column</th><th>Type</th><th>Distinct</th><th>Min</th><th>Max</th><th>Nulls</th>
                          </tr>
                        </thead>
                        <tbody>
                          {table.columns.map(col => (
                            <tr key={col.name}>
                              <td><strong>{col.name}</strong></td>
                              <td><code>{col.type}</code></td>
                              <td>{col.num_distinct ?? "—"}</td>
                              <td>{col.min_val != null ? String(col.min_val) : "—"}</td>
                              <td>{col.max_val != null ? String(col.max_val) : "—"}</td>
                              <td>{col.null_count ?? 0}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Indexes */}
                  {table.indexes?.length > 0 && (
                    <div className="schema-section">
                      <div className="schema-section-title">Indexes</div>
                      <div className="results-scroll">
                        <table className="data-table">
                          <thead><tr><th>Name</th><th>Columns</th><th>Unique</th></tr></thead>
                          <tbody>
                            {table.indexes.map(idx => (
                              <tr key={idx.name}>
                                <td><code>{idx.name}</code></td>
                                <td>{(idx.columns || []).join(", ")}</td>
                                <td>{idx.is_unique ? "✓ Yes" : "No"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EmptyTab({ msg }) {
  return <div className="tab-empty"><p>{msg}</p></div>;
}
