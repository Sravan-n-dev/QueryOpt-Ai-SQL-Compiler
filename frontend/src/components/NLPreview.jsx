import React from "react";
import { Sparkles, Cpu } from "lucide-react";

export default function NLPreview({ result }) {
  if (!result || result.input_type !== "natural_language" || !result.generated_sql) return null;

  const info = result.translation_info || {};
  const isAzureOpenAI = info.engine === "azure_openai";

  return (
    <div className="nl-preview animate-slide-up">
      <div className="nl-preview-header">
        <span className="nl-preview-label">Generated SQL</span>
        <span className={`pill ${isAzureOpenAI ? "pill-green" : "pill-amber"}`}>
          {isAzureOpenAI ? <><Sparkles size={11} /> Azure GPT-5 mini</> : <><Cpu size={11} /> Schema Engine</>}
        </span>
      </div>
      <pre className="nl-preview-code">{result.generated_sql}</pre>
      {info.explanation && (
        <p className="nl-preview-explain">{info.explanation}</p>
      )}
    </div>
  );
}
