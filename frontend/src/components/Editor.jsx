import React, { useRef, useEffect } from "react";
import { Play, Trash2, Loader2 } from "lucide-react";

export default function Editor({ mode, sqlValue, nlValue, onSqlChange, onNlChange, onRun, loading }) {
  const sqlRef = useRef(null);
  const nlRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        onRun();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onRun]);

  return (
    <section className="editor-card animate-slide-up">
      <div className="editor-header">
        <div className="editor-title">
          {mode === "sql" ? (
            <><span className="editor-dot dot-purple" /> SQL Query Editor</>
          ) : (
            <><span className="editor-dot dot-purple" /> Natural Language Prompt</>
          )}
        </div>
        <div className="editor-actions">
          <button className="btn btn-secondary btn-sm" onClick={() => mode === "sql" ? onSqlChange("") : onNlChange("")}>
            <Trash2 size={13} /> Clear
          </button>
          <button className="btn btn-primary" onClick={onRun} disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : <Play size={15} />}
            {loading ? "Compiling..." : "Compile & Execute"}
          </button>
        </div>
      </div>

      {mode === "sql" ? (
        <div className="editor-body">
          <textarea
            ref={sqlRef}
            className="code-textarea"
            spellCheck="false"
            value={sqlValue}
            onChange={e => onSqlChange(e.target.value)}
            placeholder="Enter SQL SELECT query..."
          />
          <div className="editor-footer">
            <span className="shortcut-hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> to execute</span>
          </div>
        </div>
      ) : (
        <div className="editor-body">
          <input
            ref={nlRef}
            className="nl-input"
            type="text"
            value={nlValue}
            onChange={e => onNlChange(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") onRun(); }}
            placeholder="Type your question in plain English..."
          />
          <div className="editor-footer">
            <span className="shortcut-hint"><kbd>Enter</kbd> to translate &amp; compile</span>
            <span className="shortcut-hint">Powered by Gemini AI &amp; Schema Engine</span>
          </div>
        </div>
      )}
    </section>
  );
}
