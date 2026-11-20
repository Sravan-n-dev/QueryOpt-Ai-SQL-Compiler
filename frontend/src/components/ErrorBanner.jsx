import React from "react";
import { AlertCircle } from "lucide-react";

export default function ErrorBanner({ error }) {
  if (!error) return null;
  return (
    <div className="error-banner animate-slide-up">
      <AlertCircle size={18} className="error-icon" />
      <div className="error-content">
        <span className="error-stage">Error at Stage: {error.stage}</span>
        <pre className="error-msg">{error.message}</pre>
      </div>
    </div>
  );
}
