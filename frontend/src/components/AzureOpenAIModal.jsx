import React, { useState, useEffect } from "react";
import { X, Eye, EyeOff, ExternalLink, Sparkles, Loader2 } from "lucide-react";
import {
  getAzureOpenAIConfig,
  setAzureOpenAIConfig,
  clearAzureOpenAIConfig,
} from "../utils/api";

// Kept at the existing path so this patch can be overlaid onto the project.
export default function AzureOpenAIModal({ open, onClose, onConnected }) {
  const [endpoint, setEndpoint] = useState("");
  const [key, setKey] = useState("");
  const [deployment, setDeployment] = useState("gpt-5-mini");
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [configInfo, setConfigInfo] = useState(null);

  useEffect(() => {
    if (!open) return;
    setStatus(null);
    getAzureOpenAIConfig().then((data) => {
      setConfigInfo(data);
      setEndpoint(data.endpoint || "");
      setDeployment(data.deployment || "gpt-5-mini");
    }).catch((error) => {
      setStatus({ type: "error", msg: `Could not load Azure settings: ${error.message}` });
    });
  }, [open]);

  if (!open) return null;

  async function handleSave() {
    if (!endpoint.trim()) {
      setStatus({ type: "error", msg: "Enter the Azure OpenAI resource endpoint." });
      return;
    }
    if (!key.trim() && !configInfo?.is_configured) {
      setStatus({ type: "error", msg: "Enter an Azure OpenAI API key from your Azure resource." });
      return;
    }
    if (!deployment.trim()) {
      setStatus({ type: "error", msg: "Enter the deployment name shown in Model deployments." });
      return;
    }

    setLoading(true);
    setStatus({ type: "info", msg: "Testing the Azure OpenAI deployment..." });
    try {
      const res = await setAzureOpenAIConfig(endpoint.trim(), key.trim(), deployment.trim(), true);
      if (res.success) {
        setStatus({ type: "success", msg: res.message });
        setKey("");
        onConnected?.();
        window.setTimeout(onClose, 1200);
      } else {
        setStatus({ type: "error", msg: res.message || "Azure OpenAI connection failed." });
      }
    } catch (err) {
      setStatus({ type: "error", msg: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleClear() {
    setLoading(true);
    try {
      const res = await clearAzureOpenAIConfig();
      if (!res.success) throw new Error(res.message || "Could not clear Azure configuration.");
      setKey("");
      setConfigInfo({ is_configured: false, endpoint: "", deployment: "gpt-5-mini", masked_key: "" });
      setEndpoint("");
      setDeployment("gpt-5-mini");
      setStatus({ type: "success", msg: "Azure credentials cleared. The built-in schema fallback is active." });
      onConnected?.();
    } catch (err) {
      setStatus({ type: "error", msg: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target.className.includes("modal-overlay")) onClose(); }}>
      <div className="modal-dialog">
        <div className="modal-hdr">
          <div className="modal-hdr-left">
            <Sparkles size={22} className="modal-hdr-icon" />
            <div>
              <h3>Connect Azure OpenAI</h3>
              <p className="modal-sub">Use your deployed GPT-5 mini model for Natural Language to SQL</p>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose} aria-label="Close settings"><X size={18} /></button>
        </div>

        <div className="modal-body">
          <div className="info-box">
            <strong>Find these values in Azure Portal:</strong>
            <p>
              Open your Azure OpenAI resource → <strong>Keys and Endpoint</strong> for the endpoint and key, and
              <strong> Foundry → Model deployments</strong> for the deployment name. The screenshots show your deployment as <strong>gpt-5-mini</strong>.
            </p>
            <p>
              <a href="https://portal.azure.com/" target="_blank" rel="noopener noreferrer">
                Open Azure Portal <ExternalLink size={11} />
              </a>
            </p>
          </div>

          <label className="form-label" htmlFor="azure-endpoint">Azure OpenAI Endpoint</label>
          <input
            id="azure-endpoint"
            type="url"
            className="form-input mono"
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder="https://your-resource-name.openai.azure.com"
            autoComplete="url"
            spellCheck="false"
          />
          <span className="form-hint">Use the resource endpoint, not the full deployment URL. Confirm it in Azure Portal.</span>

          <label className="form-label" htmlFor="azure-api-key" style={{ marginTop: "1rem" }}>Azure OpenAI API Key</label>
          <div className="input-row">
            <input
              id="azure-api-key"
              type={showKey ? "text" : "password"}
              className="form-input mono"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={configInfo?.is_configured ? "Leave blank to keep the saved key" : "Paste Key 1 or Key 2"}
              autoComplete="off"
              spellCheck="false"
            />
            <button className="btn btn-ghost" onClick={() => setShowKey(!showKey)} aria-label={showKey ? "Hide key" : "Show key"}>
              {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <span className="form-hint">
            {configInfo?.is_configured
              ? `Connected credentials: ${configInfo.masked_key}. Leave the field blank to reuse the saved key.`
              : "The key is saved locally in your project's .env file. Do not share it."}
          </span>

          <label className="form-label" htmlFor="azure-deployment" style={{ marginTop: "1rem" }}>Deployment Name</label>
          <input
            id="azure-deployment"
            type="text"
            className="form-input mono"
            value={deployment}
            onChange={(e) => setDeployment(e.target.value)}
            placeholder="gpt-5-mini"
            autoComplete="off"
            spellCheck="false"
          />
          <span className="form-hint">This is the deployment NAME from Foundry, not an arbitrary model label.</span>

          {status && (
            <div className={`status-box status-${status.type}`}>
              {status.type === "info" && <Loader2 size={14} className="spin" />}
              {status.msg}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-danger btn-sm" onClick={handleClear} disabled={loading}>Clear Credentials</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
            {loading ? "Testing..." : "Test & Connect"}
          </button>
        </div>
      </div>
    </div>
  );
}
