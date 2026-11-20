import React, { useState, useEffect } from "react";
import { X, Eye, EyeOff, ExternalLink, Sparkles, Loader2 } from "lucide-react";
import { getGeminiConfig, setGeminiConfig } from "../utils/api";

export default function GeminiModal({ open, onClose, onConnected }) {
  const [key, setKey] = useState("");
  const [model, setModel] = useState("gemini-2.0-flash");
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [configInfo, setConfigInfo] = useState(null);

  useEffect(() => {
    if (open) {
      getGeminiConfig().then(d => {
        setConfigInfo(d);
        if (d.model) setModel(d.model);
      }).catch(() => {});
    }
  }, [open]);

  if (!open) return null;

  async function handleSave() {
    if (!key.trim()) {
      setStatus({ type: "error", msg: "Please enter your Gemini API key." });
      return;
    }
    setLoading(true);
    setStatus({ type: "info", msg: "Verifying API key..." });
    try {
      const res = await setGeminiConfig(key.trim(), model, true);
      if (res.success) {
        setStatus({ type: "success", msg: res.message });
        onConnected?.();
        setTimeout(onClose, 1500);
      } else {
        setStatus({ type: "error", msg: res.message });
      }
    } catch (err) {
      setStatus({ type: "error", msg: err.message });
    }
    setLoading(false);
  }

  async function handleClear() {
    await setGeminiConfig("", "gemini-2.0-flash", false);
    setKey("");
    setStatus({ type: "success", msg: "Switched to built-in fallback engine." });
    onConnected?.();
  }

  return (
    <div className="modal-overlay" onClick={e => { if (e.target.className.includes("modal-overlay")) onClose(); }}>
      <div className="modal-dialog">
        <div className="modal-hdr">
          <div className="modal-hdr-left">
            <Sparkles size={22} className="modal-hdr-icon" />
            <div>
              <h3>Connect Google Gemini API</h3>
              <p className="modal-sub">Enable AI-powered Natural Language to SQL</p>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="modal-body">
          <div className="info-box">
            <strong>How to get your API key:</strong>
            <p>
              Visit <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer">
              Google AI Studio <ExternalLink size={11} /></a> → Create API Key → Paste below.
            </p>
          </div>

          <label className="form-label">API Key</label>
          <div className="input-row">
            <input
              type={showKey ? "text" : "password"}
              className="form-input mono"
              value={key}
              onChange={e => setKey(e.target.value)}
              placeholder="AIzaSy..."
              autoComplete="off"
              spellCheck="false"
            />
            <button className="btn btn-ghost" onClick={() => setShowKey(!showKey)}>
              {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <span className="form-hint">
            {configInfo?.is_configured
              ? `🟢 Currently connected (${configInfo.masked_key})`
              : "🟡 No key set — using fallback engine"}
          </span>

          <label className="form-label" style={{marginTop:"1rem"}}>Model</label>
          <select className="form-select" value={model} onChange={e => setModel(e.target.value)}>
            <option value="gemini-2.0-flash">gemini-2.0-flash (Recommended)</option>
            <option value="gemini-1.5-flash">gemini-1.5-flash</option>
            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
          </select>

          {status && (
            <div className={`status-box status-${status.type}`}>
              {status.type === "info" && <Loader2 size={14} className="spin" />}
              {status.msg}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-danger btn-sm" onClick={handleClear}>Clear Key</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
            {loading ? "Testing..." : "Test & Connect"}
          </button>
        </div>
      </div>
    </div>
  );
}
