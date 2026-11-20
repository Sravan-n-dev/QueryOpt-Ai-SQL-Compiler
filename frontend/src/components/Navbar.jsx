import React from "react";
import { Database, Cpu, Sparkles, Settings, Zap } from "lucide-react";

export default function Navbar({ stats, onOpenSettings }) {
  const aiLive = stats?.ai_available;
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="nav-brand">
          <div className="brand-icon-wrap">
            <Zap size={20} className="brand-icon" />
          </div>
          <div>
            <span className="brand-name">QueryOpt AI</span>
            <span className="brand-sub">SQL Compiler &amp; Cost-Based Optimizer</span>
          </div>
        </div>

        <div className="nav-pills">
          <span className="pill pill-green">
            <span className="dot dot-green" /> SQLite Connected
          </span>
          <span className="pill pill-purple">
            <Database size={12} />
            {stats ? `${(stats.total_records || 0).toLocaleString()} rows` : "..."}
          </span>
          <span className="pill pill-cyan">
            <Cpu size={12} />
            {stats ? `${stats.total_indexes || 0} Indexes` : "..."}
          </span>
          <button
            className={`pill ${aiLive ? "pill-green" : "pill-amber"} nav-ai-pill`}
            onClick={onOpenSettings}
            title="Configure Gemini API"
          >
            <span className={`dot ${aiLive ? "dot-green" : "dot-amber"}`} />
            <Sparkles size={12} />
            {aiLive ? `Gemini: Live` : "AI: Fallback"}
          </button>
          <button className="btn btn-ghost nav-settings-btn" onClick={onOpenSettings} title="Settings">
            <Settings size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
