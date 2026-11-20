import React from "react";
import { Download, Table2 } from "lucide-react";

export default function ResultsTab({ result }) {
  const rows = result?.execution_result?.rows || [];

  function exportCSV() {
    if (!rows.length) return;
    const cols = Object.keys(rows[0]);
    let csv = cols.join(",") + "\n";
    rows.forEach(r => {
      csv += cols.map(c => {
        let v = r[c]; if (v == null) return "";
        let s = String(v).replace(/"/g, '""');
        return s.includes(",") ? `"${s}"` : s;
      }).join(",") + "\n";
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = "query_results.csv"; a.click();
  }

  if (!rows.length) {
    return (
      <div className="tab-empty">
        <Table2 size={40} className="empty-icon" />
        <p>No results to display.</p>
        <p className="empty-sub">Run a query to see output rows here.</p>
      </div>
    );
  }

  const cols = Object.keys(rows[0]);

  return (
    <div className="results-tab">
      <div className="results-toolbar">
        <span className="results-count">{rows.length} rows returned</span>
        <button className="btn btn-secondary btn-sm" onClick={exportCSV}>
          <Download size={13} /> Export CSV
        </button>
      </div>
      <div className="results-scroll">
        <table className="data-table">
          <thead>
            <tr>{cols.map(c => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {cols.map(c => (
                  <td key={c}>{r[c] != null ? String(r[c]) : <em style={{color:"var(--text-muted)"}}>NULL</em>}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
