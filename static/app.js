/**
 * QueryOpt AI — Frontend Application Logic
 */

let currentMode = "sql";
let currentResults = [];
let allDemos = null;

const DEFAULT_SQL_DEMOS = [
  "SELECT *\nFROM Student\nWHERE age > 23\nLIMIT 10;",
  "SELECT name, cgpa\nFROM Student\nWHERE branch = 'ECE'\nLIMIT 10;",
  "SELECT name, age\nFROM Student\nWHERE age > 23 AND branch = 'ECE'\nLIMIT 10;",
  "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nLIMIT 10;",
  "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nWHERE s.age > 23 AND d.dept_name = 'Computer Science'\nLIMIT 10;",
  "SELECT s.name, c.course_name, e.marks\nFROM Student s\nINNER JOIN Enrollment e\nON s.student_id = e.student_id\nINNER JOIN Course c\nON e.course_id = c.course_id\nWHERE e.marks > 80\nLIMIT 10;",
  "SELECT name, cgpa\nFROM Student\nORDER BY cgpa DESC\nLIMIT 10;"
];

const DEFAULT_NL_DEMOS = [
  "List out all the students above age 23 whose branch is ECE.",
  "Show the names and CGPA of all CSE students.",
  "Find students who scored more than 80 marks in their courses.",
  "List the top 10 students based on CGPA."
];

const DEFAULT_ERR_DEMOS = [
  "SELECT name # age FROM Student;",
  "SELECT FROM Student;",
  "SELECT unknown_column FROM Student;"
];

document.addEventListener("DOMContentLoaded", () => {
  // Set default initial SQL
  const sqlInput = document.getElementById("sql-input");
  sqlInput.value = DEFAULT_SQL_DEMOS[0];

  // Shortcut Ctrl+Enter to execute
  sqlInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      runQuery();
    }
  });

  const nlInput = document.getElementById("nl-input");
  nlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      runQuery();
    }
  });

  // Automatically execute the initial query so the user sees results immediately on load!
  runQuery();
});

function setMode(mode) {
  currentMode = mode;
  const sqlBtn = document.getElementById("btn-mode-sql");
  const nlBtn = document.getElementById("btn-mode-nl");
  const sqlArea = document.getElementById("sql-input-container");
  const nlArea = document.getElementById("nl-input-container");
  const editorTitle = document.getElementById("editor-title");

  if (mode === "sql") {
    sqlBtn.classList.add("active");
    nlBtn.classList.remove("active");
    sqlArea.style.display = "block";
    nlArea.style.display = "none";
    editorTitle.textContent = "SQL Query Input";
  } else {
    nlBtn.classList.add("active");
    sqlBtn.classList.remove("active");
    sqlArea.style.display = "none";
    nlArea.style.display = "block";
    editorTitle.textContent = "Natural Language Prompt (Gemini AI)";
  }
}

function loadDemo(idx) {
  setMode("sql");
  const sqlInput = document.getElementById("sql-input");
  sqlInput.value = DEFAULT_SQL_DEMOS[idx] || DEFAULT_SQL_DEMOS[0];
  _highlightDemoItem(idx);
  runQuery();
}

function loadNLDemo(idx) {
  setMode("nl");
  const nlInput = document.getElementById("nl-input");
  nlInput.value = DEFAULT_NL_DEMOS[idx] || DEFAULT_NL_DEMOS[0];
  runQuery();
}

function loadErrorDemo(idx) {
  setMode("sql");
  const sqlInput = document.getElementById("sql-input");
  sqlInput.value = DEFAULT_ERR_DEMOS[idx] || DEFAULT_ERR_DEMOS[0];
  runQuery();
}

function _highlightDemoItem(idx) {
  const items = document.querySelectorAll(".demo-item");
  items.forEach((el, i) => {
    if (i === idx) el.classList.add("active");
    else el.classList.remove("active");
  });
}

function clearEditor() {
  if (currentMode === "sql") {
    document.getElementById("sql-input").value = "";
  } else {
    document.getElementById("nl-input").value = "";
    document.getElementById("nl-generated-preview").style.display = "none";
  }
}

