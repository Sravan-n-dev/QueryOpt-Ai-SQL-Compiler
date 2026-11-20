import React, { useState, useEffect, useCallback } from "react";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import Editor from "./components/Editor";
import PipelineProgress from "./components/PipelineProgress";
import MetricsRibbon from "./components/MetricsRibbon";
import ErrorBanner from "./components/ErrorBanner";
import NLPreview from "./components/NLPreview";
import InspectorTabs from "./components/InspectorTabs";
import GeminiModal from "./components/GeminiModal";
import { useQueryEngine } from "./hooks/useQueryEngine";
import { fetchStats, fetchSchema } from "./utils/api";
import { SQL_DEMOS } from "./utils/demos";
import "./styles/layout.css";

export default function App() {
  const [mode, setMode] = useState("sql");
  const [sqlValue, setSqlValue] = useState(SQL_DEMOS[0].query);
  const [nlValue, setNlValue] = useState("");
  const [activeDemo, setActiveDemo] = useState("sql-0");
  const [stats, setStats] = useState(null);
  const [schema, setSchema] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [pipelineVisible, setPipelineVisible] = useState(false);
  const { result, loading, error, execute } = useQueryEngine();

  const loadStats = useCallback(() => {
    fetchStats().then(setStats).catch(() => {});
    fetchSchema().then(d => setSchema(d?.tables || [])).catch(() => {});
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  useEffect(() => {
    execute(SQL_DEMOS[0].query, "sql");
    setPipelineVisible(true);
  }, []);

  const handleRun = useCallback(() => {
    const q = mode === "sql" ? sqlValue : nlValue;
    if (!q.trim()) return;
    setPipelineVisible(true);
    execute(q.trim(), mode);
  }, [mode, sqlValue, nlValue, execute]);

  const handleSelectDemo = useCallback((id, query, demoMode) => {
    setMode(demoMode);
    setActiveDemo(id);
    if (demoMode === "sql") {
      setSqlValue(query);
    } else {
      setNlValue(query);
    }
    setPipelineVisible(true);
    execute(query, demoMode);
  }, [execute]);

  return (
    <div className="app-root">
      <Navbar stats={stats} onOpenSettings={() => setShowSettings(true)} />

      <div className="app-layout">
        <Sidebar
          mode={mode}
          onModeChange={setMode}
          activeDemo={activeDemo}
          onSelectDemo={handleSelectDemo}
          schema={schema}
        />

        <main className="main-content">
          <div className="main-scroll">
            <Editor
              mode={mode}
              sqlValue={sqlValue}
              nlValue={nlValue}
              onSqlChange={setSqlValue}
              onNlChange={setNlValue}
              onRun={handleRun}
              loading={loading}
            />

            <PipelineProgress
              stages={result?.stages}
              loading={loading}
              visible={pipelineVisible}
            />

            <ErrorBanner error={error} />

            {mode === "nl" && <NLPreview result={result} />}

            <MetricsRibbon result={result} />

            <InspectorTabs result={result} schema={schema} />
          </div>
        </main>
      </div>

      <GeminiModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
        onConnected={loadStats}
      />
    </div>
  );
}
