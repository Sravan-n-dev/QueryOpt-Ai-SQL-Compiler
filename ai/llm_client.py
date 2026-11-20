"""
QueryOpt AI — Gemini LLM Client
===============================
Wrapper around the official google-genai SDK for natural language to SQL translation.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple


class GeminiClient:
    """Client for generating SQL queries using Google Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model_name = (model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")).strip()
        self._client = None

        if self.api_key:
            self._init_sdk()

    def _init_sdk(self) -> bool:
        if not self.api_key:
            self._client = None
            return False
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return True
        except Exception:
            self._client = None
            return False

    def is_available(self) -> bool:
        """Return True if an API key is configured and SDK client is initialized."""
        return bool(self.api_key and self._client is not None)

    def set_api_key(self, api_key: str, model: Optional[str] = None, test_connection: bool = False) -> Tuple[bool, str]:
        """Dynamically set or update the Gemini API key, optionally testing connectivity."""
        clean_key = api_key.strip()
        if not clean_key:
            self.api_key = ""
            self._client = None
            os.environ.pop("GEMINI_API_KEY", None)
            return True, "Gemini API key cleared. Using schema-grounded fallback engine."

        self.api_key = clean_key
        if model:
            self.model_name = model.strip()
        os.environ["GEMINI_API_KEY"] = self.api_key
        if model:
            os.environ["GEMINI_MODEL"] = self.model_name

        success = self._init_sdk()
        if not success:
            return False, "Could not initialize Google GenAI SDK with the provided API key."

        if test_connection:
            try:
                # Run a minimal call to verify the key is valid
                from google.genai import types
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents="Ping. Reply with PONG.",
                    config=types.GenerateContentConfig(
                        max_output_tokens=10,
                        temperature=0.0,
                    ),
                )
                if response and response.text:
                    return True, f"Verified & Connected to Google Gemini ({self.model_name}) successfully!"
                return True, f"Connected to Google Gemini ({self.model_name})."
            except Exception as exc:
                err_msg = str(exc)
                if "API_KEY_INVALID" in err_msg or "400" in err_msg:
                    return False, "Invalid API key. Please check your key from Google AI Studio."
                elif "PERMISSION_DENIED" in err_msg or "403" in err_msg:
                    return False, "Permission denied for this API key. Ensure Generative Language API is enabled."
                elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    return True, f"Key saved! Note: Rate limit encountered ({self.model_name}). Fallback will engage automatically if needed."
                return False, f"Connection test failed: {err_msg}"

        return True, f"Connected to Google Gemini ({self.model_name})."

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Gemini API and return raw response text."""
        if not self.is_available():
            raise RuntimeError(
                "Gemini API key is not configured. Set the GEMINI_API_KEY in the UI or in your .env file."
            )

        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                ),
            )
            return response.text or ""
        except Exception as exc:
            raise RuntimeError(f"Gemini API error: {str(exc)}") from exc