async function runQuery() {
  const runBtn = document.getElementById("btn-run");
  const runText = document.getElementById("run-text");
  const runIcon = document.getElementById("run-icon");
  const errorBanner = document.getElementById("error-banner");
  const metricsRibbon = document.getElementById("metrics-ribbon");
  const progressRibbon = document.getElementById("pipeline-progress");

  let queryText = "";
  if (currentMode === "sql") {
    queryText = document.getElementById("sql-input").value.trim();
  } else {
    queryText = document.getElementById("nl-input").value.trim();
  }

  if (!queryText) {
    alert("Please enter a query to execute.");
    return;
  }

  // UI loading state
  runBtn.disabled = true;
  runText.textContent = "Compiling...";
  runIcon.textContent = "⏳";
  errorBanner.style.display = "none";
  progressRibbon.style.display = "flex";

  // Reset steps
  _resetStageSteps();

  try {
    const resp = await fetch("/api/compile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText, mode: currentMode })
    });

    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.detail || "Server compilation error.");
    }

    // Update Stage steps
    _updateStageSteps(data.stages, data.success);

    if (!data.success) {
      // Show Error banner
      errorBanner.style.display = "block";
      document.getElementById("error-stage-title").textContent = `Error in Stage: ${data.error_stage}`;
      document.getElementById("error-message-text").textContent = data.error_message;
      metricsRibbon.style.display = "none";

      // Clear table
      const container = document.getElementById("results-table-container");
      container.innerHTML = `<div class="empty-state"><p style="color: #EF4444; font-weight: 600;">Compilation halted at [${data.error_stage}].</p><p>Fix the query syntax or identifiers to continue.</p></div>`;
      return;
    }

    // SUCCESS: Show Metrics & Results
    errorBanner.style.display = "none";
    metricsRibbon.style.display = "grid";

    // Handle NL preview if in NL mode
    if (currentMode === "nl" && data.generated_sql) {
      const previewBox = document.getElementById("nl-generated-preview");
      previewBox.style.display = "block";
      document.getElementById("nl-generated-sql").textContent = data.generated_sql;
    }

    // Metrics ribbon
    const er = data.execution_result || {};
    document.getElementById("metric-rows").textContent = er.row_count || 0;
    document.getElementById("metric-latency").textContent = `${(er.execution_time_ms || 0).toFixed(2)} ms`;
    document.getElementById("metric-scanned").textContent = er.rows_scanned || 0;

    const rep = data.optimization_report || {};
    document.getElementById("metric-cost").textContent = `${(rep.optimized_cost || 0).toFixed(2)}`;

    const matchEl = document.getElementById("metric-match");
    if (data.results_match === true) {
      matchEl.textContent = "✅ 100% Match";
      matchEl.className = "metric-val badge-ok";
    } else if (data.results_match === false) {
      matchEl.textContent = "⚠️ Order Diff";
      matchEl.className = "metric-val";
    } else {
      matchEl.textContent = "N/A";
    }

    // Render Results Table
    currentResults = er.rows || [];
    renderResultsTable(currentResults);

    // Render Optimization Tab
    renderOptimizationTab(data);

    // Render Physical Plan Tab
    document.getElementById("physical-plan-tree").textContent = data.physical_plan_pretty || "No physical plan.";

    // Render Relational Algebra Tab
    document.getElementById("canonical-ra-tree").textContent = data.ra_tree_text || "No logical plan.";

    // Render AST Tab
    document.getElementById("ast-pretty-view").textContent = data.ast_pretty || "No AST.";

    // Render Tokens Tab
    renderTokensTable(data.tokens || []);

  } catch (err) {
    errorBanner.style.display = "block";
    document.getElementById("error-stage-title").textContent = "Request Error";
    document.getElementById("error-message-text").textContent = err.message;
  } finally {
    runBtn.disabled = false;
    runText.textContent = "Compile & Execute";
    runIcon.textContent = "🚀";
  }
}

function renderResultsTable(rows) {
  const container = document.getElementById("results-table-container");
  const countLabel = document.getElementById("table-row-count");

  countLabel.textContent = `${rows.length} rows returned`;

  if (!rows || rows.length === 0) {
    container.innerHTML = `<div class="empty-state"><p>Query executed successfully, but returned 0 rows.</p></div>`;
    return;
  }

  const columns = Object.keys(rows[0]);

  let html = "<table><thead><tr>";
  columns.forEach(col => {
    html += `<th>${escapeHtml(col)}</th>`;
  });
  html += "</tr></thead><tbody>";

  rows.forEach(r => {
    html += "<tr>";
    columns.forEach(col => {
      const val = r[col];
      html += `<td>${val !== null && val !== undefined ? escapeHtml(String(val)) : "<em>NULL</em>"}</td>`;
    });
    html += "</tr>";
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

function renderOptimizationTab(data) {
  const rep = data.optimization_report || {};
  const decisionsList = document.getElementById("opt-decisions-list");
  let decisionsHtml = "";

  if (rep.operator_choices && rep.operator_choices.length > 0) {
    rep.operator_choices.forEach(ch => {
      decisionsHtml += `<div style="margin-bottom: 0.5rem;"><strong>🎯 ${escapeHtml(ch.strategy)}</strong> (Est. Cost: ${ch.estimated_cost}): <em>${escapeHtml(ch.reason)}</em></div>`;
    });
  } else {
    decisionsHtml = "Canonical plan chosen; no multi-path decision required.";
  }
  decisionsList.innerHTML = decisionsHtml;

  document.getElementById("plan-before").textContent = data.ra_tree_text || "N/A";
  document.getElementById("plan-after").textContent = data.ra_tree_optimized_text || "N/A";

  const rulesList = document.getElementById("applied-rules-list");
  if (data.applied_rules && data.applied_rules.length > 0) {
    let rulesHtml = "";
    data.applied_rules.forEach(r => {
      rulesHtml += `<span class="rule-badge">⚡ ${escapeHtml(r.rule_name)}</span>`;
    });
    rulesList.innerHTML = rulesHtml;
  } else {
    rulesList.innerHTML = "<em>No rewrites needed (already optimal).</em>";
  }
}

function renderTokensTable(tokens) {
  const container = document.getElementById("tokens-table-container");
  if (!tokens || tokens.length === 0) {
    container.innerHTML = "<p>No tokens available.</p>";
    return;
  }

  let html = "<table><thead><tr><th>#</th><th>Type</th><th>Value</th><th>Line</th><th>Col</th><th>Span</th></tr></thead><tbody>";
  tokens.forEach((t, i) => {
    html += `<tr>
      <td>${i}</td>
      <td><code>${escapeHtml(t.type)}</code></td>
      <td><strong>${escapeHtml(t.value)}</strong></td>
      <td>${t.line}</td>
      <td>${t.column}</td>
      <td>[${t.pos_start}:${t.pos_end}]</td>
    </tr>`;
  });
  html += "</tbody></table>";
  container.innerHTML = html;
}

function switchTab(tabId) {
  const btns = document.querySelectorAll(".tab-btn");
  const panes = document.querySelectorAll(".tab-pane");

  panes.forEach(p => p.classList.remove("active"));
  btns.forEach(b => b.classList.remove("active"));

  document.getElementById(`tab-${tabId}`).classList.add("active");
  event.target.classList.add("active");
}

function exportCSV() {
  if (!currentResults || currentResults.length === 0) {
    alert("No data available to export.");
    return;
  }

  const columns = Object.keys(currentResults[0]);
  let csvContent = columns.join(",") + "\n";

  currentResults.forEach(r => {
    const row = columns.map(c => {
      let val = r[c];
      if (val === null || val === undefined) return "";
      let str = String(val).replace(/"/g, '""');
      if (str.includes(",") || str.includes("\n")) str = `"${str}"`;
      return str;
    });
    csvContent += row.join(",") + "\n";
  });

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", "query_results.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function _resetStageSteps() {
  for (let i = 1; i <= 7; i++) {
    const el = document.getElementById(`step-s${i}`);
    if (el) {
      el.className = "stage-step";
    }
  }
}

function _updateStageSteps(stages, overallSuccess) {
  if (!stages) return;
  stages.forEach(s => {
    const el = document.getElementById(`step-s${s.stage_number}`);
    if (el) {
      if (s.status === "success") {
        el.className = "stage-step active-success";
      } else if (s.status === "error") {
        el.className = "stage-step active-error";
      }
    }
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
